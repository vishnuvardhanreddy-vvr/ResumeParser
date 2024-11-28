import os
import jwt
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse
from jwt import PyJWTError
import logging

# Load the public key from environment variables
public_key = os.getenv("public-key")
if not public_key:
    raise ValueError("PUBLIC_KEY environment variable must be set")

# Middleware class to handle JWT validation for all incoming requests
class TokenMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        
        public_endpoints = os.getenv("public-endpoints",[])  # Add your public endpoint(s) here
        public_endpoints = string_to_list(public_endpoints)

        # Check if the request path is one of the public endpoints
        if request.url.path in public_endpoints:
            # Skip token validation for this route
            response = await call_next(request)
            return response

        # Allow local development to bypass token validation
        if os.environ.get("ENV", None) == "local":
            # Set a default role for local development
            request.state.role = "local-user"
            response = await call_next(request)
            return response

        # Get the token from the Authorization header (Bearer token)
        authorization = request.headers.get("Authorization")
        
        if not authorization:
            return JSONResponse(status_code=401, content={"error": "Token is missing"})
        
        if not authorization.startswith("Bearer "):
            return JSONResponse(status_code=401, content={"error": "Invalid token format"})

        token = authorization[len("Bearer "):]

        # Decode and validate the token directly inside the middleware
        try:
            # Decode the JWT token using the public key (RS256 algorithm)
            payload = jwt.decode(token, public_key, algorithms=["RS256"], options={"verify_iat": False})

            role = payload.get("extension_Roles")

            user_id = payload.get("user_id")

            roles = os.getenv("roles",[])
            
            roles = string_to_list(roles)

            if role not in roles:
                return JSONResponse(status_code=401, content={"error": "You are not allowed to use this API"})
            
            logging.info(f"successfully verified token")
            
            if role:
                request.state.role = role
                
            if user_id:
                request.state.user_id = user_id

        except PyJWTError as e:
            logging.error(str(e))
            return JSONResponse(status_code=401, content={"error": f"Token decode error: {str(e)}"})

        response = await call_next(request)
        return response
    
def string_to_list(string):
    if isinstance(string, str):
        return string.split(",")
    return string
