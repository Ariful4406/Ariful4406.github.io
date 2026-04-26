import os
from google import genai
from supabase import create_client, Client
from ddgs import DDGS
from dotenv import load_dotenv

# এনভায়রনমেন্ট ভেরিয়েবল লোড করা
load_dotenv()

# API Keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# ক্লায়েন্ট ইনিশিয়ালাইজ করা
if GEMINI_API_KEY:
    gemini_client = genai.Client(api_key=GEMINI_API_KEY)
else:
    gemini_client = None

if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
else:
    supabase = None

def web_search_tool(query):
    """DuckDuckGo ব্যবহার করে ফ্রি ইন্টারনেট সার্চ"""
    print(f"Searching internet for: {query}...")
    try:
        results = DDGS().text(query, max_results=3)
        search_results = []
        for item in results:
            search_results.append(f"Title: {item.get('title')}\nSnippet: {item.get('body')}\nSource: {item.get('href')}")
        return "\n\n".join(search_results)
    except Exception as e:
        print(f"Search failed: {e}")
        return "No recent data found."

def save_to_memory(user_input, bot_output):
    """সুপাবেস ডাটাবেসে সেভ করা"""
    if not supabase:
        print("Supabase keys missing. Skipping memory save.")
        return
        
    data = {
        "user_query": user_input,
        "agent_response": bot_output
    }
    try:
        supabase.table("agent_memory").insert(data).execute()
        print("Memory saved successfully.")
    except Exception as e:
        print(f"Memory saving failed: {e}")

def run_agent(user_prompt):
    """মূল এজেন্টের লজিক"""
    context = web_search_tool(user_prompt)
    
    full_prompt = f"""
    You are a professional AI Agent.
    User Question: {user_prompt}
    
    Latest Information from Internet:
    {context}
    
    Please provide a detailed and expert answer based on the above info.
    """
    
    print("Agent is generating response...")
    if gemini_client:
        try:
            # গুগলের নতুন মডেল gemini-2.5-flash ব্যবহার করা হচ্ছে
            response = gemini_client.models.generate_content(
                model='gemini-2.5-flash',
                contents=full_prompt
            )
            final_answer = response.text
        except Exception as e:
            final_answer = f"Error generating content: {e}"
    else:
        final_answer = "Error: Gemini API Key missing or incorrect."
    
    save_to_memory(user_prompt, final_answer)
    
    return final_answer

if __name__ == "__main__":
    print("Starting AI Agent...")
    user_input = "Latest AI trends 2026"
    result = run_agent(user_input)
    print("\n--- AGENT RESPONSE ---\n")
    print(result)
    print("\nAgent finished its task successfully!")
