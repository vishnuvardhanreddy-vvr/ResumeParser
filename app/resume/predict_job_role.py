import os
import logging
import json
import re
from app.utils.llm import llm_model
from app.resume.prompt import job_role

from dotenv import load_dotenv
load_dotenv()



def get_job_role(json_data):
    prompt = job_role.replace("resume_json", str(json_data))
    if json_data:
        response = llm_model(prompt)
        return {"response":{"parsed_resume":json_data,"suitable_job_role":response},"status_code":200}
    else:
        return {"response":{"error":"Provide resume to extract Suitable Job Role"},"status_code":400}
