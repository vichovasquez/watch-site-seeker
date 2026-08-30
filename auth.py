import os
import urllib.parse
import httpx
from fastapi import Request, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import base64
import json
import hmac
import hashlib
import time

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
SECRET_KEY = os.environ.get("SESSION_SECRET", "vicho-watch-finder-secret-key-392847")
ALLOWED_EMAILS = [
    e.strip().lower() 
    for e in os.environ.get("ALLOWED_EMAILS", "jvasquez8@gmail.com").split(",") 
    if e.strip()
]

SESSION_COOKIE_NAME = "vicho_auth_session"

def create_session_token(email: str) -> str:
    payload = {
        "email": email.lower(),
        "exp": int(time.time()) + (86400 * 14)  # 14 days
    }
    raw = json.dumps(payload).encode("utf-8")
    sig = hmac.new(SECRET_KEY.encode("utf-8"), raw, hashlib.sha256).hexdigest()
    token = f"{base64.urlsafe_b64encode(raw).decode('utf-8')}.{sig}"
    return token

def verify_session_token(token: str) -> str | None:
    if not token or "." not in token:
        return None
    try:
        raw_b64, sig = token.split(".", 1)
        raw = base64.urlsafe_b64decode(raw_b64.encode("utf-8"))
        expected_sig = hmac.new(SECRET_KEY.encode("utf-8"), raw, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected_sig):
            return None
        payload = json.loads(raw.decode("utf-8"))
        if payload.get("exp", 0) < time.time():
            return None
        return payload.get("email")
    except Exception:
        return None

def get_current_user_email(request: Request) -> str | None:
    # If Google OAuth is not configured, grant local dev access as jvasquez8@gmail.com
    if not GOOGLE_CLIENT_ID:
        return "jvasquez8@gmail.com"
    token = request.cookies.get(SESSION_COOKIE_NAME)
    return verify_session_token(token)

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        
        # Public bypass routes
        if path.startswith("/auth/") or path.startswith("/static/css/") or path.startswith("/static/js/") or path == "/favicon.ico":
            return await call_next(request)
            
        # Check authentication
        if GOOGLE_CLIENT_ID:
            token = request.cookies.get(SESSION_COOKIE_NAME)
            email = verify_session_token(token)
            
            if not email:
                if path.startswith("/api/"):
                    return JSONResponse(status_code=401, content={"error": "Unauthorized. Please sign in with Google."})
                return RedirectResponse(url="/auth/login", status_code=303)
                
            if email not in ALLOWED_EMAILS:
                if path.startswith("/api/"):
                    return JSONResponse(status_code=403, content={"error": f"Access forbidden. Account {email} is not authorized."})
                return RedirectResponse(url="/auth/denied", status_code=303)

        response = await call_next(request)
        return response
