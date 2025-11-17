"""
Database Schemas

Define your MongoDB collection schemas here using Pydantic models.
These schemas are used for data validation in your application.

Each Pydantic model represents a collection in your database.
Model name is converted to lowercase for the collection name:
- User -> "user" collection
- Product -> "product" collection
- BlogPost -> "blogpost" collection
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime

# Example schemas (kept for reference):

class User(BaseModel):
    """
    Example users collection schema
    Collection name: "user" (lowercase of class name)
    """
    name: str = Field(..., description="Full name")
    email: str = Field(..., description="Email address")
    address: str = Field(..., description="Address")
    age: Optional[int] = Field(None, ge=0, le=120, description="Age in years")
    is_active: bool = Field(True, description="Whether user is active")

class Product(BaseModel):
    """
    Example products collection schema
    Collection name: "product" (lowercase of class name)
    """
    title: str = Field(..., description="Product title")
    description: Optional[str] = Field(None, description="Product description")
    price: float = Field(..., ge=0, description="Price in dollars")
    category: str = Field(..., description="Product category")
    in_stock: bool = Field(True, description="Whether product is in stock")

# Application schemas

class AuthUser(BaseModel):
    """
    Auth users collection schema
    Collection name: "authuser"
    Stores password as a salted hash
    """
    name: str = Field(..., description="Full name")
    email: EmailStr
    password_hash: str
    salt: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class BlogPost(BaseModel):
    """
    Blog posts collection schema
    Collection name: "blogpost"
    """
    title: str
    slug: str
    excerpt: Optional[str] = None
    content: str
    tags: List[str] = []
    cover_image: Optional[str] = None
    published: bool = True
    published_at: Optional[datetime] = None
    author: Optional[str] = None

class ContactMessage(BaseModel):
    """
    Contact messages collection schema
    Collection name: "contactmessage"
    """
    name: str
    email: EmailStr
    message: str
    status: str = Field("new", description="new|read|replied")
    submitted_at: Optional[datetime] = None
