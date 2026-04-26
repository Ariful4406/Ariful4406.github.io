import os
import google.generativeai as genai
from supabase import create_client, Client
from duckduckgo_search import DDGS
from dotenv import load_dotenv

# Load Environment Variables
load_dotenv()

# Setup API Keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Initialize Clients
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
if SUPABASE_URL and SUPABASE_KEY:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def web_search_tool(query):
    """Free Web Search using DuckDuckGo"""
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
    """Save to Supabase Database"""
    if not SUPABASE_URL or not SUPABASE_KEY:
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
    """Main Agent Logic"""
    context = web_search_tool(user_prompt)
    
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
    
    save_to_memory(user_prompt, final_answer)
    
    return final_answer

if __name__ == "__main__":
    print("Starting AI Agent...")
    user_input = "Latest AI trends 2026"
    result = run_agent(user_input)
    print("\n--- AGENT RESPONSE ---\n")
    print(result)
    print("\nAgent finished its task successfully!")
