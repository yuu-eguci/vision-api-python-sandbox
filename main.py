"""
pipenv run python main.py
"""

import os
import json
import inquirer  # type: ignore
from google.cloud import vision  # type: ignore
# https://cloud.google.com/vision/docs/reference/rest/v1/AnnotateImageResponse
from google.cloud.vision_v1.types.image_annotator import AnnotateImageResponse
from google.cloud.vision_v1.types import Feature


def main() -> None:
    file_list = os.listdir("./images/")
    image_file, detection_feature = choose_file_and_feature(file_list)

    if image_file is None or detection_feature is None:
        print("何か選ばなかったみたいだね...")
        return

    result: AnnotateImageResponse = detect_text(f"./images/{image_file}", detection_feature)

    if not result.full_text_annotation.pages:
        print("画像からテキストが見つからなかったみたいだね…")
        return

    process_result(result)


def choose_file_and_feature(file_list: list[str]) -> tuple[str | None, Feature.Type | None]:
    """
    ユーザーにファイルとテキスト検出の feature を選んでもらう。

    この関数は inquirer ライブラリを使って、コンソールにファイルリストとテキスト検出の feature を表示する。
    ユーザーは矢印キーと Enter キーで選択できる。

    Args:
        file_list (list[str]): ユーザーに提示するファイル名のリスト。

    Returns:
        tuple[str | None, Feature.Type | None]: ユーザーが選んだファイル名とテキスト検出の feature。
                                                何も選ばなければ None。
    """

    questions = [
        inquirer.List(
            'file',
            message="画像ファイルを選んでね",
            choices=file_list,
        ),
        inquirer.List(
            'feature',
            message="どのテキスト検出 feature にする？",
            choices=[t.name for t in [  # type: ignore # NOTE: enum には name があるから!!
                Feature.Type.TEXT_DETECTION,
                Feature.Type.DOCUMENT_TEXT_DETECTION,
            ]],
        ),
    ]
    answers = inquirer.prompt(questions)

    if answers is None:
        return None, None

    return answers['file'], Feature.Type[answers['feature']]  # type: ignore # NOTE: enum は indexable だから!!


def detect_text(path: str, feature_type: Feature.Type) -> AnnotateImageResponse:
    """
    Google Cloud Vision API のテキスト検出メソッドを使って、画像ファイルからテキストを検出・抽出する。

    Args:
        path (str): 処理する画像ファイルへのパス。
        feature_type (Feature.Type): 使用するテキスト検出の feature の型。

    Returns:
        AnnotateImageResponse: 画像から検出されたテキストとその他の情報を含むオブジェクト。
    """

    client = vision.ImageAnnotatorClient()

    with open(path, 'rb') as image_file:
        content = image_file.read()

    image = vision.Image(content=content)
    feature = Feature(type=feature_type)
    request = vision.AnnotateImageRequest(image=image, features=[feature])

    return client.annotate_image(request)


def process_result(result: AnnotateImageResponse) -> None:
    """
    Processes and prints the detected text and its location from an AnnotateImageResponse object.

    This function extracts the blocks of text from the first page of the `result` (AnnotateImageResponse object).
    For each block, it enumerates and prints the index of the block, each paragraph within the block,
    the combined text of each paragraph, and the coordinates of the bounding box around each paragraph.

    Args:
        result (AnnotateImageResponse): An object containing the detected text and other information from the image.

    Returns:
        None
    """

    with open('annotate_image_response.json', 'w') as f:
        json.dump(json.loads(AnnotateImageResponse.to_json(result)), f, indent=2, ensure_ascii=False)
    print('annotate_image_response.json へ、もともとの json を書き出したよ。')

    page = result.full_text_annotation.pages[0]

    # full_text_annotation の構造はなんかこんな感じ↓
    # pages: list[Page]
    #   blocks: list[Block]
    #     bounding_box: BoundingPoly
    #     paragraphs: list[Paragraph]
    #       bounding_box: BoundingPoly
    #       words: list[Word]
    #         bounding_box: BoundingPoly
    #         symbols: list[Symbol]
    #           bounding_box: BoundingPoly
    #           text: str
    # text: str
    # https://cloud.google.com/vision/docs/reference/rest/v1/AnnotateImageResponse#textannotation

    for block_index, block in enumerate(page.blocks):
        print(f">>>> block {block_index}")
        for paragraph_index, paragraph in enumerate(block.paragraphs):
            print(f"    >>>> paragraph {paragraph_index}")
            text = "         " + " ".join(
                "".join(symbol.text for symbol in word.symbols)
                for word in paragraph.words
            )
            vertices = paragraph.bounding_box.vertices
            left_top = (vertices[0].x, vertices[0].y)
            right_top = (vertices[1].x, vertices[1].y)
            right_bottom = (vertices[2].x, vertices[2].y)
            left_bottom = (vertices[3].x, vertices[3].y)
            print(text, left_top, right_top, right_bottom, left_bottom)


if __name__ == "__main__":
    main()
