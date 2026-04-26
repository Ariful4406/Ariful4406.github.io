import os
import threading
from flask import Flask
from groq import Groq
from supabase import create_client, Client
from ddgs import DDGS
from dotenv import load_dotenv
import telebot

# Environment Variables
load_dotenv()

# API Keys
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Initialize Clients
if GROQ_API_KEY:
    groq_client = Groq(api_key=GROQ_API_KEY)
else:
    groq_client = None

if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
else:
    supabase = None

# Telegram Bot
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# Flask Server (Render কে জাগিয়ে রাখার জন্য)
app = Flask(__name__)
@app.route('/')
def home():
    return "Llama-3 Agent is Running super fast with Groq!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

def web_search_tool(query):
    """ফ্রিতে ইন্টারনেট সার্চ"""
    try:
        results = DDGS().text(query, max_results=3)
        search_results = []
        for item in results:
            search_results.append(f"Title: {item.get('title')}\nSnippet: {item.get('body')}\nSource: {item.get('href')}")
        return "\n\n".join(search_results)
    except Exception as e:
        return "No recent data found."

def save_to_memory(user_input, bot_output):
    if not supabase: return
    data = {"user_query": user_input, "agent_response": bot_output}
    try:
        supabase.table("agent_memory").insert(data).execute()
    except Exception:
        pass

def run_agent(user_prompt):
    context = web_search_tool(user_prompt)
    
    system_prompt = f"""You are a professional AI Assistant. Answer the user's question clearly. 
    If the question needs current info, use the following internet data: \n{context}"""
    
    if groq_client:
        try:
            # Llama-3 এর সবচেয়ে পাওয়ারফুল মডেলটি ব্যবহার করা হচ্ছে
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
    else:
        final_answer = "Error: Groq API Key is missing."
    
    save_to_memory(user_prompt, final_answer)
    return final_answer

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "হ্যালো! আমি আপনার সুপারফাস্ট Groq AI (Llama-3) এজেন্ট। আমাকে যেকোনো কিছু জিজ্ঞাসা করতে পারেন।")

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
    bot.infinity_polling()
