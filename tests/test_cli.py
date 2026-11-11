import runpy
from pathlib import Path
from typing import Any

import pytest
from google.api_core import exceptions as api_exceptions
from google.auth import exceptions as auth_exceptions
from google.cloud import vision

from tests.factories import FakeClient, hello_response
from vision_sandbox import cli


class FakePrompt:
    """inquirer.prompt の代わり。受け取った質問を記録し、決めた回答を返す。"""

    def __init__(self, answers: dict[str, str] | None) -> None:
        self.answers = answers
        self.questions: list[Any] = []

    def __call__(self, questions: list[Any]) -> dict[str, str] | None:
        self.questions.extend(questions)
        return self.answers


def unexpected_prompt(questions: list[Any]) -> dict[str, str] | None:
    raise AssertionError("prompt should not be called")


@pytest.fixture
def image(tmp_path: Path) -> Path:
    path = tmp_path / "synthetic.png"
    path.write_bytes(b"synthetic-image-bytes")
    return path


def run_main(
    argv: list[str], client: FakeClient | Exception, prompt: Any = unexpected_prompt
) -> int:
    def factory() -> FakeClient:
        if isinstance(client, Exception):
            raise client
        return client

    return cli.main(argv, client_factory=factory, prompt=prompt)


def test_main_with_arguments_prints_paragraphs_and_writes_json(
    image: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    output = tmp_path / "out" / "response.json"
    client = FakeClient(hello_response())

    code = run_main(
        [
            str(image),
            "--feature",
            "DOCUMENT_TEXT_DETECTION",
            "--output",
            str(output),
            "--timeout",
            "5",
        ],
        client,
    )

    assert code == 0
    [(request, timeout)] = client.calls
    assert request.features[0].type_ == vision.Feature.Type.DOCUMENT_TEXT_DETECTION
    assert timeout == 5.0
    assert output.is_file()
    out = capsys.readouterr().out
    assert "         Hello, Vision API! (40, 50) (360, 50) (360, 95) (40, 95)" in out
    assert f"{output} へ、もともとの JSON を書き出したよ。" in out


def test_main_uses_defaults_for_output_and_timeout(
    image: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    client = FakeClient(hello_response())

    assert run_main([str(image), "--feature", "TEXT_DETECTION"], client) == 0

    assert client.calls[0][1] == 60.0
    assert (tmp_path / "output" / "annotate_image_response.json").is_file()


def test_main_without_arguments_prompts_for_image_and_feature(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    image_dir = tmp_path / "images"
    image_dir.mkdir()
    for name in ["b.png", "a.jpg", ".DS_Store"]:
        (image_dir / name).write_bytes(b"synthetic")
    prompt = FakePrompt({"image": "b.png", "feature": "TEXT_DETECTION"})
    client = FakeClient(hello_response())

    code = run_main(
        ["--image-dir", str(image_dir), "--output", str(tmp_path / "r.json")], client, prompt
    )

    assert code == 0
    assert [q.name for q in prompt.questions] == ["image", "feature"]
    assert prompt.questions[0].choices == ["a.jpg", "b.png"]
    assert prompt.questions[1].choices == ["TEXT_DETECTION", "DOCUMENT_TEXT_DETECTION"]
    assert client.calls[0][0].image.content == b"synthetic"
    assert "Hello, Vision API!" in capsys.readouterr().out


def test_main_prompts_only_for_missing_feature(image: Path, tmp_path: Path) -> None:
    prompt = FakePrompt({"feature": "DOCUMENT_TEXT_DETECTION"})
    client = FakeClient(hello_response())

    assert run_main([str(image), "--output", str(tmp_path / "r.json")], client, prompt) == 0

    assert [q.name for q in prompt.questions] == ["feature"]
    assert client.calls[0][0].features[0].type_ == vision.Feature.Type.DOCUMENT_TEXT_DETECTION


def test_main_returns_1_when_prompt_is_cancelled(
    image: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    client = FakeClient(hello_response())

    assert run_main([str(image)], client, FakePrompt(None)) == 1

    assert client.calls == []
    assert "選択がキャンセルされた" in capsys.readouterr().err


def test_main_reports_empty_image_dir(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert run_main(["--image-dir", str(tmp_path)], FakeClient(hello_response())) == 1

    assert "画像が見つからない" in capsys.readouterr().err


def test_main_reports_missing_image_dir(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert run_main(["--image-dir", str(tmp_path / "nope")], FakeClient(hello_response())) == 1

    assert "画像ディレクトリ" in capsys.readouterr().err


def test_main_reports_missing_image_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    missing = tmp_path / "missing.png"
    client = FakeClient(hello_response())

    assert run_main([str(missing), "--feature", "TEXT_DETECTION"], client) == 1

    assert client.calls == []
    assert "画像を読めなかった" in capsys.readouterr().err


def test_main_reports_when_no_text_is_found(
    image: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    output = tmp_path / "r.json"
    client = FakeClient(vision.AnnotateImageResponse())

    code = run_main([str(image), "--feature", "TEXT_DETECTION", "--output", str(output)], client)

    assert code == 0
    assert "テキストが見つからなかった" in capsys.readouterr().out
    assert not output.exists()


@pytest.mark.parametrize(
    ("client", "message"),
    [
        (
            FakeClient(vision.AnnotateImageResponse(error={"code": 3, "message": "Bad image."})),
            "Bad image.",
        ),
        (
            FakeClient(api_exceptions.DeadlineExceeded("timed out")),  # type: ignore[no-untyped-call]
            "timed out",
        ),
        (
            auth_exceptions.DefaultCredentialsError("no adc"),  # type: ignore[no-untyped-call]
            "GOOGLE_APPLICATION_CREDENTIALS",
        ),
    ],
    ids=["response-error", "api-exception", "credentials"],
)
def test_main_reports_api_and_auth_errors(
    image: Path,
    tmp_path: Path,
    client: FakeClient | Exception,
    message: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output = tmp_path / "r.json"

    code = run_main([str(image), "--feature", "TEXT_DETECTION", "--output", str(output)], client)

    assert code == 1
    assert message in capsys.readouterr().err
    assert not output.exists()


def test_main_reports_unwritable_output(
    image: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # 出力先がディレクトリだと書き込めない
    code = run_main(
        [str(image), "--feature", "TEXT_DETECTION", "--output", str(tmp_path)],
        FakeClient(hello_response()),
    )

    assert code == 1
    captured = capsys.readouterr()
    assert "Hello, Vision API!" in captured.out
    assert "JSON を書き出せなかった" in captured.err


@pytest.mark.parametrize("value", ["0", "-1", "abc", "nan", "inf"])
def test_main_rejects_invalid_timeout(image: Path, value: str) -> None:
    with pytest.raises(SystemExit) as exc_info:
        run_main([str(image), "--timeout", value], FakeClient(hello_response()))

    assert exc_info.value.code == 2


def test_main_rejects_unknown_feature(image: Path) -> None:
    with pytest.raises(SystemExit) as exc_info:
        run_main([str(image), "--feature", "LABEL_DETECTION"], FakeClient(hello_response()))

    assert exc_info.value.code == 2


def test_run_exits_with_main_return_code(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli, "main", lambda: 7)

    with pytest.raises(SystemExit) as exc_info:
        cli.run()

    assert exc_info.value.code == 7


def test_module_entry_point_shows_help(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("sys.argv", ["vision-sandbox", "--help"])

    with pytest.raises(SystemExit) as exc_info:
        runpy.run_module("vision_sandbox", run_name="__main__")

    assert exc_info.value.code == 0
    assert "usage: vision-sandbox" in capsys.readouterr().out
