# google_sheets.py
import os
from datetime import datetime
import db
from gspread import Spreadsheet
from oauth2client.service_account import ServiceAccountCredentials
import gspread

# Подключение к Google Sheets
def get_sheet() -> Spreadsheet:
    scope = ["https://spreadsheets.google.com/feeds",
             "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(
        os.getenv("GOOGLE_CREDENTIALS_JSON"), scope
    )
    client = gspread.authorize(creds)
    sheet = client.open_by_key(os.getenv("SPREADSHEET_ID")).sheet1
    return sheet

def append_rows_to_sheet(rows: list):
    """Добавляет список строк в конец таблицы"""
    sheet = get_sheet()
    sheet.append_rows(rows)

def export_weather_to_sheets(tg_id, period="-1 month"):
    """Экспорт погодной аналитики пользователя в Google Sheets"""
    user = db.get_user_by_tg_id(tg_id)
    if not user or not user.get("city"):
        return "Сначала выберите город"

    city = user["city"]
    data = db.get_weather_counts(tg_id, city, period)
    if not data:
        return "Нет данных для экспорта"

    today_str = datetime.today().strftime("%Y-%m-%d")
    rows = []
    for condition, count in data:
        rows.append([tg_id, city, today_str, condition, count])

    append_rows_to_sheet(rows)
    return f"Экспорт завершён. Добавлено {len(rows)} строк"
