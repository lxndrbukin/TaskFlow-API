from fastapi import APIRouter, HTTPException
from passlib.context import CryptContext
from models import User

auth_router = APIRouter(prefix="/auth", tags=["auth"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

@auth_router.post("/register")
def register(user: User):
	if len(user.password.encode("utf-8")) > 72:
		raise HTTPException(status_code=400, detail="Password too long")
	user.password = pwd_context.hash(user.password)
	return user