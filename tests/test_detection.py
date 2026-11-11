import json
from pathlib import Path

import pytest
from google.cloud import vision

from tests.factories import (
    SQUARE,
    BreakType,
    FakeClient,
    hello_response,
    paragraph,
    response,
    symbol,
    word,
)
from vision_sandbox.detection import (
    FEATURES,
    ParagraphText,
    VisionApiError,
    detect_text,
    extract_paragraphs,
    format_paragraphs,
    list_images,
    write_response_json,
)


def test_list_images_returns_sorted_image_files_only(tmp_path: Path) -> None:
    for name in ["b.PNG", "a.jpg", "c.webp", ".DS_Store", ".hidden.png", "notes.txt"]:
        (tmp_path / name).write_bytes(b"synthetic")
    (tmp_path / "dir.png").mkdir()

    assert [p.name for p in list_images(tmp_path)] == ["a.jpg", "b.PNG", "c.webp"]


def test_features_offer_text_and_document_detection() -> None:
    assert FEATURES == {
        "TEXT_DETECTION": vision.Feature.Type.TEXT_DETECTION,
        "DOCUMENT_TEXT_DETECTION": vision.Feature.Type.DOCUMENT_TEXT_DETECTION,
    }


def test_detect_text_sends_image_bytes_feature_and_timeout(tmp_path: Path) -> None:
    image = tmp_path / "synthetic.png"
    image.write_bytes(b"synthetic-image-bytes")
    client = FakeClient(hello_response())

    result = detect_text(image, FEATURES["DOCUMENT_TEXT_DETECTION"], client, timeout=12.5)

    assert result == hello_response()
    [(request, timeout)] = client.calls
    assert request.image.content == b"synthetic-image-bytes"
    assert [f.type_ for f in request.features] == [vision.Feature.Type.DOCUMENT_TEXT_DETECTION]
    assert timeout == 12.5


def test_detect_text_raises_when_response_has_error(tmp_path: Path) -> None:
    image = tmp_path / "synthetic.png"
    image.write_bytes(b"synthetic")
    failed = vision.AnnotateImageResponse(error={"code": 3, "message": "Bad image data."})

    with pytest.raises(VisionApiError, match=r"Bad image data\. \(code=3\)"):
        detect_text(image, FEATURES["TEXT_DETECTION"], FakeClient(failed), timeout=1)


def test_extract_paragraphs_joins_symbols_with_detected_breaks() -> None:
    assert extract_paragraphs(hello_response()) == [
        ParagraphText(0, 0, 0, "Hello, Vision API!", tuple(SQUARE)),
    ]


def test_extract_paragraphs_keeps_text_without_breaks_unsplit() -> None:
    # 日本語のように空白のない文は単語間に空白を入れない
    words = [word(symbol("合"), symbol("成")), word(symbol("画"), symbol("像", BreakType.HYPHEN))]
    result = response([[paragraph(words, SQUARE)]])

    assert extract_paragraphs(result)[0].text == "合成画像-"


def test_extract_paragraphs_covers_all_pages_and_irregular_boxes() -> None:
    first = paragraph([word(symbol("A"))], SQUARE)
    triangle = paragraph([word(symbol("B", BreakType.EOL_SURE_SPACE))], [(0, 0), (5, 0), (0, 5)])
    second = paragraph([word(symbol("C", BreakType.SURE_SPACE))], [])
    result = response([[first]], [[triangle], [second]])

    assert extract_paragraphs(result) == [
        ParagraphText(0, 0, 0, "A", tuple(SQUARE)),
        ParagraphText(1, 0, 0, "B", ((0, 0), (5, 0), (0, 5))),
        ParagraphText(1, 1, 0, "C", ()),
    ]


def test_extract_paragraphs_returns_empty_list_without_annotation() -> None:
    assert extract_paragraphs(vision.AnnotateImageResponse()) == []


def test_format_paragraphs_prints_headers_text_and_vertices() -> None:
    paragraphs = [
        ParagraphText(0, 0, 0, "Hello", ((1, 2), (3, 4))),
        ParagraphText(0, 0, 1, "World", ()),
        ParagraphText(1, 2, 0, "Next", ((5, 6),)),
    ]

    assert format_paragraphs(paragraphs) == (
        ">>>> page 0 / block 0\n"
        "    >>>> paragraph 0\n"
        "         Hello (1, 2) (3, 4)\n"
        "    >>>> paragraph 1\n"
        "         World\n"
        ">>>> page 1 / block 2\n"
        "    >>>> paragraph 0\n"
        "         Next (5, 6)"
    )


def test_write_response_json_creates_parent_and_keeps_unicode(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "out.json"
    result = vision.AnnotateImageResponse(
        full_text_annotation=vision.TextAnnotation(text="合成テキスト"),
    )

    write_response_json(result, path)

    raw = path.read_text(encoding="utf-8")
    assert "合成テキスト" in raw
    assert json.loads(raw)["fullTextAnnotation"]["text"] == "合成テキスト"


def test_detect_text_raises_when_response_has_error_code_only(tmp_path: Path) -> None:
    image = tmp_path / "synthetic.png"
    image.write_bytes(b"synthetic")
    failed = vision.AnnotateImageResponse(error={"code": 13})

    with pytest.raises(VisionApiError, match=r"\(code=13\)"):
        detect_text(image, FEATURES["TEXT_DETECTION"], FakeClient(failed), timeout=1)
