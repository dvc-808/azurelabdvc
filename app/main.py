from __future__ import annotations

from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse, PlainTextResponse
from fastapi.templating import Jinja2Templates

from .db import fetch_user_profile, init_engine
from .azure_clients import get_blob_client


app = FastAPI(title="User Profile App", version="1.0.0")

templates = Jinja2Templates(directory="app/templates")


@app.on_event("startup")
def on_startup() -> None:
    # Initialize DB engine early to fail fast if secrets/network are misconfigured
    init_engine()


@app.get("/healthz", response_class=PlainTextResponse)
def healthcheck() -> str:
    return "ok"


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/users/{user_id}", response_class=HTMLResponse)
def get_user_profile_page(request: Request, user_id: str) -> HTMLResponse:
    profile = fetch_user_profile(user_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="User not found")

    # Build photo URL to our proxy route. We avoid exposing a SAS publicly.
    photo_url: Optional[str] = None
    if profile.get("photo_blob_name"):
        photo_url = f"/users/{user_id}/photo"

    context = {
        "request": request,
        "profile": profile,
        "photo_url": photo_url,
    }
    return templates.TemplateResponse("user.html", context)


@app.get("/users/{user_id}/photo")
def get_user_photo(user_id: str):
    profile = fetch_user_profile(user_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="User not found")

    photo_blob_name = profile.get("photo_blob_name")
    if not photo_blob_name:
        raise HTTPException(status_code=404, detail="Photo not available")

    blob_client = get_blob_client(photo_blob_name)
    stream = blob_client.download_blob()

    # Determine content type if available, fallback to octet-stream
    content_type = "application/octet-stream"
    try:
        props = blob_client.get_blob_properties()
        if props and props.content_settings and props.content_settings.content_type:
            content_type = props.content_settings.content_type
    except Exception:
        # Non-fatal if we cannot retrieve properties
        pass

    return StreamingResponse(stream.chunks(), media_type=content_type)


# Local dev entry point
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True) 