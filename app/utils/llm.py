import logging
import json
import re
import os

from app.utils.prompt_template import gemini_model
from dotenv import load_dotenv
load_dotenv()

def gemini_llm(input):
    response = gemini_model(input)
    response = response["candidates"][0]["content"]["parts"][0]["text"]
    # response = gemini_chain.run(input_json)
    logging.info(f"Gemini response: {response}")
    return response



def llm_model(input):
    response = ""
    try:
        current_model_name = os.getenv("CURRENT_LLM_MODEL")
        if current_model_name=="GEMINI":
            response = gemini_llm(input=input)
            response = format_llm_response(raw_response=response)
        else:
            response = {"response":{"error":"Only GEMINI model is available"},"status_code":400}
    except Exception as e:
        response = {"response":{"error":str(e)},"status_code":500}
    finally:
        return response


def format_llm_response(raw_response):
    try:
        if "`" in raw_response:
            raw_response = raw_response.replace("```json\n", "").replace("```", "").strip()
        if "**Explanation:**" in raw_response:
            raw_response = raw_response.split("**Explanation:**")[0]
        raw_response = json.loads(raw_response)
    except Exception as e:
        logging.error(f"Error occured : {str(e)}")
    
    return raw_response
    