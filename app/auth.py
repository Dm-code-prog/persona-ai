import os
import jwt
import base64

from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# Get the Supabase JWT secret from environment variables
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET")

if not SUPABASE_JWT_SECRET:
    raise ValueError("SUPABASE_JWT_SECRET is not set")

# Define authentication scheme
security = HTTPBearer()

def validate_jwt(token: str):
    """
    Validate and decode the JWT from Supabase.
    """
    try:
        payload = jwt.decode(token, key=SUPABASE_JWT_SECRET, algorithms=["HS256"], audience="authenticated")
        return payload  # Contains user information and claims
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)):
    """
    FastAPI dependency to extract and validate JWT from the Authorization header.
    """
    return validate_jwt(credentials.credentials)