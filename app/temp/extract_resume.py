import os
import fitz
import shutil
import logging
import pypandoc
from io import BytesIO
import base64
import json
from fastapi.responses import StreamingResponse
from app.utils.llm import get_llm
from app.utils.document_to_image import pdf_to_image
from app.services.fetch_lightcast_skills import lightcast_resume_extractor
from docx import Document
import subprocess
import fitz  # PyMuPDF
from PIL import Image
import pytesseract
import io


class Resume:
    def __init__(self, file, filename):
        self.file = file
        self.filename = filename
        self.output_path = "temp/"
        self.result = None

    async def extract(self):
        file_path = self.output_path
        if not os.path.exists(file_path):
            os.makedirs(file_path)

        doc = os.path.join(file_path, self.filename)
        with open(doc, "wb") as f:
            f.write(self.file)

        file_extension = os.path.splitext(doc)[1].lower()
        word_to_pdf = None

        if file_extension in [".doc", ".docx"]:
            # logging.info(f"Converting {file_extension} to .pdf")
            # doc = self.convert_to_pdf(doc)
            word_content = None

            word_to_pdf = convert_word_to_pdf(doc)

            if word_to_pdf is None:
                if file_extension == ".docx" or file_extension == "docx":
                    word_content = read_docx_text(doc)
                    logging.info(f"docx file content : {word_content}")
                    logging.info(f"extraction for word document using llm is started")
                    self.result = await llm_response_with_text(text=word_content)
                elif file_extension == ".doc" or file_extension == "doc":
                    word_content = read_doc_text(doc)
                    logging.info(f"doc file content : {word_content}")
                    logging.info(f"extraction for word document using llm is started")
                    self.result = await llm_response_with_text(text=word_content)

                # Assuming lightcast_resume_extractor returns some data based on the file
                self.result = await lightcast_resume_extractor(file=doc,extracted_json=self.result)
            doc = word_to_pdf

        if os.path.splitext(doc)[1] == ".pdf":
            is_text = False
            logging.info("PDF to image conversion process started")
            pdf_content = read_pdf_text(doc)
            logging.info(f"pdf file content : {pdf_content}")
            image = pdf_to_image(doc)
            self.result = await llm_response(image)
            if is_scanned_pdf(doc):
                logging.info(
                    f"uploaded pdf is a scanned pdf so extracting text from scanned pdf.")
                doc = pdf_content
                is_text = True
            self.result = await lightcast_resume_extractor(
                file=doc, extracted_json=self.result, is_text=is_text)
        else:
            raise ValueError("Unsupported file type")

        return self.result

    def convert_to_pdf(self, input_path):
        output_path = input_path.replace(
            os.path.splitext(input_path)[1], ".pdf")
        pypandoc.convert_file(input_path, to='pdf', outputfile=output_path)
        return output_path

    def convert_image(self):
        file_path = self.output_path
        if not os.path.exists(file_path):
            os.makedirs(file_path)
        # elif os.path.exists(file_path):
        #     shutil.rmtree(file_path)

        doc = os.path.join(file_path, self.filename)
        # Saving file to the directory where the file conversion process executes
        with open(doc, "wb") as f:
            f.write(self.file)
        file_extension = os.path.splitext(doc)[1]
        # check for the file format
        if file_extension == ".pdf":
            logging.info("pdf to image conversion process started")
            image = pdf_to_image(doc)
            image_data = base64.b64decode(image)
            image_io = BytesIO(image_data)
            shutil.rmtree(file_path)
            return StreamingResponse(image_io, media_type="image/png")

    def split_pdf(self):
        input_path = self.file
        output_path = self.output_path

        if not os.path.exists(output_path):
            os.makedirs(output_path)

        pdf = fitz.open(input_path)
        num_pages = len(pdf)

        for i in range(num_pages):
            pdf_writer = fitz.open()
            pdf_writer.insert_pdf(pdf, from_page=i, to_page=i)
            pdf_writer.save(f"{output_path}/page_{i + 1}.pdf")

        pdf.close()

        return [os.path.join(output_path, f"page_{i + 1}.pdf") for i in range(num_pages)]

    def clean_directory(self):
        shutil.rmtree(self.output_path)


