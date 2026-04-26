import os
import sys
import threading
from flask import Flask
from groq import Groq
from supabase import create_client, Client
from ddgs import DDGS
from dotenv import load_dotenv
import telebot

# Environment Variables Load
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# --- Error Checking ---
if not TELEGRAM_BOT_TOKEN:
    print("\n" + "="*50)
    print("❌ ERROR: TELEGRAM_BOT_TOKEN is missing in Render!")
    print("Please add TELEGRAM_BOT_TOKEN in Environment Variables.")
    print("="*50 + "\n")
    sys.exit(1)

if not GROQ_API_KEY:
    print("\n" + "="*50)
    print("❌ ERROR: GROQ_API_KEY is missing in Render!")
    print("Please add GROQ_API_KEY in Environment Variables.")
    print("="*50 + "\n")
    sys.exit(1)

# Initialize Clients
groq_client = Groq(api_key=GROQ_API_KEY)
if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
else:
    supabase = None

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

app = Flask(__name__)
@app.route('/')
def home():
    return "Llama-3 Agent is Running super fast with Groq!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

def web_search_tool(query):
    try:
        results = DDGS().text(query, max_results=3)
        return "\n\n".join([f"Title: {item.get('title')}\nSnippet: {item.get('body')}" for item in results])
    except Exception:
        return "No recent data found."

def save_to_memory(user_input, bot_output):
    if not supabase: return
    try:
        supabase.table("agent_memory").insert({"user_query": user_input, "agent_response": bot_output}).execute()
    except Exception:
        pass

def run_agent(user_prompt):
    context = web_search_tool(user_prompt)
    system_prompt = f"You are a helpful AI Assistant. Use this info to answer if needed: \n{context}"
    
    try:
        chat_completion = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            model="llama3-70b-8192",
            temperature=0.5,
        )
        final_answer = chat_completion.choices[0].message.content
    except Exception as e:
        final_answer = f"Error generating content: {e}"
        
    save_to_memory(user_prompt, final_answer)
    return final_answer

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "হ্যালো! আমি আপনার সুপারফাস্ট Groq AI (Llama-3) এজেন্ট।")

@bot.message_handler(func=lambda message: True)
def handle_user_message(message):
    processing_msg = bot.reply_to(message, "⚡ দ্রুত তথ্য খুঁজছি...")
    answer = run_agent(message.text)
    try:
        bot.edit_message_text(chat_id=message.chat.id, message_id=processing_msg.message_id, text=answer)
    except Exception:
        bot.send_message(message.chat.id, answer)

if __name__ == "__main__":
    print("Starting Web Server...")
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()
    
    print("Starting Telegram Bot with Groq...")
    try:
        bot.infinity_polling()
    except Exception as e:
        print(f"\n❌ Telegram Bot Error: {e}\n")
