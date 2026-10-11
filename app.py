import streamlit as st
import pandas as pd
import plotly.express as px
from database import init_db, run_query
from nlp_engine import generate_sql_from_prompt
from security import validate_read_only_sql, SecurityError

# Page setup
st.set_page_config(page_title="Enterprise NL Analytics Engine", page_icon="📈", layout="wide")

# Initialize database on app load
@st.cache_resource
def setup():
    init_db()

setup()

st.title("📈 Enterprise Natural Language Analytics Engine")
st.markdown("Query your financial and stock market database using plain English. Security guardrails and automated visualizations active.")

# Sidebar documentation
with st.sidebar:
    st.header("About the Engine")
    st.markdown("""
    * **NLP Core:** Google Gemini API
    * **Security Layer:** AST Parsing (`sqlparse`)
    * **Database:** SQLite + Live Yahoo Finance Data
    * **Visualization:** Dynamic Plotly Mapper
    """)
    st.info("Try typing prompts like:\n- *Show closing prices for AAPL in 2026*\n- *Compare average trading volumes by tech company*\n- *What was the highest price for MSFT?*")

# Main Input Bar
user_prompt = st.text_input("Enter your analytics question:", placeholder="e.g., Show me the top 5 highest closing prices for Tesla")

if user_prompt:
    with st.spinner("Processing natural language query..."):
        try:
            # 1. Generate SQL via NLP Engine
            raw_sql = generate_sql_from_prompt(user_prompt)
            
            # 2. Enforce Enterprise Security Guardrails (AST Verification)
            safe_sql = validate_read_only_sql(raw_sql)
            
            with st.expander("🛡️ Verified Secure SQL Query"):
                st.code(safe_sql, language="sql")
                
            # 3. Execute Query Safely Against Database
            df = run_query(safe_sql)
            
            if df.empty:
                st.warning("Query executed successfully, but returned zero results.")
            else:
                # 4. Display Tabular Data Results
                st.subheader("📊 Query Result Dataframe")
                st.dataframe(df, use_container_width=True)
                
                # 5. Automated Dynamic Visualization Mapping (No manual filters needed)
                st.subheader("📉 Automated Visual Analytics")
                
                cols = df.columns.tolist()
                if len(cols) >= 2:
                    x_col = cols[0]
                    y_col = cols[1]
                    
                    # Choose chart style dynamically based on column names/data types
                    if "date" in x_col.lower() or "time" in x_col.lower() or "date" in str(df[x_col].dtype).lower():
                        fig = px.line(df, x=x_col, y=y_col, markers=True, title=f"Time-Series Analysis: {y_col} over {x_col}")
                    else:
                        fig = px.bar(df, x=x_col, y=y_col, text_auto=True, title=f"Distribution Analysis: {y_col} by {x_col}")
                        
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("Single scalar metric result detected.")
                    st.metric(label=cols[0], value=str(df.iloc[0, 0]))
                    
        except SecurityError as se:
            st.error(f"🚨 Security Block: {se}")
        except Exception as e:
            st.error(f"An error occurred during execution: {e}")