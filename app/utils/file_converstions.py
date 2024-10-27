from PIL import Image
import pytesseract
import fitz
from docx import Document
from io import BytesIO

def ocr_image_to_text(image_path):
    # Open the image using Pillow
    image = Image.open(image_path)
    # Use pytesseract to do OCR on the image
    text = pytesseract.image_to_string(image)
    return text


def read_pdf(file):
    text = ""
    with fitz.open(stream=file, filetype="pdf") as pdf_document:
        for page in pdf_document:
            text += page.get_text() + "\n"
    return text

def read_docx(file):
    file = BytesIO(file)
    doc = Document(file)
    text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
    return text
