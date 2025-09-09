import os
import telebot
from telebot import types
from dotenv import load_dotenv
import db
import requests
import datetime
from weather import get_weather
import schedule
import time
import threading

# -------------------- Загрузка токенов --------------------
load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")

bot = telebot.TeleBot(TOKEN)

# -------------------- /start --------------------
@bot.message_handler(commands=['start'])
def start(message):
    tg_id = message.from_user.id
    chat_id = message.chat.id

    # Добавляем пользователя в БД
    db.add_user(tg_id, chat_id)

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_city = types.KeyboardButton("Выбрать город")
    btn_analytics = types.KeyboardButton("Моя аналитика")
    markup.add(btn_city, btn_analytics)

    bot.send_message(chat_id,
                     "Привет! Я бот-погодник 🌤\nВыбери действие ниже или напиши город вручную:",
                     reply_markup=markup)

# -------------------- /help --------------------
@bot.message_handler(commands=['help'])
def help_cmd(message):
    chat_id = message.chat.id
    bot.send_message(chat_id,
                     "Команды:\n"
                     "/start - начать работу с ботом\n"
                     "/help - помощь\n"
                     "/setcity - изменить город")

# -------------------- /setcity --------------------
@bot.message_handler(commands=['setcity'])
def setcity(message):
    chat_id = message.chat.id
    msg = bot.send_message(chat_id, "Напиши название города (например, Moscow):")
    bot.register_next_step_handler(msg, save_city)

# -------------------- Сохраняем город --------------------
def save_city(message):
    chat_id = message.chat.id
    tg_id = message.from_user.id
    city_name = message.text.strip()

    # Простейший геокодинг через OpenWeatherMap
    url = "http://api.openweathermap.org/geo/1.0/direct"
    params = {"q": city_name, "limit": 1, "appid": WEATHER_API_KEY}
    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        if not data:
            bot.send_message(chat_id, "Город не найден 😢 Попробуй ещё раз.")
            return
        city_info = data[0]
        db.update_city(tg_id, city_info['name'], city_info['lat'], city_info['lon'])
        bot.send_message(chat_id, f"Город успешно сохранён: {city_info['name']} ✅")

        # 🔹 Сразу проверяем погоду и отправляем уведомление
        try:
            w = get_weather(city_info['lat'], city_info['lon'])
            today_str = datetime.datetime.utcnow().strftime("%Y-%m-%d")

            send_msg = None
            if w['precipitation_type'] in ["rain", "snow"]:
                send_msg = f"Прогноз на сегодня в {city_info['name']}: {w['condition']} 🌧❄️"
            elif w['temp_max'] >= 25:
                send_msg = f"Сегодня в {city_info['name']} жарко 🔥 {w['temp_max']}°C"

            if send_msg:
                bot.send_message(chat_id, send_msg)
                db.save_weather_sample(tg_id, today_str,
                                       w['temp'], w['temp_max'], w['temp_min'],
                                       w['condition'], w['precipitation_type'],
                                       w['pop'], w['raw_json'])
                db.update_last_notify_date(tg_id, today_str)

        except Exception as e:
            bot.send_message(chat_id, f"Ошибка при проверке погоды: {e}")

    except Exception as e:
        bot.send_message(chat_id, f"Ошибка при определении города: {e}")


# -------------------- Обработка сообщений (кнопки Reply) --------------------
@bot.message_handler(func=lambda message: True)
def reply_buttons(message):
    text = message.text
    chat_id = message.chat.id

    if text == "Выбрать город":
        setcity(message)
    elif text == "Моя аналитика":
        bot.send_message(chat_id, "Пока аналитика не готова, будет позже 📊")
    else:
        # Можно сделать обработку как нового города
        save_city(message)


def send_daily_notifications(bot):
    """
    Проходим по всем пользователям и отправляем уведомления
    если дождь/снег/жара > 25°C
    """
    today_str = datetime.datetime.utcnow().strftime("%Y-%m-%d")
    users = db.get_all_users()

    for u in users:
        if u['notify_morning'] != 1:
            continue  # пропускаем тех, кто отключил уведомления

        # чтобы не слать дважды за день
        if u['last_notify_date'] == today_str:
            continue

        if not u['city'] or not u['lat'] or not u['lon']:
            continue  # город не выбран

        try:
            w = get_weather(u['lat'], u['lon'])
            db.save_weather_sample(u['tg_id'], today_str,
                                   w['temp'], w['temp_max'], w['temp_min'],
                                   w['condition'], w['precipitation_type'],
                                   w['pop'], w['raw_json'])

            send_msg = None
            if w['precipitation_type'] in ["rain", "snow"]:
                send_msg = f"Прогноз на сегодня в {u['city']}: {w['condition']} 🌧❄️"
            elif w['temp_max'] >= 25:
                send_msg = f"Сегодня в {u['city']} жарко 🔥 {w['temp_max']}°C"

            if send_msg:
                bot.send_message(u['chat_id'], send_msg)
                db.update_last_notify_date(u['tg_id'], today_str)
        except Exception as e:
            print(f"Ошибка при отправке уведомления для {u['tg_id']}: {e}")

def run_scheduled_notifications():
    schedule.every().day.at("08:00").do(send_daily_notifications, bot=bot)

    while True:
        schedule.run_pending()
        time.sleep(30)  # проверяем каждые 30 секунд

# -------------------- Запуск бота --------------------
if __name__ == "__main__":
    db.init_db()
    print("Бот запущен...")

    threading.Thread(target=run_scheduled_notifications, daemon=True).start()

    bot.infinity_polling()

