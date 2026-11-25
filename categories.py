class ExpenseCategory:
    code: str
    title: str


class Groceries(ExpenseCategory):
    code, title = "groceries", "Продукты"


class Transport(ExpenseCategory):
    code, title = "transport", "Транспорт"


class Home(ExpenseCategory):
    code, title = "home", "Дом"


class Leisure(ExpenseCategory):
    code, title = "leisure", "Досуг"


class Health(ExpenseCategory):
    code, title = "health", "Здоровье"


class Other(ExpenseCategory):
    code, title = "other", "Другое"


CATEGORIES = {
    category.code: category.title
    for category in (Groceries, Transport, Home, Leisure, Health, Other)
}
