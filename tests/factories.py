"""テスト用に Vision SDK のレスポンスを組み立てる。値はすべて架空のもの。"""

from google.cloud import vision

BreakType = vision.TextAnnotation.DetectedBreak.BreakType


def symbol(text: str, brk: int | None = None) -> vision.Symbol:
    if brk is None:
        return vision.Symbol(text=text)
    detected = vision.TextAnnotation.DetectedBreak(type_=brk)
    return vision.Symbol(
        text=text, property=vision.TextAnnotation.TextProperty(detected_break=detected)
    )


def word(*symbols: vision.Symbol) -> vision.Word:
    return vision.Word(symbols=list(symbols))


def paragraph(words: list[vision.Word], vertices: list[tuple[int, int]]) -> vision.Paragraph:
    poly = vision.BoundingPoly(vertices=[vision.Vertex(x=x, y=y) for x, y in vertices])
    return vision.Paragraph(words=words, bounding_box=poly)


def response(*pages: list[list[vision.Paragraph]]) -> vision.AnnotateImageResponse:
    """pages は「ページ > ブロック > 段落」の入れ子リスト。"""
    built = [
        vision.Page(blocks=[vision.Block(paragraphs=paragraphs) for paragraphs in blocks])
        for blocks in pages
    ]
    return vision.AnnotateImageResponse(
        full_text_annotation=vision.TextAnnotation(pages=built),
    )


SQUARE = [(40, 50), (360, 50), (360, 95), (40, 95)]


def hello_response() -> vision.AnnotateImageResponse:
    """合成画像の 1 行目 "Hello, Vision API!" を模したレスポンス。"""
    hello = word(*(symbol(c) for c in "Hello"), symbol(",", BreakType.SPACE))
    vision_word = word(*(symbol(c) for c in "Visio"), symbol("n", BreakType.SPACE))
    api = word(symbol("A"), symbol("P"), symbol("I"), symbol("!", BreakType.LINE_BREAK))
    return response([[paragraph([hello, vision_word, api], SQUARE)]])


class FakeClient:
    """ImageAnnotatorClient の代わり。リクエストを記録し、決めたレスポンスを返す。"""

    def __init__(self, result: vision.AnnotateImageResponse | Exception) -> None:
        self.result = result
        self.calls: list[tuple[vision.AnnotateImageRequest, float]] = []

    def annotate_image(
        self, request: vision.AnnotateImageRequest, *, timeout: float
    ) -> vision.AnnotateImageResponse:
        self.calls.append((request, timeout))
        if isinstance(self.result, Exception):
            raise self.result
        return self.result
