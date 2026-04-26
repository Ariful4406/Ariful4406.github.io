import os
import sys
import threading
from flask import Flask
from groq import Groq
from supabase import create_client, Client
from ddgs import DDGS
from dotenv import load_dotenv
import telebot

load_dotenv()

# Config
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not TELEGRAM_BOT_TOKEN or not GROQ_API_KEY:
    sys.exit(1)

groq_client = Groq(api_key=GROQ_API_KEY)
supabase = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
app = Flask(__name__)

@app.route('/')
def home():
    return "AI Agent is Online!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

def web_search_tool(query):
    try:
        results = DDGS().text(query, max_results=3)
        return "\n\n".join([f"Title: {item.get('title')}\nSnippet: {item.get('body')}" for item in results])
    except Exception:
        return "No recent internet data found."

def run_agent(user_prompt):
    context = web_search_tool(user_prompt)
    system_prompt = f"You are a helpful AI Assistant. Search Context: \n{context}"
    
    # প্রথমে শক্তিশালী মডেল চেষ্টা করবে, না হলে ছোট মডেল ব্যবহার করবে
    models_to_try = ["llama-3.3-70b-versatile", "llama3-8b-8192"]
    
    final_answer = ""
    for model_name in models_to_try:
        try:
            chat_completion = groq_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model=model_name,
                temperature=0.6,
            )
            final_answer = chat_completion.choices[0].message.content
            break # উত্তর পেয়ে গেলে লুপ থেকে বের হয়ে যাবে
        except Exception as e:
            final_answer = f"Error with {model_name}: {str(e)}"
            continue # এরর হলে পরের মডেলটি ট্রাই করবে
            
    return final_answer

@bot.message_handler(func=lambda message: True)
def handle_user_message(message):
    processing_msg = bot.reply_to(message, "⏳ তথ্য খুঁজছি এবং চিন্তা করছি...")
    answer = run_agent(message.text)
    try:
        bot.edit_message_text(chat_id=message.chat.id, message_id=processing_msg.message_id, text=answer)
    except Exception:
        bot.send_message(message.chat.id, answer)

if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    bot.infinity_polling()
