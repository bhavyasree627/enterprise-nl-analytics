import os
import time
import sqlite3
import requests
import json
import streamlit as st
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

DB_NAME = "enterprise_stocks.db"

def _get_api_key():
    # Hosted: read from Streamlit secrets
    try:
        key = st.secrets["GEMINI_API_KEY"]
        if key:
            return key
    except Exception:
        pass  # no secrets configured (e.g. running locally)
    # Local: read from .env / environment variable
    return os.environ.get("GEMINI_API_KEY")

def get_db_schema() -> str:
    """Inspects the local SQLite database and returns the schema for LLM context injection."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    schema_description = []
    for table_name in tables:
        t_name = table_name[0]
        cursor.execute(f"PRAGMA table_info({t_name});")
        columns = cursor.fetchall()
        col_list = [f"{col[1]} ({col[2]})" for col in columns]
        schema_description.append(f"Table: {t_name}\nColumns: {', '.join(col_list)}")
        
    conn.close()
    return "\n\n".join(schema_description)


def generate_sql_from_prompt(user_prompt: str) -> str:
    """
    Takes natural language input, combines it with database schema context, 
    and uses Google Gemini REST API to generate a secure SQL query.
    """
    api_key = _get_api_key()
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is not set.")

    api_key = api_key.strip()
    schema = get_db_schema()
    
    system_instruction = (
        "You are an expert enterprise data analytics assistant. Your job is to convert "
        "natural language questions into clean, executable SQLite SELECT queries based on the provided database schema.\n"
        "Rules:\n"
        "1. Return ONLY the raw SQL query string. Do not include markdown code block backticks (like ```sql) or explanatory text.\n"
        "2. Only generate read-only SELECT statements.\n"
        "3. Use correct table and column names from the schema."
    )

    prompt = f"Database Schema:\n{schema}\n\nUser Question: {user_prompt}"

    # Clean, explicit URL string (no trailing commas or brackets)
    #url = "[https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent](https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent)"
    # url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent"


    payload = {
        "contents": [
            {
                "parts": [
                    {"text": f"{system_instruction}\n\n{prompt}"}
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.0
        }
    }
    
    headers = {"Content-Type": "application/json"}
    params = {"key": api_key}

    RETRYABLE = {429, 500, 503, 504}

    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent"

    response = None
    for attempt in range(3):
        response = requests.post(url, params=params, headers=headers, json=payload, timeout=30)
        if response.status_code == 200:
            break
        if response.status_code in RETRYABLE:
            time.sleep(2 ** attempt)   # waits 1s, 2s, 4s
            continue
        break  # non-retryable error (bad key, bad request): stop trying

    if response.status_code != 200:
        raise Exception(f"Gemini API Error (Status {response.status_code}): {response.text}")

    result_json = response.json()
    try:
        sql_query = result_json["candidates"][0]["content"]["parts"][0]["text"].strip()
    except (KeyError, IndexError) as e:
        raise Exception(f"Unexpected response structure from Gemini API: {result_json}") from e

    # Clean output formatting
    if sql_query.startswith("```sql"):
        sql_query = sql_query[6:]
    if sql_query.startswith("```"):
        sql_query = sql_query[3:]
    if sql_query.endswith("```"):
        sql_query = sql_query[:-3]
        
    return sql_query.strip()