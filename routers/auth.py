from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordRequestForm
import sqlite3
from passlib.context import CryptContext
from models import User
from db import load_db

auth_router = APIRouter(prefix="/auth", tags=["auth"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

@auth_router.post("/register", status_code=status.HTTP_201_CREATED)
def register(form: User, db: sqlite3.Connection = Depends(load_db)):
	cursor = db.cursor()
	cursor.execute('SELECT COUNT(*) FROM users WHERE username = ?', (form.username,))
	row = cursor.fetchone()
	if row[0] > 0:
		raise HTTPException(status_code=409, detail="Username taken")
	if len(form.password.encode("utf-8")) > 72:
		raise HTTPException(status_code=400, detail="Password too long")
	form.password = pwd_context.hash(form.password)
	insert_user = '''
        INSERT INTO users(username, password)
        VALUES(?, ?)
    '''
	values = (
		form.username,
		form.password
	)
	cursor.execute(insert_user, values)
	db.commit()
	return {"msg": "User registered successfully", "username": form.username}