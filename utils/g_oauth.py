import requests
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
import os


#===================================================
# WIZAI Cridential
CLIENT_ID =  ""
CLIENT_SECRET = ""
GOOGLE_CLIENT_SECRET  = "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" # os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI   = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/api/oauth/google/callback")
GOOGLE_SCOPES         = "https://www.googleapis.com/auth/adwords https://www.googleapis.com/auth/userinfo.email"
 
FRONTEND_URL          = "http://localhost:3000"

import requests

def verify_google_user(id_token: str):
    # Change the URL to the tokeninfo validation endpoint
    url = f"https://oauth2.googleapis.com/tokeninfo?id_token={id_token}"
    
    try:
        response = requests.get(url)
        user_info = response.json()
        
        # Google returns 'error' or 'error_description' if the JWT is invalid
        if response.status_code != 200 or "error" in user_info:
            print(f"Google Error Detail: {user_info}")
            return f"Google Error: {user_info.get('error_description', 'Invalid Token')}"
            
        return user_info
    except Exception as e:
        return f"Connection Error: {str(e)}"

# Use this ONLY if you are sending the 'ya29' token
import requests
from fastapi import HTTPException

def verify_google_user1(access_token: str):
    # This endpoint handles 'ya29...' style access tokens
    url = "https://www.googleapis.com/oauth2/v3/userinfo"
    headers = {"Authorization": f"Bearer {access_token}"}
    
    try:
        response = requests.get(url, headers=headers)
        user_info = response.json()
        
        if response.status_code != 200:
            print(f"Google Error Detail: {user_info}")
            return f"Google Error: {user_info.get('error_description', 'Invalid Token')}"
            
        return user_info
    except Exception as e:
        return f"Connection Error: {str(e)}"

