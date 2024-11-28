import cv2
import pymupdf
import base64
import numpy as np

class MergeImage:
    def __init__(self, initial_image):
        self.merge_image = initial_image
        self.x, self.y = self.merge_image.shape[:2]

    def append(self, image):
        image = image[:, :, :3]
        x, y = image.shape[:2]
        new_image = cv2.resize(image, (int(y * float(self.x) / x), self.x))
        self.merge_image = np.hstack((self.merge_image, new_image))

def pdf_to_image(pdf_path):
    mergedImage = ''
    doc = pymupdf.open(pdf_path)  # Open document
    for page in doc:  # Iterate through the pages
        np_arr = np.frombuffer(page.get_pixmap().tobytes(), np.uint8)
        image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)  # Render page to an image
        if page.number == 0:
            mergedImage = MergeImage(image)
        else:
            mergedImage.append(image)
    _, buffer = cv2.imencode('.png', mergedImage.merge_image)
    base64Image = base64.b64encode(buffer).decode('utf-8')
    return base64Image

def pdf_to_multiple_images(pdf_path):
    image_list = []
    doc = pymupdf.open(pdf_path)  # Open document
    for page in doc:  # Iterate through the pages
        np_arr = np.frombuffer(page.get_pixmap().tobytes(), np.uint8)
        image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)  # Render page to an image
        image_list.append(get_base64_image(image))
    return image_list

def get_base64_image(image):
    _, buffer = cv2.imencode('.png', image)
    base64Image = base64.b64encode(buffer).decode('utf-8')
    return base64Image

def images_to_base64(image_list):
    return [get_base64_image(cv2.imread(img_path)) for img_path in image_list]
