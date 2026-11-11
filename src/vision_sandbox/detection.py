"""Vision API でテキストを検出し、結果を段落単位に整形する。"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from google.cloud import vision

# 値は vision.Feature.Type (SDK の型情報では int 扱い)
FEATURES: dict[str, int] = {
    "TEXT_DETECTION": vision.Feature.Type.TEXT_DETECTION,
    "DOCUMENT_TEXT_DETECTION": vision.Feature.Type.DOCUMENT_TEXT_DETECTION,
}

# Vision API が受け付ける画像形式のうち、拡張子で判別できるもの
IMAGE_SUFFIXES = frozenset(
    {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".ico", ".tif", ".tiff"}
)

_BreakType = vision.TextAnnotation.DetectedBreak.BreakType
# 段落を 1 行で表示するため、改行系の区切りも空白として扱う
_BREAK_TEXT = {
    _BreakType.SPACE: " ",
    _BreakType.SURE_SPACE: " ",
    _BreakType.EOL_SURE_SPACE: " ",
    _BreakType.LINE_BREAK: " ",
    _BreakType.HYPHEN: "-",
}


class VisionApiError(RuntimeError):
    """API がレスポンスの error フィールドで失敗を返したときの例外。"""


class AnnotateClient(Protocol):
    """detect_text が必要とする ImageAnnotatorClient の部分。"""

    def annotate_image(
        self, request: vision.AnnotateImageRequest, *, timeout: float
    ) -> vision.AnnotateImageResponse: ...


@dataclass(frozen=True)
class ParagraphText:
    page: int
    block: int
    paragraph: int
    text: str
    vertices: tuple[tuple[int, int], ...]


def list_images(directory: Path) -> list[Path]:
    """ディレクトリ直下の画像ファイルを名前順に返す。隠しファイルは除く。"""
    return sorted(
        path
        for path in directory.iterdir()
        if path.is_file()
        and not path.name.startswith(".")
        and path.suffix.lower() in IMAGE_SUFFIXES
    )


def detect_text(
    path: Path, feature: int, client: AnnotateClient, *, timeout: float
) -> vision.AnnotateImageResponse:
    """画像を送ってテキストを検出する。API がエラーを返したら VisionApiError を送出する。"""
    request = vision.AnnotateImageRequest(
        image=vision.Image(content=path.read_bytes()),
        features=[vision.Feature(type_=feature)],
    )
    response = client.annotate_image(request, timeout=timeout)
    if response.error.code or response.error.message:
        raise VisionApiError(f"{response.error.message} (code={response.error.code})")
    return response


def _paragraph_text(paragraph: vision.Paragraph) -> str:
    parts: list[str] = []
    for word in paragraph.words:
        for symbol in word.symbols:
            parts.append(symbol.text)
            parts.append(_BREAK_TEXT.get(symbol.property.detected_break.type_, ""))
    return "".join(parts).strip()


def extract_paragraphs(response: vision.AnnotateImageResponse) -> list[ParagraphText]:
    """全ページの段落について、テキストとバウンディングボックスの頂点を取り出す。"""
    return [
        ParagraphText(
            page=page_index,
            block=block_index,
            paragraph=paragraph_index,
            text=_paragraph_text(paragraph),
            vertices=tuple((v.x, v.y) for v in paragraph.bounding_box.vertices),
        )
        for page_index, page in enumerate(response.full_text_annotation.pages)
        for block_index, block in enumerate(page.blocks)
        for paragraph_index, paragraph in enumerate(block.paragraphs)
    ]


def format_paragraphs(paragraphs: list[ParagraphText]) -> str:
    lines: list[str] = []
    for p in paragraphs:
        if p.paragraph == 0:
            lines.append(f">>>> page {p.page} / block {p.block}")
        lines.append(f"    >>>> paragraph {p.paragraph}")
        lines.append(" ".join(["        ", p.text, *(str(v) for v in p.vertices)]))
    return "\n".join(lines)


def write_response_json(response: vision.AnnotateImageResponse, path: Path) -> None:
    """レスポンス全体を、日本語をエスケープしない JSON で書き出す。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.loads(vision.AnnotateImageResponse.to_json(response))
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
