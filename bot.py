# bot.py
import os
import telebot
from groq import Groq

# Токены из переменных окружения (задаются в GitHub Secrets)
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

if not TELEGRAM_TOKEN or not GROQ_API_KEY:
    raise ValueError("Не заданы TELEGRAM_TOKEN или GROQ_API_KEY")

# Инициализация
bot = telebot.TeleBot(TELEGRAM_TOKEN)
groq_client = Groq(api_key=GROQ_API_KEY)

# Хранилище контекста диалога (в памяти — сбрасывается при перезапуске)
conversation_history = {}

MODEL = "openai/gpt-oss-120b"  # Актуальная бесплатная модель Groq
SYSTEM_PROMPT = "Ты полезный ассистент. Отвечай кратко и по делу на русском языке."


@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(
        message,
        "Привет! Я AI-бот на базе Groq.\n"
        "Напиши любой вопрос — отвечу.\n\n"
        "Команды:\n"
        "/clear — очистить контекст диалога"
    )


@bot.message_handler(commands=['clear'])
def clear_history(message):
    conversation_history.pop(message.chat.id, None)
    bot.reply_to(message, "Контекст диалога очищен.")


@bot.message_handler(func=lambda msg: True)
def handle_message(message):
    chat_id = message.chat.id
    user_text = message.text

    bot.send_chat_action(chat_id, 'typing')

    # Получаем или создаём историю
    if chat_id not in conversation_history:
        conversation_history[chat_id] = []

    conversation_history[chat_id].append({
        "role": "user",
        "content": user_text
    })

    # Ограничиваем историю последними 10 сообщениями
    messages = conversation_history[chat_id][-10:]

    try:
        response = groq_client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                *messages
            ],
            temperature=0.7,
            max_tokens=1024
        )

        ai_response = response.choices[0].message.content

        # Сохраняем ответ
        conversation_history[chat_id].append({
            "role": "assistant",
            "content": ai_response
        })

        # Отправляем (разбиваем длинные сообщения)
        if len(ai_response) > 4000:
            for i in range(0, len(ai_response), 4000):
                bot.send_message(chat_id, ai_response[i:i+4000])
        else:
            bot.reply_to(message, ai_response)

    except Exception as e:
        bot.reply_to(message, f"Ошибка: {str(e)}")


if __name__ == "__main__":
    print("Бот запущен...")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
