import os
import inquirer  # type: ignore
from google.cloud import vision  # type: ignore
# https://cloud.google.com/vision/docs/reference/rest/v1/AnnotateImageResponse
from google.cloud.vision_v1.types.image_annotator import AnnotateImageResponse


def main() -> None:
    file_list = os.listdir("./images/")
    image_file = choose_file(file_list)

    if image_file is None:
        print("ファイルが選択されなかったみたいだね...")
        return

    result: AnnotateImageResponse = detect_text(f"./images/{image_file}")

    if not result.full_text_annotation.pages:
        print("画像からテキストが見つからなかったみたいだね…")
        return

    process_result(result)


def choose_file(file_list: list[str]) -> str | None:
    """
    Prompts the user to choose a file from the given list of files.

    This function uses the inquirer library to present a list of files to the user in the console.
    The user can navigate through the list and select a file using the arrow keys and Enter key.

    Args:
        file_list (list[str]): List of file names to be presented to the user.

    Returns:
        str: The name of the file chosen by the user. If no file is chosen, returns None.
    """

    questions = [
        inquirer.List(
            'file',
            message="選んでね",
            choices=file_list,
        ),
    ]
    answers = inquirer.prompt(questions)

    return None if answers is None else answers['file']


def detect_text(path: str) -> AnnotateImageResponse:
    """
    Detects and extracts text from an image file using the Google Cloud Vision API's document_text_detection method.

    This function opens and reads an image file specified by the `path` argument,
    and sends the image content to the Google Cloud Vision API for text detection.
    It then returns the API response as an AnnotateImageResponse object, which
    contains the detected text and other information.

    Args:
        path (str): A string representing the path to the image file to be processed.

    Returns:
        AnnotateImageResponse: An object containing the detected text and other information from the image.
    """

    client = vision.ImageAnnotatorClient()

    with open(path, 'rb') as image_file:
        content = image_file.read()

    image = vision.Image(content=content)

    return client.document_text_detection(image=image)


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

    page = result.full_text_annotation.pages[0]
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
