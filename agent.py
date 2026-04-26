import os
import sys
import threading
import requests
import re
from bs4 import BeautifulSoup
from flask import Flask
from groq import Groq
from supabase import create_client
from ddgs import DDGS
from dotenv import load_dotenv
import telebot

load_dotenv()

# Configuration & Security Check
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not all([GROQ_API_KEY, TELEGRAM_BOT_TOKEN]):
    print("❌ Critical Error: Environment Variables are missing!")
    sys.exit(1)

# Initialize Clients
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
groq_client = Groq(api_key=GROQ_API_KEY)
supabase = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None

app = Flask(__name__)

@app.route('/')
def home(): return "Professional SEO Engine is Online."

# --- Advanced Tools ---
def get_web_content(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        res = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # Extract metadata
        title = soup.title.string if soup.title else "N/A"
        desc = soup.find('meta', attrs={'name': 'description'})
        desc = desc['content'] if desc else "N/A"
        emails = list(set(re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', res.text)))
        
        return f"Source: {url}\nTitle: {title}\nMeta Description: {desc}\nEmails Found: {emails}\n"
    except: return "Could not retrieve data from URL."

def professional_search(query):
    try:
        results = DDGS().text(query, max_results=5)
        return "\n\n".join([f"Info: {r['body']}\nLink: {r['href']}" for r in results])
    except: return "Search unavailable at the moment."

# --- Agent Brain ---
def run_professional_agent(user_prompt):
    # Context gathering
    url_match = re.search(r'(https?://\S+)', user_prompt)
    web_context = get_web_content(url_match.group(0)) if url_match else ""
    search_context = professional_search(user_prompt)

    system_message = f"""You are 'Biplob's SEO Engine', a highly sophisticated AI developed for Md Biplob Hossen.
    Your owner: Md Biplob Hossen (SEO Expert & Web Developer).
    
    Guidelines:
    1. Strictly Professional: Use a formal, corporate tone. No informal chatting.
    2. Data-Driven: Base answers on the provided context. If data is missing, state it clearly.
    3. Lead Generation: If a YouTube/Website link is found, prioritize extracting contact info and SEO metrics.
    4. Signature: Always end with your owner's professional signature.
    
    Context Data:
    {web_context}
    {search_context}
    """
    
    try:
        response = groq_client.chat.completions.create(
            messages=[{"role": "system", "content": system_message}, {"role": "user", "content": user_prompt}],
            model="llama-3.3-70b-versatile",
            temperature=0.3, # Lower temperature for more factual and less 'creative' answers
        )
        answer = response.choices[0].message.content
        return f"{answer}\n\n---\n**Md Biplob Hossen**\n*SEO Expert & Web Developer*"
    except Exception as e:
        return f"Technical Error: {str(e)}"

# --- Telegram Handlers ---
@bot.message_handler(commands=['start'])
def welcome(message):
    bot.reply_to(message, "গোপন সোর্স এবং এআই ডাটাবেসে আপনাকে স্বাগতম, বিপ্লব। আমি আপনার প্রফেশনাল এসইও এবং লিড জেনারেশন ইঞ্জিন। যেকোনো প্রজেক্ট বা লিংক দিয়ে আমাকে কমান্ড দিন।")

@bot.message_handler(func=lambda message: True)
def handle(message):
    status_msg = bot.reply_to(message, "⏳ প্রফেশনাল ডাটা এনালাইসিস চলছে...")
    final_output = run_professional_agent(message.text)
    bot.edit_message_text(chat_id=message.chat.id, message_id=status_msg.message_id, text=final_output, parse_mode="Markdown")

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))).start()
    bot.infinity_polling()
