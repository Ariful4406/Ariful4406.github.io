import os
import threading
from flask import Flask
from google import genai
from supabase import create_client, Client
from ddgs import DDGS
from dotenv import load_dotenv
import telebot

# এনভায়রনমেন্ট ভেরিয়েবল লোড করা
load_dotenv()

# API Keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# ক্লায়েন্ট ইনিশিয়ালাইজ করা
if GEMINI_API_KEY:
    gemini_client = genai.Client(api_key=GEMINI_API_KEY)
if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
else:
    supabase = None

# টেলিগ্রাম বট ইনিশিয়ালাইজ করা
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# Render-কে সন্তুষ্ট রাখার জন্য একটি ডামি Flask সার্ভার
app = Flask(__name__)
@app.route('/')
def home():
    return "AI Agent is Running and Connected to Telegram!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

def web_search_tool(query):
    """DuckDuckGo ব্যবহার করে ইন্টারনেট সার্চ"""
    try:
        results = DDGS().text(query, max_results=3)
        search_results = []
        for item in results:
            search_results.append(f"Title: {item.get('title')}\nSnippet: {item.get('body')}\nSource: {item.get('href')}")
        return "\n\n".join(search_results)
    except Exception as e:
        return "No recent data found."

def save_to_memory(user_input, bot_output):
    """সুপাবেস ডাটাবেসে সেভ করা"""
    if not supabase: return
    data = {"user_query": user_input, "agent_response": bot_output}
    try:
        supabase.table("agent_memory").insert(data).execute()
    except Exception as e:
        print(f"Memory saving failed: {e}")

def run_agent(user_prompt):
    """এজেন্টের মূল লজিক"""
    context = web_search_tool(user_prompt)
    
    full_prompt = f"""
    You are a professional AI Assistant.
    User Question: {user_prompt}
    
    Latest Information from Internet:
    {context}
    
    Please provide a helpful, detailed, and expert answer based on the above info.
    """
    
    if gemini_client:
        try:
            response = gemini_client.models.generate_content(
                model='gemini-2.0-flash',
                contents=full_prompt
            )
            final_answer = response.text
        except Exception as e:
            final_answer = f"Error generating content: {e}"
    else:
        final_answer = "Error: Gemini API Key is missing."
    
    save_to_memory(user_prompt, final_answer)
    return final_answer

# --- টেলিগ্রাম বটের কমান্ড এবং মেসেজ হ্যান্ডলার ---

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "হ্যালো! আমি আপনার পার্সোনাল এআই এজেন্ট। আমাকে যেকোনো কিছু জিজ্ঞাসা করতে পারেন।")

@bot.message_handler(func=lambda message: True)
def handle_user_message(message):
    # ইউজারকে জানানো হচ্ছে যে বট কাজ করছে
    processing_msg = bot.reply_to(message, "⏳ তথ্য খুঁজছি এবং চিন্তা করছি...")
    
    # এজেন্টের মাধ্যমে উত্তর তৈরি করা
    answer = run_agent(message.text)
    
    # উত্তরটি পাঠানো
    bot.edit_message_text(chat_id=message.chat.id, message_id=processing_msg.message_id, text=answer)


if __name__ == "__main__":
    print("Starting Web Server...")
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()
    
    print("Starting Telegram Bot...")
    bot.infinity_polling()