def read_docx_text(file_path):
    document = Document(file_path)
    text = []
    for paragraph in document.paragraphs:
        text.append(paragraph.text)
    return '\n'.join(text)


def read_doc_text(file_path):
    result = subprocess.run(['antiword', file_path],
                            capture_output=True, text=True)
    if result.returncode == 0:
        return result.stdout
    else:
        return None


def read_pdf_text(file_path):
    text = ""
    # Open the PDF file
    with fitz.open(file_path) as pdf:
        # Iterate through each page
        for page in pdf:
            page_text = page.get_text()  # Extract text from the page
            if page_text.strip():  # If text is found, append it
                text += page_text
            else:  # If no text, perform OCR
                pix = page.get_pixmap()  # Render the page to an image
                img = Image.open(io.BytesIO(pix.tobytes())
                                 )  # Convert to PIL image
                text += pytesseract.image_to_string(img)  # Perform OCR
    return text

def convert_word_to_pdf(file_path):
    result = None

    # Check if the file exists
    if not os.path.isfile(file_path):
        logging.error(f"File does not exist: {file_path}")
        return None

    # Construct the command
    # command = ['libreoffice', '--headless', '--convert-to', 'pdf', file_path]
    output_dir = file_path.split("/")[0]
    command = ['libreoffice', '--headless', '--convert-to', 'pdf', '--outdir', output_dir, file_path]
    logging.info(f"Executing command: {' '.join(command)}")
    
    try:
        # Execute the command with the original file's directory as the working directory
        subprocess.run(command, check=True)
        result = os.path.splitext(file_path)[0] + '.pdf'  # Path of the new PDF
        logging.info(f"Converted: {file_path} to {result}.")
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to convert {file_path}: {e}")
    
    return result



def is_scanned_pdf(file_path):
    # Open the PDF file
    with fitz.open(file_path) as pdf:
        # Iterate through each page
        for page in pdf:
            text = page.get_text()  # Extract text from the page
            if text.strip():  # If text is found, it's not a scanned PDF
                return False
    # If no text is found on any page, it's likely a scanned PDF
    return True


def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')


