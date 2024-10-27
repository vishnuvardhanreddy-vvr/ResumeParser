import os
import logging
import json
import re


from app.utils.file_converstions import read_docx, read_pdf
from app.utils.llm import llm_model
from app.resume.prompt import resume_prompt as resume_parser_prompt


class ResumeParser():
    def __init__(self,file,file_name):
        self.temp_folder_path = ""
        self.file = file
        self.file_name = file_name
        self.result = None
        self.response = None
    
    def parse_resume(self):
        file = self.file
        file_extension = self.file_name.split(".")[1]
        if file_extension ==".pdf" or file_extension == "pdf":
           self.result = read_pdf(self.file)
           prompt = resume_parser_prompt.replace("resume_text",self.result)
           self.result = llm_model(prompt)
        elif file_extension == ".docx" or file_extension == "docx":
            self.result = read_docx(self.file)
            prompt = resume_parser_prompt.replace("resume_text",self.result)
            self.result = llm_model(prompt)
        else:
            self.result = None
        
        if self.result and not self.result.get("error"):
            self.response = {"response":{"parsed_resume":self.result},"status_code":200}
        elif self.result and self.result.get("error"):
            self.response = {"response":self.result,"status_code":400}
        else:
            self.response = {"response":{"message":"something went wrong","parsed_resume":self.result},"status_code":500}
        return self.response