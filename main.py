import os
import json
import csv
import io
import urllib.parse
import httpx
from fastapi import FastAPI, Request, HTTPException, Body, Depends
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Optional
import uvicorn

import sites_manager
import references_manager
from search_engine import MultiSiteSearcher
import auth
from auth import AuthMiddleware, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, ALLOWED_EMAILS, create_session_token, verify_session_token, SESSION_COOKIE_NAME, get_current_user_email

app = FastAPI(title="Vicho's Watch Finder", version="2.5.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(AuthMiddleware)

# Mount static files
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

searcher = MultiSiteSearcher(timeout=8.0)

# ================= AUTHENTICATION ROUTES =================

@app.get("/auth/login", response_class=HTMLResponse)
async def login_page(request: Request):
    token = request.cookies.get(SESSION_COOKIE_NAME)
    user_email = verify_session_token(token)
    if user_email and user_email in ALLOWED_EMAILS:
        return RedirectResponse(url="/", status_code=303)
        
    client_id = GOOGLE_CLIENT_ID
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sign In - Vicho's Watch Finder</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: 'Inter', sans-serif;
            background: #090d16;
            color: #f1f5f9;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }}
        .card {{
            background: #131b2e;
            border: 1px solid #1e293b;
            border-radius: 16px;
            padding: 40px 32px;
            max-width: 440px;
            width: 100%;
            text-align: center;
            box-shadow: 0 20px 40px rgba(0,0,0,0.5);
        }}
        .icon {{
            font-size: 42px;
            color: #3b82f6;
            margin-bottom: 20px;
        }}
        h1 {{
            font-size: 24px;
            font-weight: 700;
            margin-bottom: 8px;
        }}
        p {{
            font-size: 14px;
            color: #94a3b8;
            margin-bottom: 28px;
            line-height: 1.5;
        }}
        .auth-badge {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background: rgba(59, 130, 246, 0.12);
            color: #60a5fa;
            border: 1px solid rgba(59, 130, 246, 0.3);
            border-radius: 9999px;
            padding: 4px 12px;
            font-size: 12px;
            font-weight: 600;
            margin-bottom: 24px;
        }}
        .btn-google {{
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 12px;
            width: 100%;
            background: #ffffff;
            color: #1e293b;
            border: none;
            border-radius: 10px;
            padding: 14px;
            font-size: 15px;
            font-weight: 600;
            text-decoration: none;
            transition: all 0.2s;
            cursor: pointer;
        }}
        .btn-google:hover {{
            background: #f8fafc;
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(255,255,255,0.15);
        }}
        .footer {{
            margin-top: 24px;
            font-size: 12px;
            color: #64748b;
        }}
    </style>
</head>
<body>
    <div class="card">
        <div class="icon"><i class="fa-solid fa-compass"></i></div>
        <h1>Vicho's Watch Finder</h1>
        <p>Private luxury watch search & matching across 80 dealers.</p>
        <div class="auth-badge"><i class="fa-solid fa-lock"></i> Restricted Access: jvasquez8@gmail.com</div>
        <a href="/auth/google" class="btn-google">
            <svg width="20" height="20" viewBox="0 0 24 24"><path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/><path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/><path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"/><path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"/></svg>
            Sign in with Google
        </a>
        <div class="footer">Authorized accounts only • Protected by Google OAuth</div>
    </div>