class PromptTemplate:
    extractPrompt = '''
Please follow these instructions to detect the document type and extract resume data only if the document is identified as a resume. Return the extracted data in JSON format.

Step 1: **Document Type Detection**:
    - Analyze the provided document to determine if it is a resume.
    - If the document is not a resume, respond with the message: "Invalid document: The provided document is not a resume." No further action is needed in this case.

Step 2: **Resume Data Extraction** (only if Step 1 confirms the document is a resume):
    - Extract relevant information from the resume file.
    - Identify the job family (career_field) to which the user's resume belongs.

Skills and Proficiency:
    - List skill names along with their proficiency levels, rated between 1 (lowest) and 7 (highest).
    - Dynamically categorize each skill as either "business" or "technical" based on your knowledge.
    - Also populate the O*NET skill name, according to the skill name.

Recent Job Title:
    - Extract the most recent job title from the user's work experience.

Validation:
    - If the file is not a resume, respond with "Invalid document: The provided document is not a resume."

Text Length Constraints:
    - Ensure key_responsibility, summary, and learning_outcome texts are between 50 and 100 characters.

Career Field:
    - Based on the user resume, pick the correct career_field within the existing career_field list.
    - Only create a new career_field if the resume doesn't fit into any of the existing categories.

Example response (for a valid resume):

{
    "person": {
      "name": {
        "formattedName": "Sumit Kumar",
        "given": "Sumit",
        "family": "Kumar"
      },
      "communication": {
        "phone": [
          {
            "formattedNumber": "+91-9798141114"
          }
        ],
        "email": [
          {
            "address": "sumitphd13@gmail.com"
          }
        ],
        "web": [
          {
            "url": "http://www.linkedin.com/in/dr-sumit-kumar-8572aa213"
          },
          {
            "url": "http://www.scholar.google.com/citations"
          },
          {
            "url": "https://www.researchgate.net/profile/Sumit-Kumar-80"
          }
        ]
      },
      "birthDate": "1987-11-15"
    },
    "education": [
        {
            "institution_name": "University of Pennsylvania",
            "degree": "Bachelors",
            "field_of_study": "Marketing & Communication",
            "graduated_date": "2017-05-15"
        }
    ],
    "work_experience": [
        {
            "job_title": "Marketing Executive",
            "company_name": "Hilton",
            "start_date": "2017-06-01",
            "end_date": "2020-08-15",
            "key_responsibility": "Building and running digital campaigns for Hilton's America's region"
        },
        {
            "job_title": "Senior Marketing Manager",
            "company_name": "Ritz-Carlton",
            "start_date": "2024-03-01",
            "end_date": "current",
            "key_responsibility": "Responsible for global digital and physical marketing teams for Resorts"
        }
    ],
    "skills": [
        {
            "skill_name": "Business Communication",
            "proficiency_level": "5",
            "skill_type": "Business",
            "onet_name": "Interpersonal Communication"
        },
        {
            "skill_name": "Financial Management",
            "proficiency_level": "3",
            "skill_type": "Business",
            "onet_name": "Financial Planning"
        },
        {
            "skill_name": "MS Excel",
            "proficiency_level": "6",
            "skill_type": "Technical"
        }
    ],
    "certifications": [
        {
            "certification_name": "Digital Marketing",
            "issuing_organization": "Wharton Business School",
            "issue_date": "2021-01-15",
            "learning_outcome": "Leverage new models in business and e-commerce to increase profitability, specifically focusing on the right metrics to gauge and guide ongoing customer-centric efforts."
        }
    ],
    "career_field": "Marketing",
    "recent_job_title": "Senior Marketing Manager"
}

'''
    validate_resume = '''
You will receive JSON data containing resume information. Your task is to verify whether the provided resume data is valid based on the example of a valid resume given in the example response.

### Input:
- A JSON object containing resume data with fields such as name, contact information, education, work experience, skills, etc.

Output:
{
    "is_resume":"Yes"
}
'''

    @staticmethod
    async def azure_openai_text_template(client, deployment, text):
        prompt = PromptTemplate.extractPrompt
        response = await client.chat.completions.create(
            model=deployment,
            messages=[
                {"role": "system",
                    "content": "You are an information extractor from a given resume"},
                {"role": "user", "content": [
                    {"type": "text", "text": prompt},
                    {"type": "text", "text":text}
                ]}
            ],
            max_tokens=3700,
            temperature=0
        )
        return response

    @staticmethod
    async def azure_openai_image_template(client, deployment, base64_image):
        prompt = PromptTemplate.extractPrompt
        response = await client.chat.completions.create(
            model=deployment,
            messages=[
                {"role": "system",
                    "content": "You are an information extractor from a given resume"},
                {"role": "user", "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {
                        "url": f"data:image/jpeg;base64,{base64_image}"}}
                ]}
            ],
            max_tokens=3700,
            temperature=0
        )
        return response

    @staticmethod
    async def azure_openai_multiple_images_template(client, deployment, base64_image_list):
        prompt = PromptTemplate.extractPrompt
        response = await client.chat.completions.create(
            model=deployment,
            messages=[
                {"role": "system",
                    "content": "You are an information extractor from a given resume"},
                {"role": "user", "content": [
                    {"type": "text", "text": prompt},
                    *[{"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image}"}} for image in base64_image_list]
                ]}
            ],
            max_tokens=3700,
            temperature=0
        )
        return response


