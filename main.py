from fastapi import FastAPI, Form, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import mysql.connector
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if not os.path.exists("uploads"):
    os.makedirs("uploads")

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="campusfind_db"
    )

class ItemUpdate(BaseModel):
    title: str
    description: str
    category: str
    location: str
    contact_info: str
    username: str

class AuthPayload(BaseModel):
    username: str
    password: str

# --- REAL AUTHENTICATION ENDPOINTS ---

@app.post("/api/register")
def register(payload: AuthPayload):
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    
    # Check if username already exists
    cursor.execute("SELECT * FROM users WHERE username = %s", (payload.username.strip(),))
    existing = cursor.fetchone()
    
    if existing:
        cursor.close()
        db.close()
        raise HTTPException(status_code=400, detail="Username already exists. Please sign in.")
    
    # Insert new user into database
    cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (payload.username.strip(), payload.password))
    db.commit()
    cursor.close()
    db.close()
    return {"message": "Account registered successfully", "username": payload.username.strip()}

@app.post("/api/login")
def login(payload: AuthPayload):
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    
    # Check if account exists with matching username and password
    cursor.execute("SELECT * FROM users WHERE username = %s AND password = %s", (payload.username.strip(), payload.password))
    user = cursor.fetchone()
    cursor.close()
    db.close()
    
    if not user:
        raise HTTPException(status_code=401, detail="Account not found or incorrect password. Please sign up first.")
    
    return {"message": "Login successful", "username": user["username"]}

# --- ITEM ENDPOINTS ---

@app.get("/api/items/")
def get_items():
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT id, title, description, category, location, contact_info, username, image_url, created_at 
        FROM items 
        ORDER BY id DESC
    """)
    items = cursor.fetchall()
    cursor.close()
    db.close()
    return items

@app.post("/api/items/")
async def create_item(
    title: str = Form(...),
    description: str = Form(...),
    category: str = Form(...),
    location: str = Form(...),
    contact_info: str = Form(...),
    username: str = Form(...),
    image: UploadFile = File(None)
):
    image_url = None
    if image and image.filename:
        file_path = f"uploads/{image.filename}"
        with open(file_path, "wb") as f:
            f.write(await image.read())
        image_url = f"http://127.0.0.1:8000/uploads/{image.filename}"

    db = get_db_connection()
    cursor = db.cursor()
    sql = """
        INSERT INTO items (title, description, category, location, contact_info, username, image_url)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    cursor.execute(sql, (title, description, category, location, contact_info, username, image_url))
    db.commit()
    cursor.close()
    db.close()
    return {"message": "Item posted successfully", "username": username}

@app.put("/api/items/{item_id}")
def update_item(item_id: int, item: ItemUpdate):
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT username FROM items WHERE id = %s", (item_id,))
    existing = cursor.fetchone()

    if not existing:
        cursor.close()
        db.close()
        raise HTTPException(status_code=404, detail="Item not found")
    
    if existing["username"].strip().lower() != item.username.strip().lower():
        cursor.close()
        db.close()
        raise HTTPException(status_code=403, detail="You can only edit your own posts")

    sql = """
        UPDATE items 
        SET title = %s, description = %s, category = %s, location = %s, contact_info = %s 
        WHERE id = %s
    """
    cursor.execute(sql, (item.title, item.description, item.category, item.location, item.contact_info, item_id))
    db.commit()
    cursor.close()
    db.close()
    return {"message": "Report updated successfully"}

@app.delete("/api/items/{item_id}")
def delete_item(item_id: int, username: str):
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT username FROM items WHERE id = %s", (item_id,))
    existing = cursor.fetchone()

    if not existing:
        cursor.close()
        db.close()
        raise HTTPException(status_code=404, detail="Item not found")
    
    if existing["username"].strip().lower() != username.strip().lower():
        cursor.close()
        db.close()
        raise HTTPException(status_code=403, detail="You can only delete your own posts")

    cursor.execute("DELETE FROM items WHERE id = %s", (item_id,))
    db.commit()
    cursor.close()
    db.close()
    return {"message": "Report deleted"}