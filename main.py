from fastapi import FastAPI
from pydantic import BaseModel

class Item(BaseModel):
	name: str
	price: float
	is_offer: bool = None

app = FastAPI(title="TaskFlow API", description="TaskFlow")

@app.get("/")
def home():
	return {"message": "Hello there"}

@app.get("/items")
def read_items(skip: int = 0, limit: int = 10):
	return {"skip": skip, "limit": limit}

@app.get("/items/{item_id}")
def read_item(item_id: int):
	return {"item_id": item_id}

@app.post("/items")
def add_item(item: Item):
	return {"item": item}