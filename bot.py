import os
import telebot
from telebot import apihelper
from groq import Groq

# Токены из переменных окружения
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

if not TELEGRAM_TOKEN or not GROQ_API_KEY:
    raise ValueError("Не заданы TELEGRAM_TOKEN или GROQ_API_KEY")

# Инициализация клиентов
bot = telebot.TeleBot(TELEGRAM_TOKEN)
groq_client = Groq(api_key=GROQ_API_KEY)

# Хранилище контекста (в памяти — для cron-режима не сохраняется между запусками)
conversation_history = {}

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, 
        "Привет! Я AI-бот на Groq.\n"
        "Напиши любой вопрос — отвечу.\n"
        "Доступные модели: llama-3.3-70b-versatile, llama-3.1-8b-instant"
    )

@bot.message_handler(commands=['clear'])
def clear_history(message):
    conversation_history.pop(message.chat.id, None)
    bot.reply_to(message, "Контекст очищен.")

@bot.message_handler(func=lambda msg: True)
def handle_message(message):
    chat_id = message.chat.id
    user_text = message.text
    
    # Отправляем "печатает..."
    bot.send_chat_action(chat_id, 'typing')
    
    # Получаем или создаём историю диалога
    if chat_id not in conversation_history:
        conversation_history[chat_id] = []
    
    # Добавляем сообщение пользователя
    conversation_history[chat_id].append({
        "role": "user",
        "content": user_text
    })
    
    # Ограничиваем историю последними 10 сообщениями
    messages = conversation_history[chat_id][-10:]
    
    try:
        # Запрос к Groq (OpenAI-совместимый API)
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "Ты полезный ассистент. Отвечай кратко и по делу."},
                *messages
            ],
            temperature=0.7,
            max_tokens=1024
        )
        
        ai_response = response.choices[0].message.content
        
        # Сохраняем ответ в историю
        conversation_history[chat_id].append({
            "role": "assistant",
            "content": ai_response
        })
        
        # Отправляем ответ (разбиваем если длинный)
        if len(ai_response) > 4000:
            for i in range(0, len(ai_response), 4000):
                bot.send_message(chat_id, ai_response[i:i+4000])
        else:
            bot.reply_to(message, ai_response)
            
    except Exception as e:
        bot.reply_to(message, f"Ошибка: {str(e)}")

if __name__ == "__main__":
    # ВАЖНО: для GitHub Actions это запустится и сразу завершится
    # Нужно использовать infinity_polling с таймаутом или webhook
    print("Бот запущен...")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
