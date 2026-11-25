import json
import os
import sqlite3
from contextlib import closing, contextmanager
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Annotated
from urllib.parse import urlencode

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from categories import CATEGORIES

ROOT = Path(__file__).resolve().parent #путь к файлу main.py
DATABASE = os.getenv("TRACKER_DB", ROOT / "tracker.sqlite3") #путь к бд


@contextmanager
def database():
    with closing(sqlite3.connect(DATABASE)) as connection, connection: #устанавливаем соединение с базой данных 
        connection.row_factory = sqlite3.Row
        yield connection


with database() as db:                #создаем таблицу расходов и проверяем наличие столбца копейки
    db.execute("BEGIN IMMEDIATE")
    db.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY,
            kopeyki INTEGER NOT NULL CHECK(kopeyki > 0),
            category TEXT NOT NULL,
            day TEXT NOT NULL,
            comment TEXT NOT NULL
        )
    """)

class Expense(BaseModel): #создаем модель расходов с проверкой данных
    rubles: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    category: str
    day: date
    comment: str = Field(default="", max_length=300)


class ExpenseTracker:
    def __init__(self):
        with (ROOT / "config.json").open(encoding="utf-8") as file:
            config = json.load(file)

        self.app = FastAPI(title="Трекер расходов") 
        self.app.add_middleware(
            CORSMiddleware,    #проверяем, что запрос идет с разрешенного порта
            allow_origins=config["cors_origins"],
            allow_methods=["*"],
            allow_headers=["*"],
        )
        self.templates = Jinja2Templates(directory=ROOT / "static") #связь с фронтендом
        self.app.get("/", response_class=HTMLResponse)(self.index)
        self.app.post("/expenses")(self.submit_expense)
        self.app.get("/api/categories")(self.get_categories)
        self.app.get("/api/expenses")(self.get_expenses)
        self.app.post("/api/expenses", status_code=201)(self.add_expense)

    def index(self, request: Request, category: str = "", day: date | None = None, added: bool = False):
        return self.templates.TemplateResponse(request, "index.html", {
            **self.get_expenses(),
            "categories": CATEGORIES,
            "selected_category": category,
            "selected_day": day or date.today(),
            "added": added,
        })

    def submit_expense(self, expense: Annotated[Expense, Form()]):
        self.add_expense(expense)
        query = urlencode({"category": expense.category, "day": expense.day, "added": 1})
        return RedirectResponse(f"/?{query}", status_code=303)

    def get_categories(self):
        return [{"code": code, "title": title} for code, title in CATEGORIES.items()]

    def get_expenses(self):
        with database() as db:
            rows = [dict(row) for row in db.execute("SELECT * FROM expenses ORDER BY day DESC, id DESC")]
        return {"total_kopeyki": sum(row["kopeyki"] for row in rows), "entries": rows}

    def add_expense(self, expense: Expense):
        if expense.category not in CATEGORIES:
            raise HTTPException(422, "Неизвестная категория")
        kopeyki = int(expense.rubles * 100)
        with database() as db:
            cursor = db.execute(
                """INSERT INTO expenses (kopeyki, category, day, comment)
                   VALUES (:kopeyki, :category, :day, :comment)""",
                {
                    "kopeyki": kopeyki,
                    "category": expense.category,
                    "day": expense.day.isoformat(),
                    "comment": expense.comment.strip(),
                },
            )
            return {"id": cursor.lastrowid}


app = ExpenseTracker().app