async def llm_response(image):
    response = False
    logging.info("LLM response function started")

    client, deployment = get_llm()

    try:
        logging.info("LLM started reading image content")
        response = await PromptTemplate.azure_openai_image_template(
            client, deployment, image)

        if response is None:
            raise ValueError("Received None from LLM response")

        result = response.choices[0].message.content

        # Formatting response to get desired output
        cleaned_json_string = result.removeprefix(
            "```json").removesuffix("```")
        cleaned_json_string = cleaned_json_string.replace(
            "\\n", "").replace("\\", "")

        logging.info(f"Cleaned JSON string length: {len(cleaned_json_string)}")
        results = json.loads(cleaned_json_string)
        logging.info("Response Received from LLM")

        if len(results.get("work_experience", [])) > 0 and results.get("career_field") is not None:
            return {"response": results, "status_code": 200}
        else:
            return {"response": {"message": "Your resume seems a bit light, can you add a bit more depth to your resume and share again?",
                                 "description": "LLM is not able to get enough data from the resume"}, "status_code": 400}

    except Exception as e:
        logging.error(f"Exception at LLM call: {e}")
        return {"response": {"message": "We are not able to extract the details",
                             "error": "Unprocessable Entity",
                             "description": f"Error occurred while generating response: {e}"},
                "status_code": 422}


async def llm_response_multiple_images(image_list):
    response = False
    logging.info("LLM response function for multiple images started")

    client, deployment = get_llm()

    try:
        logging.info("LLM started reading images content")
        response = await PromptTemplate.azure_openai_multiple_images_template(
            client, deployment, image_list)

        if response is None:
            raise ValueError("Received None from LLM response")

        result = response.choices[0].message.content

        # Formatting response to get desired output
        cleaned_json_string = result.removeprefix(
            "```json").removesuffix("```")
        cleaned_json_string = cleaned_json_string.replace(
            "\\n", "").replace("\\", "")

        logging.info(f"Cleaned JSON string length: {len(cleaned_json_string)}")
        results = json.loads(cleaned_json_string)
        logging.info("Response Received from LLM")

        if len(results.get("work_experience", [])) > 0 and results.get("career_field") is not None:
            return {"response": results, "status_code": 200}
        else:
            return {"response": {"message": "Your resume seems a bit light, can you add a bit more depth to your resume and share again?",
                                 "description": "LLM is not able to get enough data from the resume"}, "status_code": 400}

    except Exception as e:
        logging.error(f"Exception at LLM call: {e}")
        return {"response": {"message": "We are not able to extract the details",
                             "error": "Unprocessable Entity",
                             "description": f"Error occurred while generating response: {e}"},
                "status_code": 422}


async def validate_resume(json_data):
    response = None
    client, deployment = get_llm()

    try:
        prompt = PromptTemplate.validate_resume
        response = await client.chat.completions.create(
            model=deployment,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": [
                    {"type": "text", "text": json.dumps(json_data)}
                ]
                }
            ],
            max_tokens=3700,
            temperature=0
        )

        if response is None:
            raise ValueError("Received None from LLM response")

        result = response.choices[0].message.content

        # Formatting response to get desired output
        cleaned_json_string = result.removeprefix(
            "```json").removesuffix("```")
        cleaned_json_string = cleaned_json_string.replace(
            "\\n", "").replace("\\", "")

        results = json.loads(cleaned_json_string)

        is_resume = results.get("is_resume")
        if is_resume.lower() == "yes":
            is_resume = True
        else:
            is_resume = False

        if type(results) == dict and is_resume == True:
            response = {"response": {"is_resume": is_resume,
                                     "data": json_data}, "status_code": 200}
        else:
            response = {"response": {"is_resume": is_resume,
                                     "data": json_data}, "status_code": 400}
    except Exception as e:
        logging.error(f"Error Occured : {str(e)}")
        logging.exception(str(e))
        response = {"response": {"message": "something went to wrong",
                                 "error": str(e)}, "status_code": 500}
    finally:
        return response


async def llm_response_with_text(text):
    response = False
    logging.info("LLM response function started")

    client, deployment = get_llm()

    try:
        logging.info("LLM started reading image content")
        response = await PromptTemplate.azure_openai_text_template(
            client, deployment, text)

        if response is None:
            raise ValueError("Received None from LLM response")

        result = response.choices[0].message.content

        # Formatting response to get desired output
        cleaned_json_string = result.removeprefix(
            "```json").removesuffix("```")
        cleaned_json_string = cleaned_json_string.replace(
            "\\n", "").replace("\\"