</body>
</html>"""

@app.get("/auth/google")
async def auth_google(request: Request):
    if not GOOGLE_CLIENT_ID:
        # Dev fallback when Google OAuth credentials not yet configured
        resp = RedirectResponse(url="/", status_code=303)
        resp.set_cookie(SESSION_COOKIE_NAME, create_session_token("jvasquez8@gmail.com"), max_age=86400*14, httponly=True)
        return resp
        
    redirect_uri = str(request.url_for("auth_callback"))
    if redirect_uri.startswith("http://") and "localhost" not in redirect_uri and "127.0.0.1" not in redirect_uri:
        redirect_uri = redirect_uri.replace("http://", "https://")
        
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "response_type": "code",
        "scope": "openid email profile",
        "redirect_uri": redirect_uri,
        "access_type": "online",
        "prompt": "select_account"
    }
    google_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"
    return RedirectResponse(url=google_url)

@app.get("/auth/callback")
async def auth_callback(request: Request, code: Optional[str] = None, error: Optional[str] = None):
    if error or not code:
        return RedirectResponse(url="/auth/login?error=oauth_failed", status_code=303)
        
    redirect_uri = str(request.url_for("auth_callback"))
    if redirect_uri.startswith("http://") and "localhost" not in redirect_uri and "127.0.0.1" not in redirect_uri:
        redirect_uri = redirect_uri.replace("http://", "https://")

    # Exchange authorization code for token
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code"
    }
    
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(token_url, data=data)
        if token_resp.status_code != 200:
            return RedirectResponse(url="/auth/login?error=token_exchange_failed", status_code=303)
        token_json = token_resp.json()
        access_token = token_json.get("access_token")
        
        # Get user info
        user_resp = await client.get("https://www.googleapis.com/oauth2/v2/userinfo", headers={"Authorization": f"Bearer {access_token}"})
        if user_resp.status_code != 200:
            return RedirectResponse(url="/auth/login?error=userinfo_failed", status_code=303)
        user_info = user_resp.json()
        email = user_info.get("email", "").strip().lower()

    if email not in ALLOWED_EMAILS:
        return RedirectResponse(url=f"/auth/denied?email={urllib.parse.quote(email)}", status_code=303)

    resp = RedirectResponse(url="/", status_code=303)
    resp.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=create_session_token(email),
        max_age=86400 * 14,
        httponly=True,
        samesite="lax",
        secure=True if not ("localhost" in str(request.url) or "127.0.0.1" in str(request.url)) else False
    )
    return resp

@app.get("/auth/denied", response_class=HTMLResponse)
async def access_denied_page(request: Request, email: str = ""):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Access Denied - Vicho's Watch Finder</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: 'Inter', sans-serif;
            background: #090d16;
            color: #f1f5f9;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }}
        .card {{
            background: #131b2e;
            border: 1px solid rgba(239, 68, 68, 0.3);
            border-radius: 16px;
            padding: 40px 32px;
            max-width: 460px;
            width: 100%;
            text-align: center;
            box-shadow: 0 20px 40px rgba(0,0,0,0.5);
        }}
        .icon {{
            font-size: 42px;
            color: #ef4444;
            margin-bottom: 20px;
        }}
        h1 {{
            font-size: 22px;
            font-weight: 700;
            margin-bottom: 12px;
            color: #f87171;
        }}
        p {{
            font-size: 14px;
            color: #94a3b8;
            margin-bottom: 24px;
            line-height: 1.6;
        }}
        .account-badge {{
            background: rgba(239, 68, 68, 0.12);
            color: #fca5a5;
            border: 1px solid rgba(239, 68, 68, 0.2);
            border-radius: 8px;
            padding: 10px 14px;
            font-size: 13px;
            font-weight: 600;
            margin-bottom: 24px;
            word-break: break-all;
        }}
        .btn {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            width: 100%;
            background: #1e293b;
            color: #f1f5f9;
            border: 1px solid #334155;
            border-radius: 10px;
            padding: 12px;
            font-size: 14px;
            font-weight: 600;
            text-decoration: none;
            transition: all 0.2s;
        }}
        .btn:hover {{
            background: #334155;
        }}
    </style>
</head>
<body>
    <div class="card">
        <div class="icon"><i class="fa-solid fa-circle-exclamation"></i></div>
        <h1>403 • Access Restricted</h1>
        <p>This application is private and accessible only to authorized accounts.</p>
        <div class="account-badge">Signed in as: {email or 'Unauthorized Account'}</div>
        <a href="/auth/logout" class="btn"><i class="fa-solid fa-arrow-right-from-bracket"></i> Sign Out & Try Another Account</a>
    </div>
</body>
</html>"""

@app.get("/auth/logout")
async def auth_logout(request: Request):
    resp = RedirectResponse(url="/auth/login", status_code=303)
    resp.delete_cookie(SESSION_COOKIE_NAME)
    return resp

@app.get("/auth/me")
async def get_me(request: Request):
    email = get_current_user_email(request)
    return {"email": email, "authenticated": bool(email)}

# ================= MAIN APPLICATION ROUTES =================

@app.get("/", response_class=HTMLResponse)
async def read_root():
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h1>Vicho's Watch Finder</h1>")

@app.get("/api/sites")
async def get_sites():
    return sites_manager.load_sites()

@app.post("/api/sites")
async def add_site(site_data: Dict = Body(...)):
    new_site = sites_manager.add_site(site_data)
    return new_site

