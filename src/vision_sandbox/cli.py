"""画像とフィーチャーを選び、Vision API のテキスト検出結果を表示する CLI。"""

import argparse
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

import inquirer
from google.api_core import exceptions as api_exceptions
from google.auth import exceptions as auth_exceptions
from google.cloud import vision

from vision_sandbox.detection import (
    FEATURES,
    AnnotateClient,
    VisionApiError,
    detect_text,
    extract_paragraphs,
    format_paragraphs,
    list_images,
    write_response_json,
)

Prompt = Callable[[list[Any]], dict[str, str] | None]


def _positive_float(value: str) -> float:
    try:
        number = float(value)
    except ValueError:
        number = 0.0
    if number <= 0:
        raise argparse.ArgumentTypeError(f"正の数を指定してください: {value}")
    return number


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vision-sandbox",
        description="Google Cloud Vision API で画像のテキストを検出する (API 呼び出しは課金対象)",
    )
    parser.add_argument("image", nargs="?", type=Path, help="解析する画像。省略すると対話で選ぶ")
    parser.add_argument(
        "--image-dir", type=Path, default=Path("images"), help="対話選択で使う画像ディレクトリ"
    )
    parser.add_argument("--feature", choices=list(FEATURES), help="省略すると対話で選ぶ")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("output/annotate_image_response.json"),
        help="API レスポンス全体の JSON の書き出し先",
    )
    parser.add_argument(
        "--timeout", type=_positive_float, default=60.0, help="API 呼び出しのタイムアウト秒数"
    )
    return parser


class CliError(Exception):
    """利用者に伝えて終了コード 1 で終わるべき失敗。"""


def _choose(args: argparse.Namespace, prompt: Prompt) -> tuple[Path, int]:
    """引数で足りない画像とフィーチャーを対話で選んでもらう。"""
    image: Path | None = args.image
    feature_name: str | None = args.feature

    questions: list[Any] = []
    if image is None:
        try:
            images = list_images(args.image_dir)
        except OSError as e:
            raise CliError(f"画像ディレクトリを読めなかったよ: {e}") from e
        if not images:
            raise CliError(f"{args.image_dir} に画像が見つからないよ。")
        questions.append(
            inquirer.List(
                "image", message="画像ファイルを選んでね", choices=[p.name for p in images]
            )
        )
    if feature_name is None:
        questions.append(
            inquirer.List(
                "feature", message="どのテキスト検出 feature にする？", choices=list(FEATURES)
            )
        )

    answers: dict[str, str] = {}
    if questions:
        prompted = prompt(questions)
        if prompted is None:
            raise CliError("選択がキャンセルされたよ。")
        answers = prompted
    image_path = image if image is not None else args.image_dir / answers["image"]
    return image_path, FEATURES[feature_name or answers["feature"]]


def _detect(
    args: argparse.Namespace, prompt: Prompt, client_factory: Callable[[], AnnotateClient]
) -> vision.AnnotateImageResponse:
    image, feature = _choose(args, prompt)
    try:
        return detect_text(image, feature, client_factory(), timeout=args.timeout)
    except OSError as e:
        raise CliError(f"画像を読めなかったよ: {e}") from e
    except auth_exceptions.DefaultCredentialsError as e:
        message = f"認証情報が見つからないよ。GOOGLE_APPLICATION_CREDENTIALS を確認してね: {e}"
        raise CliError(message) from e
    except (api_exceptions.GoogleAPICallError, VisionApiError) as e:
        raise CliError(f"Vision API の呼び出しに失敗したよ: {e}") from e


def main(
    argv: Sequence[str] | None = None,
    *,
    client_factory: Callable[[], AnnotateClient] = vision.ImageAnnotatorClient,
    prompt: Prompt = inquirer.prompt,
) -> int:
    args = build_parser().parse_args(argv)
    try:
        response = _detect(args, prompt, client_factory)
    except CliError as e:
        print(e, file=sys.stderr)
        return 1

    paragraphs = extract_paragraphs(response)
    if not paragraphs:
        print("画像からテキストが見つからなかったみたいだね…")
        return 0

    write_response_json(response, args.output)
    print(format_paragraphs(paragraphs))
    print(f"{args.output} へ、もともとの JSON を書き出したよ。")
    return 0


def run() -> None:
    sys.exit(main())
