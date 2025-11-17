import os
import hashlib
import secrets
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr

from database import db, create_document, get_documents
from schemas import AuthUser, BlogPost, ContactMessage

app = FastAPI(title="SaaS Starter API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Utility functions for auth

def hash_password(password: str, salt: Optional[str] = None):
    if salt is None:
        salt = secrets.token_hex(16)
    pwd_hash = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 200000)
    return salt, pwd_hash.hex()


def verify_password(password: str, salt: str, password_hash: str) -> bool:
    _, computed = hash_password(password, salt)
    return secrets.compare_digest(computed, password_hash)


# Request/Response models

class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class LoginResponse(BaseModel):
    token: str
    name: str
    email: EmailStr

class BlogCreateRequest(BaseModel):
    title: str
    slug: str
    content: str
    excerpt: Optional[str] = None
    tags: Optional[List[str]] = None
    cover_image: Optional[str] = None
    published: bool = True

class ContactRequest(BaseModel):
    name: str
    email: EmailStr
    message: str


@app.get("/")
def read_root():
    return {"message": "SaaS Starter API running"}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
                response["connection_status"] = "Connected"
            except Exception as e:
                response["database"] = f"⚠️ Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️ Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"
    return response


# Auth Endpoints

@app.post("/auth/register", response_model=LoginResponse)
def register(payload: RegisterRequest):
    # Check if user exists
    existing = list(db["authuser"].find({"email": payload.email})) if db else []
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    salt, pwd_hash = hash_password(payload.password)
    user = AuthUser(
        name=payload.name,
        email=payload.email,
        password_hash=pwd_hash,
        salt=salt,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    _id = create_document("authuser", user)
    token = secrets.token_urlsafe(24)
    # Store session token (simple): upsert into a collection
    db["session"].update_one(
        {"user_id": _id},
        {"$set": {"user_id": _id, "token": token, "created_at": datetime.now(timezone.utc)}},
        upsert=True,
    )
    return LoginResponse(token=token, name=user.name, email=user.email)


@app.post("/auth/login", response_model=LoginResponse)
def login(payload: LoginRequest):
    user = db["authuser"].find_one({"email": payload.email}) if db else None
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not verify_password(payload.password, user.get("salt"), user.get("password_hash")):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = secrets.token_urlsafe(24)
    db["session"].update_one(
        {"user_id": str(user.get("_id"))},
        {"$set": {"user_id": str(user.get("_id")), "token": token, "created_at": datetime.now(timezone.utc)}},
        upsert=True,
    )
    return LoginResponse(token=token, name=user.get("name"), email=user.get("email"))


# Blog Endpoints

@app.get("/blog", response_model=List[BlogPost])
def list_blogs():
    docs = get_documents("blogpost", {}, limit=20)
    # Convert ObjectId to string-safe fields
    out = []
    for d in docs:
        d.pop("_id", None)
        if d.get("published") and not d.get("published_at"):
            d["published_at"] = datetime.now(timezone.utc)
        out.append(BlogPost(**d))
    return out


@app.post("/blog", response_model=BlogPost)
def create_blog(payload: BlogCreateRequest):
    data = BlogPost(
        title=payload.title,
        slug=payload.slug,
        content=payload.content,
        excerpt=payload.excerpt or payload.content[:160],
        tags=payload.tags or [],
        cover_image=payload.cover_image,
        published=payload.published,
        published_at=datetime.now(timezone.utc) if payload.published else None,
        author="admin",
    )
    create_document("blogpost", data)
    return data


# Contact Endpoints

@app.post("/contact")
def contact_submit(payload: ContactRequest):
    msg = ContactMessage(
        name=payload.name,
        email=payload.email,
        message=payload.message,
        status="new",
        submitted_at=datetime.now(timezone.utc),
    )
    create_document("contactmessage", msg)
    return {"ok": True}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
