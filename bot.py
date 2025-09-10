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
from timezonefinder import TimezoneFinder
import datetime
import pytz



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
        lat = city_info['lat']
        lon = city_info['lon']
        city_name = city_info['name']

        # Определяем таймзону
        tf = TimezoneFinder()
        timezone_str = tf.timezone_at(lat=lat, lng=lon)

        # Считаем смещение UTC
        tz_offset = None
        if timezone_str:
            tz = pytz.timezone(timezone_str)
            tz_offset = int(tz.utcoffset(datetime.datetime.utcnow()).total_seconds() / 3600)

        # Сохраняем в базу
        db.update_city(tg_id, city_name, lat, lon, timezone_str, tz_offset)

        bot.send_message(chat_id, f"Город успешно сохранён: {city_name} ✅\n"
                                  f"Таймзона: {timezone_str}, UTC{tz_offset:+d}")

        # Сразу проверяем погоду и отправляем уведомление
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
        save_city(message)


def send_daily_notifications():
    users = db.get_all_users()
    now_utc = datetime.now(timezone.utc)

    for user in users:
        tg_id, city, lat, lon, tz_offset = user

        if not city or not lat or not lon or tz_offset is None:
            continue

        # Локальное время пользователя
        user_time = now_utc + timedelta(hours=tz_offset)

        # Если сейчас у пользователя 08:00 (± 5 минут для надёжности)
        if user_time.hour == 8 and user_time.minute < 5:
            try:
                weather = get_weather(lat, lon)
                notify = False
                message = f"Погода в {city} сегодня:\n"

                if weather["precipitation_type"] in ["rain", "snow"]:
                    notify = True
                    message += f"❗ Ожидаются осадки: {weather['precipitation_type']}\n"

                if weather["temp_max"] > 25:
                    notify = True
                    message += f"🔥 Жара: до {weather['temp_max']}°C\n"

                if notify:
                    bot.send_message(tg_id, message)

            except Exception as e:
                print(f"Ошибка при отправке уведомления пользователю {tg_id}: {e}")

def run_scheduled_notifications():
    schedule.every().day.at("08:00").do(send_daily_notifications, bot=bot)

    while True:
        schedule.run_pending()
        time.sleep(30)  

# -------------------- Запуск бота --------------------
if __name__ == "__main__":
    db.init_db()
    print("Бот запущен...")

    threading.Thread(target=run_scheduled_notifications, daemon=True).start()

    bot.infinity_polling()

