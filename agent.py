import os
import google.generativeai as genai
from supabase import create_client, Client
from apify_client import ApifyClient
from dotenv import load_dotenv

# Load Environment Variables
load_dotenv()

# Setup API Keys from Environment Variables
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
APIFY_TOKEN = os.getenv("APIFY_TOKEN")

# Initialize Clients
genai.configure(api_key=GEMINI_API_KEY)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
apify_client = ApifyClient(APIFY_TOKEN)

def web_search_tool(query):
    """Internet theke latest data khuje ber korar tool"""
    print(f"Searching internet for: {query}...")
    run_input = {
        "queries": [query],
        "resultsPerPage": 3,
        "maxPagesPerQuery": 1
    }
    # Using Google Search Scraper
    run = apify_client.actor("apify/google-search-scraper").call(run_input=run_input)
    
    search_results = []
    for item in apify_client.dataset(run["defaultDatasetId"]).iterate_items():
        search_results.append(f"Title: {item.get('title')}\nSnippet: {item.get('snippet')}\nSource: {item.get('url')}")
    
    return "\n\n".join(search_results)

def save_to_memory(user_input, bot_output):
    """Supabase database-e conversation save rakha"""
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
    """Main Agent Logic"""
    # 1. First, search for fresh info
    context = web_search_tool(user_prompt)
    
    # 2. Prepare the Brain (Gemini)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    full_prompt = f"""
    You are a professional AI Agent.
    User Question: {user_prompt}
    
    Latest Information from Internet:
    {context}
    
    Please provide a detailed and expert answer based on the above info.
    """
    
    print("Agent is generating response...")
    response = model.generate_content(full_prompt)
    final_answer = response.text
    
    # 3. Save conversation to Supabase
    save_to_memory(user_prompt, final_answer)
    
    return final_answer

if __name__ == "__main__":
    # Test your agent here
    user_input = "Latest WordPress SEO trends 2026"
    result = run_agent(user_input)
    print("\n--- AGENT RESPONSE ---\n")
    print(result)
