from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.config import settings
from datetime import datetime, timedelta, timezone
from jose import jwt
from passlib.context import CryptContext

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class LoginRequest(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str = "admin"

@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest):
    # Demo credentials check
    demo_users = {
        "admin@gstauditpro.in": {"password": "Admin@123", "role": "super_admin"},
        "ca@demo.in": {"password": "Demo@123", "role": "ca"},
        "user@demo.in": {"password": "Demo@123", "role": "user"},
    }
    user = demo_users.get(data.email)
    if not user or user["password"] != data.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token_data = {
        "sub": data.email,
        "role": user["role"],
        "exp": datetime.now(timezone.utc) + timedelta(hours=24)
    }
    token = jwt.encode(token_data, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return TokenResponse(access_token=token, role=user["role"])

@router.get("/me")
async def get_me():
    return {"email": "admin@gstauditpro.in", "role": "super_admin"}
