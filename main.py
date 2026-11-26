import json
from datetime import date
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlencode

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from categories import CATEGORIES

ROOT = Path(__file__).resolve().parent #путь к файлу main.py


class Expense(BaseModel): #создаем модель расходов с проверкой данных
    rubles: Decimal = Field(gt=0, max_digits=12, decimal_places=2) 
    category: str
    day: date
    comment: str = Field(default="", max_length=300)


class ExpenseTracker:
    def __init__(self):
        with (ROOT / "config.json").open(encoding="utf-8") as file:
            config = json.load(file)

        self.expenses = {}
        self.next_id = 1

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
        self.app.post("/expenses/{expense_id}/delete")(self.delete_expense)
        self.app.get("/api/categories")(self.get_categories)
        self.app.get("/api/expenses")(self.get_expenses)
        self.app.post("/api/expenses", status_code=201)(self.add_expense)

    async def index(self, request: Request, category: str = "", day: date | None = None, added: bool = False): #функция для заполнения фронтенда
        return self.templates.TemplateResponse(request, "index.html", {
            **(await self.get_expenses()),
            "categories": CATEGORIES,
            "selected_category": category,
            "selected_day": day or date.today(),
            "added": added,
        })

    async def submit_expense(self, expense: Expense = Form()): #функция для добавления расхода через фронтенд
        await self.add_expense(expense)
        query = urlencode({"category": expense.category, "day": expense.day, "added": 1})
        return RedirectResponse(f"/?{query}", status_code=303)

    async def delete_expense(self, expense_id: int): #удаляем выбранный расход по его id
        self.expenses.pop(expense_id, None)
        return RedirectResponse(url="/", status_code=303)

    def get_categories(self):
        return [{"code": code, "title": title} for code, title in CATEGORIES.items()]

    async def get_expenses(self): #функция для получения списка расходов и их общей суммы
        rows = list(self.expenses.values())
        rows.sort(key=lambda row: (row["day"], row["id"]), reverse=True)
        return {"total_kopeyki": sum(row["kopeyki"] for row in rows), "entries": rows}

    async def add_expense(self, expense: Expense): #записываем расход в словарь
        if expense.category not in CATEGORIES:
            raise HTTPException(422, "Неизвестная категория")
        kopeyki = int(expense.rubles * 100)
        expense_id = self.next_id
        self.next_id += 1
        self.expenses[expense_id] = {
            "id": expense_id,
            "kopeyki": kopeyki,
            "category": expense.category,
            "day": expense.day.isoformat(),
            "comment": expense.comment.strip(),
        }
        return {"id": expense_id}


app = ExpenseTracker().app
