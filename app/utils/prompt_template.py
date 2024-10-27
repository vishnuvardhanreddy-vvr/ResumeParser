import requests
import os

from dotenv import load_dotenv
load_dotenv()





def gemini_model(prompt):
    # Set your Gemini API key (replace with your actual API key)
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    
    # URL endpoint for the Gemini model
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={GEMINI_API_KEY}"
    
    # Headers
    headers = {
        'Content-Type': 'application/json'
    }
    
    # Payload with the prompt
    data = {
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt
                    }
                ]
            }
        ]
    }
    
    # Make the POST request
    response = requests.post(url, headers=headers, json=data)
    
    # Check response status and return result
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"API call failed: {response.status_code} - {response.text}")