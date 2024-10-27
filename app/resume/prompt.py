prompt = """
I have a resume in plain text format.  Please extract the following information from it and present it as a valid JSON object:

**Resume Text:**

resume_text

**Fields to Extract:**

* **name:** The full name of the candidate.
* **email:** The candidate's email address.
* **phone:** The candidate's phone number.
* **address:** The candidate's address.
* **experience:** A list of the candidate's work experience, including job title, company, and dates of employment. 
* **education:** A list of the candidate's education, including degree, institution, and dates of attendance.
* **skills:** A list of the candidate's skills.

**Example of Expected JSON Output:**

{
  "name": "John Doe",
  "email": "john.doe@email.com",
  "phone": "(123) 456-7890",
  "address": "123 Main Street, Anytown, CA 12345",
  "experience": [
    { "title": "Software Engineer", "company": "Google", "dates": "2020-Present" },
    { "title": "Web Developer", "company": "Acme Inc.", "dates": "2018-2020" }
  ],
  "education": [
    { "degree": "Master of Science", "institution": "Stanford University", "dates": "2018-2020" },
    { "degree": "Bachelor of Arts", "institution": "University of California, Berkeley", "dates": "2014-2018" }
  ],
  "skills": [
    "Python", "Java", "JavaScript", "SQL", "Machine Learning"
  ]
}

"""

resume_prompt = """
I have a resume in plain text format.  Please extract the following information from it and present it as a valid JSON object:

**Resume Text:**

resume_text

**Fields to Extract:**

* **name:** The full name of the candidate.
* **email:** The candidate's email address.
* **phone:** The candidate's phone number.
* **address:** The candidate's address.
* **experience:** A list of the candidate's work experience, including job title, company, and dates of employment. 
* **education:** A list of the candidate's education, including degree, institution, and dates of attendance.
* **skills:** A list of the candidate's skills.

**Example of Expected JSON Output:**

{
  "name": "John Doe",
  "email": "john.doe@email.com",
  "phone": "(123) 456-7890",
  "address": "123 Main Street, Anytown, CA 12345",
  "experience": [
    { "title": "Software Engineer", "company": "Google", "dates": "2020-Present" },
    { "title": "Web Developer", "company": "Acme Inc.", "dates": "2018-2020" }
  ],
  "education": [
    { "degree": "Master of Science", "institution": "Stanford University", "dates": "2018-2020" },
    { "degree": "Bachelor of Arts", "institution": "University of California, Berkeley", "dates": "2014-2018" }
  ],
  "skills": [
    "Python", "Java", "JavaScript", "SQL", "Machine Learning"
  ]
}


**Instructions**
* If given Resume Text is not a valid resume means if the text does not seem like resume then return JSON object.
* Follow the exact structure as below Invalid Resume Example.
* Do not include any other explanation or text.

**Fields**:
* **error:** This is not a valid resume.
* **description:** In Json description can be reason why it is considered as not a valid resume.

Invalid Resume Example :
{
"error":"This is not a valid resume",
"description":"Uploaded file does not contain information about resume"
}
"""

job_role = """
I have a json which has resume data.  Please extract the information from it and suggest the suitable job role and industry. Present it as a valid JSON object:

**Resume Json:**

resume_json

**Fields to Extract:**

* **job_role:** suitable job role based on skills and projects exist in Resume Json.
* **industry:** Industry or field that job role belongs to.

**Example of Expected JSON Output:**

{
  "job_role":"Associate Software Engineer",
  "industry":"Software/IT"
}

"""