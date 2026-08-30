import os
import json
import csv
import io
from fastapi import FastAPI, Request, HTTPException, Body
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Optional
import uvicorn
import sites_manager
import references_manager
from search_engine import MultiSiteSearcher

app = FastAPI(title="Multi-Website Search & Matcher Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

searcher = MultiSiteSearcher(timeout=8.0)

# Serve static assets
static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h1>Site Search App Running</h1>")

# --- REFERENCES API ---
@app.get("/api/references")
async def get_references():
    refs = references_manager.load_references()
    return {"references": refs, "count": len(refs)}

@app.post("/api/references/sync-gdoc")
async def sync_references_gdoc(payload: Dict = Body(default={})):
    file_id = payload.get("file_id", "15Jt2CXVU-crP8qJtV6lQ1B58fssOCtgkAvM4M-B_Tdg")
    res = references_manager.sync_references_from_google_doc(file_id)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "Sync failed"))
    return res

@app.post("/api/references")
async def save_references(payload: Dict = Body(...)):
    if "raw_text" in payload:
        refs = references_manager.set_raw_references_text(payload["raw_text"])
    elif "references" in payload:
        references_manager.save_references(payload["references"])
        refs = references_manager.load_references()
    else:
        raise HTTPException(status_code=400, detail="Missing raw_text or references array")
    return {"success": True, "count": len(refs), "references": refs}

@app.post("/api/references/add")
async def add_reference(payload: Dict = Body(...)):
    ref = payload.get("reference", "").strip()
    if not ref:
        raise HTTPException(status_code=400, detail="Reference text is required")
    refs = references_manager.add_reference(ref)
    return {"success": True, "count": len(refs), "references": refs}

@app.delete("/api/references/{ref}")
async def delete_reference(ref: str):
    refs = references_manager.delete_reference(ref)
    return {"success": True, "count": len(refs), "references": refs}

# --- SITES API ---
@app.get("/api/sites")
async def get_sites():
    sites = sites_manager.load_sites()
    return {"sites": sites, "count": len(sites)}

@app.post("/api/sites")
async def add_site(payload: Dict = Body(...)):
    url = payload.get("url")
    name = payload.get("name")
    category = payload.get("category", "Dealer")
    custom_search_url = payload.get("custom_search_url", "")
    platform = payload.get("platform", "auto")
    
    if not url:
        raise HTTPException(status_code=400, detail="Website URL is required")
        
    try:
        site = sites_manager.add_site(url, name, category, custom_search_url, platform)
        return {"success": True, "site": site}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.put("/api/sites/{site_id}")
async def update_site(site_id: str, updates: Dict = Body(...)):
    site = sites_manager.update_site(site_id, updates)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    return {"success": True, "site": site}

@app.delete("/api/sites/{site_id}")
async def delete_site(site_id: str):
    success = sites_manager.delete_site(site_id)
    if not success:
        raise HTTPException(status_code=404, detail="Site not found")
    return {"success": True}

@app.post("/api/sites/{site_id}/toggle")
async def toggle_site(site_id: str, payload: Dict = Body(default={})):
    enabled = payload.get("enabled")
    site = sites_manager.toggle_site(site_id, enabled)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    return {"success": True, "site": site}

@app.post("/api/sites/toggle-all")
async def toggle_all_sites(payload: Dict = Body(...)):
    enabled = payload.get("enabled", True)
    sites = sites_manager.set_all_sites_enabled(enabled)
    return {"success": True, "sites": sites, "count": len(sites)}

@app.get("/api/sites/raw")
async def get_raw_sites():
    raw_text = sites_manager.get_raw_sites_text()
    return {"raw_text": raw_text}

@app.post("/api/sites/raw")
async def save_raw_sites(payload: Dict = Body(...)):
    raw_text = payload.get("raw_text", "")
    sites = sites_manager.set_raw_sites_text(raw_text)
    return {"success": True, "count": len(sites), "sites": sites}

@app.post("/api/sites/sync-gdoc")
async def sync_gdoc(payload: Dict = Body(default={})):
    file_id = payload.get("file_id", "1QQ5nj6pgv90nfKKa93L4hpK10lato-7b")
    res = sites_manager.sync_from_google_drive(file_id)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "Sync failed"))
    return res

