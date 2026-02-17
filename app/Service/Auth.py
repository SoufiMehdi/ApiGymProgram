import os
from fastapi import Security, HTTPException, status
from fastapi.security.api_key import APIKeyHeader
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_KEY")
api_key_header = APIKeyHeader(name="x-api-key", auto_error=True)


async def verify_api_key(key: str = Security(api_key_header)):
    if key != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Clé API invalide"
        )
    return key