from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine, text
from datetime import datetime, timedelta, timezone
from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from datetime import date
from typing import Optional
from dotenv import load_dotenv
from fastapi.encoders import jsonable_encoder
from google import genai
import json
import jwt
import bcrypt
import os
import time

engine = create_engine("mysql+pymysql://root:@localhost/expense_tracker")
app = FastAPI()

class UserIn(BaseModel):
    username: str
    password: str

@app.post("/signup")
def signup(user: UserIn):
    hashed = bcrypt.hashpw(user.password.encode(), bcrypt.gensalt()).decode()
    with engine.begin() as conn:
        try: 
            conn.execute(
                text("INSERT INTO users (userName, userPass) VALUES (:u, :p)"),
                {"u": user.username, "p": hashed},
            )
        except Exception:
            raise HTTPException(400, "Username already exist")
    return {"message": "User created"}

load_dotenv()
gemini = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODELS = ["gemini-3.5-flash-lite", "gemini-3.8-flash"]
SECRET_KEY = os.getenv("SECRET_KEY")

security = HTTPBearer()

def get_current_user(creds: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(creds.credentials, SECRET_KEY, algorithms=["HS256"])
        return payload["userId"]
    except Exception as ex:
        print("JWT ERROR:", repr(ex))
        raise HTTPException(401, "Invalid or expired token")

@app.post("/login")
def login(user: UserIn):
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT userID, userPass FROM users WHERE userName = :u"),
            {"u": user.username},
        ).fetchone()

    if row is None or not bcrypt.checkpw(user.password.encode(), row.userPass.encode()):
        raise HTTPException(401, "Wrong username or password")

    payload = {
        "userId": row.userID,
        "exp": datetime.now(timezone.utc) + timedelta(hours=24),
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    return {"access_token": token}

class ExpenseIn(BaseModel):
    amount: float
    description: Optional[str] = None
    date: date
    categoryID: int

@app.post("/expenses")
def add_expenses(e: ExpenseIn, user_id: int = Depends(get_current_user)):
    with engine.begin() as conn:
        conn.execute(
            text("""INSERT INTO expenses (userID, categoryID, amount, description, sdate) VALUES (:u, :c, :a, :d, :dt)"""),
            {"u": user_id, "c": e.categoryID, "a": e.amount, "d": e.description, "dt": e.date},
        )
    return {"message": "Expense added"}

@app.get("/expenses")
def list_expenses(user_id: int = Depends(get_current_user)):
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT * FROM expenses WHERE userID = :u ORDER BY sdate DESC"),
            {"u": user_id},
        ).mappings().all()
    return jsonable_encoder([dict(r) for r in rows])

@app.put("/expenses/{expense_id}")
def update_expense(expense_id: int, e: ExpenseIn, user_id: int = Depends(get_current_user)):
    with engine.begin() as conn:
        result = conn.execute(
            text("""UPDATE expenses SET categoryID=:c, amount=:a, description=:d, sdate=:dt WHERE expensesID=:id AND userID=:u"""),
            {"c": e.categoryID, "a": e.amount, "d": e.description, "dt": e.date, "id": expense_id, "u": user_id},
        )
    if result.rowcount == 0:
        raise HTTPException(404, "Expense not found")
    return {"message": "Expense updated"}

@app.delete("/expenses/{expense_id}")
def delete_expense(expense_id: int, user_id: int = Depends(get_current_user)):
    with engine.begin() as conn:
        result = conn.execute(
            text("DELETE FROM expenses WHERE expensesID=:id AND userID=:u"),
            {"id": expense_id, "u": user_id},
        )
    if result.rowcount == 0:
        raise HTTPException(404, "Expense not found")
    return {"message": "Expense deleted"}

class AIIn(BaseModel):
    text: str

@app.post("/ai/categorize")
def ai_category(body: AIIn, user_id: int = Depends(get_current_user)):
    prompt = (
        "Extract expense details from this text: " + body.text + "\n"
        "Reply with ONLY JSON, no extra words, in this form: "
        '{"amount": number, "description": "short text", "category": "Food|Transport|Shopping|Bills|Savings|Others"}'
    )
    last_error = None
    for attempt in range(3):
        model = MODELS[attempt % len(MODELS)]
        try:
            res = gemini.models.generate_content(model=model, contents=prompt)
            clean = res.text.replace("'''json", "").replace("'''", "").strip()
            data = json.loads(clean)
            break
        except Exception as ex:
            last_error = exec
            print("AI ERROR:", repr(ex))
            time.sleep(2)
    else:
        raise HTTPException(502, "AI is busy, please try again")

    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT categoryID FROM category WHERE categoryName = :n"), {"n": data.get("category")},
        ).fetchone()
    data["categoryID"] = row.categoryID if row else None
    return data

@app.get("/category")
def list_category():
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT * FROM category")).mappings().all()
    return [dict(r) for r in rows]