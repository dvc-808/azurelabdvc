from __future__ import annotations

from typing import Optional

from fastapi import FastAPI, HTTPException, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse, StreamingResponse, PlainTextResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from azure.storage.blob import ContentSettings

from .db import fetch_user_profile, init_engine, user_exists, insert_user_profile
from .azure_clients import get_blob_client, get_blob_service_client, get_secret_client


app = FastAPI(title="User Profile App", version="1.0.0")

templates = Jinja2Templates(directory="app/templates")


@app.on_event("startup")
def on_startup() -> None:
    # Initialize DB engine early to fail fast if secrets/network are misconfigured
    init_engine()
    # Initialize Azure Key Vault and Blob service clients as well
    get_secret_client()
    get_blob_service_client()


@app.get("/healthz", response_class=PlainTextResponse)
def healthcheck() -> str:
    return "ok"


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/users/new", response_class=HTMLResponse)
def new_user_form(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("create_user.html", {"request": request})


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


@app.post("/users", response_class=JSONResponse)
async def create_user(
    user_id: str = Form(...),
    name: str = Form(...),
    age: Optional[int] = Form(None),
    phone: Optional[str] = Form(None),
    address: Optional[str] = Form(None),
    photo: Optional[UploadFile] = File(None),
):
    # Check if user already exists
    if user_exists(user_id):
        raise HTTPException(status_code=409, detail="User already exists")

    photo_blob_name: Optional[str] = None

    # Upload photo to blob if present
    if photo is not None:
        # Choose a blob name convention: users/{user_id}/{original_filename}
        safe_filename = photo.filename or "photo"
        blob_name = f"users/{user_id}/{safe_filename}"
        blob_client = get_blob_client(blob_name)
        data = await photo.read()
        content_settings = None
        if getattr(photo, "content_type", None):
            content_settings = ContentSettings(content_type=photo.content_type)
        blob_client.upload_blob(data, overwrite=True, content_settings=content_settings)
        photo_blob_name = blob_name

    # Insert into database
    try:
        insert_user_profile(
            user_id=user_id,
            name=name,
            age=age,
            phone=phone,
            address=address,
            photo_blob_name=photo_blob_name,
        )
    except Exception as exc:
        # Rollback blob if DB insert fails
        if photo_blob_name:
            try:
                get_blob_client(photo_blob_name).delete_blob()
            except Exception:
                pass
        raise HTTPException(status_code=500, detail="Failed to create user") from exc

    return {"status": "created", "user_id": user_id}


# Local dev entry point
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True) 