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