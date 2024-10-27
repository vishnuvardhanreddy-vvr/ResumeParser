from fastapi import FastAPI, Request, File, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.resume.extract_resume import ResumeParser


from dotenv import load_dotenv
load_dotenv()

app = FastAPI()


@app.get("/")
async def get_status():
    return JSONResponse(content={"status":"Ok"},status_code=200)


@app.post("/api/resume")
async def upload_resume_file(file: UploadFile = File(...)):
    response = {}
    try:
        file_name = file.filename
        file = await file.read()
        resume_parser = ResumeParser(file=file,file_name=file_name)
        parsed_text = resume_parser.parse_resume()
        if parsed_text:
            response = {"response":{"data":parsed_text},"status_code":200}
        else:
            response = {"response":{"data":parsed_text},"status_code":400}
    except Exception as e:
        response = {"response":{"error":str(e)},"status_code":500}
    finally:
        return JSONResponse(content=response.get("response"),status_code=response.get("status_code"))


@app.post("/api/job-role")
async def get_job_role():
    return JSONResponse(content={},status_code=200)