@app.put("/api/sites/{site_id}")
async def update_site(site_id: str, site_data: Dict = Body(...)):
    updated = sites_manager.update_site(site_id, site_data)
    if not updated:
        raise HTTPException(status_code=404, detail="Site not found")
    return updated

@app.delete("/api/sites/{site_id}")
async def delete_site(site_id: str):
    success = sites_manager.delete_site(site_id)
    if not success:
        raise HTTPException(status_code=404, detail="Site not found")
    return {"success": True}

@app.post("/api/sites/{site_id}/toggle")
async def toggle_site(site_id: str):
    updated = sites_manager.toggle_site(site_id)
    if not updated:
        raise HTTPException(status_code=404, detail="Site not found")
    return updated

@app.post("/api/sites/bulk-import")
async def bulk_import(payload: Dict = Body(...)):
    raw_text = payload.get("raw_text", "")
    category = payload.get("category", "Dealer")
    if not raw_text:
        raise HTTPException(status_code=400, detail="raw_text is required")
    added = sites_manager.bulk_import_sites(raw_text, category)
    return {"success": True, "count": len(added), "sites": added}

@app.post("/api/sites/sync-gdoc")
async def sync_gdoc(payload: Optional[Dict] = Body(default=None)):
    doc_url = payload.get("doc_url") if payload else None
    res = sites_manager.sync_from_google_doc(doc_url)
    return res

@app.get("/api/references")
async def get_references():
    return references_manager.load_references()

@app.post("/api/references")
async def add_reference(ref_data: Dict = Body(...)):
    new_ref = references_manager.add_reference(ref_data)
    return new_ref

@app.put("/api/references/{ref_id}")
async def update_reference(ref_id: str, ref_data: Dict = Body(...)):
    updated = references_manager.update_reference(ref_id, ref_data)
    if not updated:
        raise HTTPException(status_code=404, detail="Reference not found")
    return updated

@app.delete("/api/references/{ref_id}")
async def delete_reference(ref_id: str):
    success = references_manager.delete_reference(ref_id)
    if not success:
        raise HTTPException(status_code=404, detail="Reference not found")
    return {"success": True}

@app.post("/api/references/{ref_id}/toggle")
async def toggle_reference(ref_id: str):
    updated = references_manager.toggle_reference(ref_id)
    if not updated:
        raise HTTPException(status_code=404, detail="Reference not found")
    return updated

@app.post("/api/references/sync-gdoc")
async def sync_references_gdoc(payload: Optional[Dict] = Body(default=None)):
    doc_url = payload.get("doc_url") if payload else None
    res = references_manager.sync_references_from_google_doc(doc_url)
    return res

@app.get("/api/search/stream")
async def search_stream(query: str):
    if not query.strip():
        raise HTTPException(status_code=400, detail="Query parameter is required")
        
    sites = sites_manager.load_sites()
    enabled_sites = [s for s in sites if s.get("enabled", True)]
    
    async def event_generator():
        yield f"data: {json.dumps({'type': 'init', 'total_sites': len(enabled_sites), 'query': query})}\n\n"
        for site in enabled_sites:
            try:
                res = await searcher.search_site(site, query)
                yield f"data: {json.dumps({'type': 'site_result', 'data': res})}\n\n"
            except Exception as e:
                err_payload = {
                    "site_id": site.get("id"),
                    "site_name": site.get("name"),
                    "site_url": site.get("url"),
                    "status": "error",
                    "matches_count": 0,
                    "products": [],
                    "error": str(e)
                }
                yield f"data: {json.dumps({'type': 'site_result', 'data': err_payload})}\n\n"
        yield f"data: {json.dumps({'type': 'done'})}\n\n"
        
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@app.get("/api/export/csv")
async def export_csv(query: str = ""):
    sites = sites_manager.load_sites()
    results = await searcher.search_all(sites, query) if query else []
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Site Name", "Site URL", "Product Title", "Price", "Product URL", "Match Score"])
    
    for r in results:
        site_name = r.get("site_name", "")
        site_url = r.get("site_url", "")
        for p in r.get("products", []):
            writer.writerow([
                site_name,
                site_url,
                p.get("title", ""),
                p.get("price", ""),
                p.get("url", ""),
                p.get("score", "")
            ])
            
    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=watch_search_results_{query or 'all'}.csv"}
    )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "127.0.0.1")
    uvicorn.run("main:app", host=host, port=port, reload=False if os.environ.get("PORT") else True)
