from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine, text
from datetime import datetime, timedelta, timezone
from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from datetime import date
from typing import Optional
from dotenv import load_dotenv
import jwt
import bcrypt
import os

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

@app.get("/category")
def list_category():
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT * FROM category")).mappings().all()
    return [dict(r) for r in rows]