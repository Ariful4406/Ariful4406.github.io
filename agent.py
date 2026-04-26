import os
import sys
import threading
import requests
from bs4 import BeautifulSoup
from flask import Flask
from groq import Groq
from supabase import create_client, Client
from ddgs import DDGS
from dotenv import load_dotenv
import telebot

load_dotenv()

# API Keys
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
groq_client = Groq(api_key=GROQ_API_KEY)
supabase = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None

app = Flask(__name__)

@app.route('/')
def home(): return "SEO AI Agent is Live!"

# --- টুলস: ওয়েব স্ক্র্যাপার এবং এসইও অ্যানালাইজার ---
def seo_scraper_tool(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        title = soup.title.string if soup.title else "No Title"
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        desc = meta_desc['content'] if meta_desc else "No Meta Description"
        h1s = [h1.get_text() for h1 in soup.find_all('h1')]
        
        return f"URL: {url}\nTitle: {title}\nDescription: {desc}\nH1 Tags: {h1s}"
    except Exception as e:
        return f"Error scraping URL: {e}"

def web_search_tool(query):
    try:
        results = DDGS().text(query, max_results=3)
        return "\n\n".join([f"Title: {item.get('title')}\nSnippet: {item.get('body')}" for item in results])
    except Exception:
        return "No search data found."

# --- মূল এজেন্ট লজিক ---
def run_agent(user_prompt):
    # যদি মেসেজে কোনো URL থাকে, তবে স্ক্র্যাপার একটিভ হবে
    scrape_context = ""
    if "http" in user_prompt:
        url = [word for word in user_prompt.split() if "http" in word][0]
        scrape_context = seo_scraper_tool(url)
    
    search_context = web_search_tool(user_prompt)
    
    system_prompt = f"""You are a professional SEO Expert and Web Developer AI Assistant. 
    Your owner is Md Biplob Hossen. 
    If a URL is provided, analyze its SEO based on this data: {scrape_context}
    Use this search data if needed: {search_context}
    Always provide professional, actionable SEO and Web Dev advice."""
    
    try:
        chat_completion = groq_client.chat.completions.create(
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            model="llama-3.3-70b-versatile",
            temperature=0.5,
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        return f"Error: {e}"

# --- টেলিগ্রাম হ্যান্ডলার ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "হ্যালো! আমি বিপ্লবের এসইও এবং ওয়েব দেব এজেন্ট। কোনো ওয়েবসাইটের লিংক দিন, আমি সেটির এসইও অডিট করে দিচ্ছি।")

@bot.message_handler(func=lambda message: True)
def handle_user_message(message):
    msg = bot.reply_to(message, "⏳ এনালাইসিস করছি...")
    answer = run_agent(message.text)
    bot.edit_message_text(chat_id=message.chat.id, message_id=msg.message_id, text=answer)

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))).start()
    bot.infinity_polling()
