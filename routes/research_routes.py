import httpx
from fastapi import APIRouter, Depends, HTTPException, Query

from models.models import User
from schemas.schemas import ScholarSearchRequest
from services.auth_service import get_current_user
from utils.config import SERP_API_KEY

router = APIRouter(prefix="/api/v1/research", tags=["Research"])


@router.post("/scholar")
async def search_google_scholar(
    req: ScholarSearchRequest,
    current_user: User = Depends(get_current_user),
):
    if not SERP_API_KEY:
        raise HTTPException(status_code=503, detail="Google Scholar API not configured")

    params = {
        "engine": "google_scholar",
        "q": req.query,
        "api_key": SERP_API_KEY,
        "num": req.num_results,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get("https://serpapi.com/search", params=params)

    if response.status_code != 200:
        raise HTTPException(status_code=502, detail="Google Scholar search failed")

    data = response.json()
    results = data.get("organic_results", [])

    return {
        "query": req.query,
        "total_results": len(results),
        "results": [
            {
                "title": r.get("title", ""),
                "snippet": r.get("snippet", ""),
                "link": r.get("link", ""),
                "publication_info": r.get("publication_info", {}).get("summary", ""),
                "cited_by_count": r.get("inline_links", {}).get("cited_by", {}).get("total", 0),
                "cited_by_link": r.get("inline_links", {}).get("cited_by", {}).get("link", ""),
                "year": r.get("publication_info", {}).get("summary", "").split(",")[-1].strip() if r.get("publication_info") else "",
                "authors": [a.get("name", "") for a in r.get("publication_info", {}).get("authors", [])],
            }
            for r in results
        ],
    }


@router.get("/scholar/cite/{result_id}")
async def get_citation(
    result_id: str,
    current_user: User = Depends(get_current_user),
):
    if not SERP_API_KEY:
        raise HTTPException(status_code=503, detail="Google Scholar API not configured")

    params = {
        "engine": "google_scholar_cite",
        "q": result_id,
        "api_key": SERP_API_KEY,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get("https://serpapi.com/search", params=params)

    if response.status_code != 200:
        raise HTTPException(status_code=502, detail="Citation fetch failed")

    data = response.json()
    citations = data.get("citations", [])

    return {
        "result_id": result_id,
        "citations": [
            {
                "title": c.get("title", ""),
                "snippet": c.get("snippet", ""),
            }
            for c in citations
        ],
        "links": data.get("links", []),
    }


@router.get("/scholar/author")
async def search_author(
    author: str = Query(..., description="Author name to search"),
    current_user: User = Depends(get_current_user),
):
    if not SERP_API_KEY:
        raise HTTPException(status_code=503, detail="Google Scholar API not configured")

    params = {
        "engine": "google_scholar_profiles",
        "mauthors": author,
        "api_key": SERP_API_KEY,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get("https://serpapi.com/search", params=params)

    if response.status_code != 200:
        raise HTTPException(status_code=502, detail="Author search failed")

    data = response.json()
    profiles = data.get("profiles", [])

    return {
        "query": author,
        "profiles": [
            {
                "name": p.get("name", ""),
                "affiliations": p.get("affiliations", ""),
                "email": p.get("email", ""),
                "cited_by": p.get("cited_by", 0),
                "interests": [i.get("title", "") for i in p.get("interests", [])],
                "thumbnail": p.get("thumbnail", ""),
            }
            for p in profiles
        ],
    }
