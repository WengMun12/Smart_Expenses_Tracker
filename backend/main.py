from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine, text
from datetime import datetime, timedelta, timezone
from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import UploadFile, File
from datetime import date
from typing import Optional
from dotenv import load_dotenv
from fastapi.encoders import jsonable_encoder
from google import genai
from google.genai import types
import json
import jwt
import bcrypt
import os
import time
import ssl

DATABASE_URL = os.getenv("DATABASE_URL", "mysql+pymysql://root:@Localhost/expense_tracker")
connect_args = {"ssl": ssl.create_default_context()} if os.getenv("DB_SSL") == "true" else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
app = FastAPI()

class UserIn(BaseModel):
    username: str
    password: str

@app.post("/signup")
def signup(user: UserIn):
    if len(user.password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters")
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
            text("""SELECT e.*, c.categoryName
                    FROM expenses e
                    LEFT JOIN category c ON e.categoryID = c.categoryID
                    WHERE e.userID = :u
                    ORDER BY e.sdate DESC"""),
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

JSON_FORMAT = (
    "Reply with ONLY JSON, no extra words, in this form: " 
    '{"amount": number, "description": "short text", "category": "Food|Transport|Shopping|Bills|Savings|Others"}'
)

def run_ai(contents):
    data = None
    for attempt in range(4):
        model = MODELS[attempt % len(MODELS)]
        try: 
            res = gemini.models.generate_content(model=model, contents=contents)
            clean = res.text.replace("```json", "").replace("```", "").strip()
            data = json.loads(clean)
            break
        except Exception as ex:
            print("AI ERROR:", model, repr(ex))
            time.sleep(3)
    if data is None:
        raise HTTPException(502, "AI is busy, please try again")

    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT categoryID FROM category WHERE categoryName = :n"),
            {"n": data.get("category")},
        ).fetchone()
    data["categoryID"] = row.categoryID if row else None
    return data

@app.post("/ai/categorize")
def ai_category(body: AIIn, user_id: int = Depends(get_current_user)):
    prompt = "Extract expense details from this text: " + body.text + "\n" + JSON_FORMAT
    return run_ai(prompt)

@app.post("/ai/receipt")
def ai_receipt(file: UploadFile = File(...), user_id: int = Depends(get_current_user)):
    image_bytes = file.file.read()
    print("RECEIPT:", file.content_type, len(image_bytes), "bytes")
    if len(image_bytes) > 5 * 1024 * 1024:
        raise HTTPException(413, "Image too large (max 5MB)")
    mime = file.content_type if (file.content_type or "").startswith("image/") else "image/jpeg"
    part = types.Part.from_bytes(data=image_bytes, mime_type=mime)
    prompt = (
        "This is a receipt. Extract the total amount paid, use the store name as the description and pick the best category."
        "If you cannot read it, set amount to 0.\n" + JSON_FORMAT
    )
    return run_ai([part, prompt])

@app.post("/ai/tips")
def ai_tips(month: Optional[str] = None, user_id: int = Depends(get_current_user)):
    current = build_summary(user_id, month)
    if not current["by_category"]:
        raise HTTPException(400, "No expenses this month")

    y, m = map(int, current["month"].split("-"))
    prev_month = f"{y - 1}-12" if m == 1 else f"{y}-{m - 1:02d}"
    previous = build_summary(user_id, prev_month)

    prompt =(
        "You are a friendly personal finance coach for a student. Currency is RM.\n"
        f"This month's spending: {json.dumps(current)}\n"
        f"Last month's total: {previous['total']}\n"
        "Give exactly 3 short, specifc practical tips to save money, based on the biggest categories and any increase from last month."
        "Each tip must be under 25 words."
        "Reply with ONLY a JSON array of 3 strings, no extra words."
    )

    tips = None
    for attempt in range(4):
        model = MODELS[attempt % len(MODELS)]
        try: 
            res =gemini.models.generate_content(model=model, contents=prompt, config=types.GenerateContentConfig(max_output_tokens=500))
            raw = res.text
            print("TIPS RAW:", model, repr(raw))
            clean = raw.replace("```json", "").replace("```", "").strip()
            data = json.loads(clean)
            if isinstance(data, dict):
                data = next((v for v in data.values() if isinstance(v, list)), [])
            if isinstance(data, list) and data:
                tips = [str(t) for t in data[:3]]
                break
            print("TIPS BAD SHAPE:", data)
        except Exception as ex:
            print("AI ERROR:", model, repr(ex))
            time.sleep(3)
    if tips is None:
        raise HTTPException(502, "AI is busy, please try again")
    return {"month": current["month"], "tips": tips}

@app.get("/category")
def list_category():
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT * FROM category")).mappings().all()
    return [dict(r) for r in rows]

def build_summary(user_id: int, month: Optional[str] = None):
    if month is None:
        month = date.today().strftime("%Y-%m")
    try:
        start = date.fromisoformat(month + "-01")
    except ValueError:
        raise HTTPException(400, "Month must look like 2026-11")
    end = date(start.year + start.month // 12, start.month % 12 + 1, 1)

    with engine.connect() as conn:
        rows = conn.execute(
            text("""SELECT COALESCE(c.categoryName, 'Uncategorized') AS category, SUM(e.amount) AS total
                    FROM expenses e
                    LEFT JOIN category c ON e.categoryID = c.categoryID
                    WHERE e.userID = :u AND e.sdate >= :s AND e.sdate < :e
                    GROUP BY category
                    ORDER BY total DESC"""),
            {"u": user_id, "s": start, "e": end},
        ).mappings().all()

    by_category = [{"category": r["category"], "total": float(r["total"])} for r in rows]
    return {
        "month": month,
        "total": round(sum(x["total"] for x in by_category), 2),
        "by_category": by_category,
    }

@app.get("/summary")
def summary(month: Optional[str] = None, user_id: int = Depends(get_current_user)):
    return build_summary(user_id, month)