@app.post("/api/sites/bulk")
async def bulk_import(payload: Dict = Body(...)):
    raw_text = payload.get("text", "")
    category = payload.get("category", "Dealer")
    if not raw_text:
        raise HTTPException(status_code=400, detail="No text/URLs provided")
        
    added = sites_manager.bulk_import_sites(raw_text, category)
    return {"success": True, "added_count": len(added), "sites": added}

# --- SEARCH API ---
@app.post("/api/search")
async def search_sites(payload: Dict = Body(...)):
    query = payload.get("query", "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="Search query is required")
        
    selected_site_ids = payload.get("site_ids")
    sites = sites_manager.load_sites()
    
    if selected_site_ids:
        sites_to_search = [s for s in sites if s["id"] in selected_site_ids and s.get("enabled", True)]
    else:
        sites_to_search = [s for s in sites if s.get("enabled", True)]
        
    if not sites_to_search:
        return {"query": query, "total_sites_searched": 0, "total_matches": 0, "results": [], "message": "No active websites configured to search."}

    results = await searcher.search_all(sites_to_search, query)
    
    total_matches = sum(r.get("matches_count", 0) for r in results)
    
    all_products = []
    for r in results:
        for p in r.get("products", []):
            product_copy = dict(p)
            product_copy["site_name"] = r["site_name"]
            product_copy["site_url"] = r["site_url"]
            all_products.append(product_copy)
            
    all_products.sort(key=lambda x: x.get("score", 0), reverse=True)

    return {
        "query": query,
        "total_sites_searched": len(sites_to_search),
        "total_matches": total_matches,
        "site_results": results,
        "all_products": all_products
    }

# --- BATCH SEARCH API ---
@app.post("/api/batch-search")
async def batch_search(payload: Dict = Body(...)):
    references = payload.get("references", [])
    if isinstance(references, str):
        references = [r.strip() for r in references.split("\n") if r.strip()]
    if not references:
        raise HTTPException(status_code=400, detail="No references provided")
        
    selected_site_ids = payload.get("site_ids")
    sites = sites_manager.load_sites()
    if selected_site_ids:
        sites_to_search = [s for s in sites if s["id"] in selected_site_ids and s.get("enabled", True)]
    else:
        sites_to_search = [s for s in sites if s.get("enabled", True)]
        
    if not sites_to_search:
        return {"references": references, "total_matches": 0, "results_by_reference": {}, "all_products": []}

    results_by_reference = {}
    all_products = []
    total_matches = 0

    for ref in references:
        res = await searcher.search_all(sites_to_search, ref)
        ref_matches = sum(r.get("matches_count", 0) for r in res)
        total_matches += ref_matches
        
        ref_products = []
        for r in res:
            for p in r.get("products", []):
                p_copy = dict(p)
                p_copy["site_name"] = r["site_name"]
                p_copy["site_url"] = r["site_url"]
                p_copy["matched_reference"] = ref
                ref_products.append(p_copy)
                all_products.append(p_copy)
                
        results_by_reference[ref] = {
            "matches_count": ref_matches,
            "site_results": res,
            "products": ref_products
        }

    all_products.sort(key=lambda x: x.get("score", 0), reverse=True)

    return {
        "references": references,
        "total_references": len(references),
        "total_sites_searched": len(sites_to_search),
        "total_matches": total_matches,
        "results_by_reference": results_by_reference,
        "all_products": all_products
    }

@app.get("/api/export/csv")
async def export_csv(query: str = ""):
    sites = sites_manager.load_sites()
    if not query:
        raise HTTPException(status_code=400, detail="Query parameter is required")
        
    results = await searcher.search_all([s for s in sites if s.get("enabled", True)], query)
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Website", "Product Title", "Price", "URL", "In Stock", "Match Score", "Search Query"])
    
    for r in results:
        for p in r.get("products", []):
            writer.writerow([
                r.get("site_name"),
                p.get("title"),
                p.get("price"),
                p.get("url"),
                "Yes" if p.get("available", True) else "No",
                p.get("score"),
                query
            ])
            
    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=search_results_{query}.csv"}
    )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "127.0.0.1")
    uvicorn.run("main:app", host=host, port=port, reload=False if os.environ.get("PORT") else True)
