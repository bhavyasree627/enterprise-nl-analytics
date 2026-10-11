import sqlite3
import pandas as pd
import yfinance as yf

DB_NAME = "enterprise_stocks.db"

def init_db():
    """Fetches real historical stock data via yfinance and populates SQLite database."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # 1. Create Stocks Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stocks (
            ticker TEXT PRIMARY KEY,
            company_name TEXT,
            sector TEXT
        )
    """)

    # 2. Create Stock Prices Table (Time-series analytics focus)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stock_prices (
            price_id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT,
            date TEXT,
            open_price REAL,
            high_price REAL,
            low_price REAL,
            close_price REAL,
            volume INTEGER,
            FOREIGN KEY (ticker) REFERENCES stocks(ticker)
        )
    """)
    conn.commit()

    # Check if data already exists
    cursor.execute("SELECT COUNT(*) FROM stock_prices")
    if cursor.fetchone()[0] == 0:
        print("📥 Downloading live stock data from Yahoo Finance...")
        
        tickers_data = [
            ("AAPL", "Apple Inc.", "Technology"),
            ("MSFT", "Microsoft Corp.", "Technology"),
            ("TSLA", "Tesla Inc.", "Automotive"),
            ("GOOGL", "Alphabet Inc.", "Technology"),
            ("AMZN", "Amazon.com Inc.", "Consumer Cyclical")
        ]

        for ticker, name, sector in tickers_data:
            cursor.execute("INSERT OR IGNORE INTO stocks (ticker, company_name, sector) VALUES (?, ?, ?)", (ticker, name, sector))
            
            # Fetch past 1 year of daily historical data using yfinance
            stock_df = yf.Ticker(ticker).history(period="1y")
            stock_df = stock_df.reset_index()
            
            for _, row in stock_df.iterrows():
                date_str = str(row['Date']).split()[0] # Format date YYYY-MM-DD
                cursor.execute("""
                    INSERT INTO stock_prices (ticker, date, open_price, high_price, low_price, close_price, volume)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    ticker, 
                    date_str, 
                    float(row['Open']), 
                    float(row['High']), 
                    float(row['Low']), 
                    float(row['Close']), 
                    int(row['Volume'])
                ))
        
        conn.commit()
        print("Database successfully populated with real market data!")

    conn.close()

def run_query(sql_query: str) -> pd.DataFrame:
    """Executes a SQL query safely and returns a Pandas DataFrame."""
    conn = sqlite3.connect(DB_NAME)
    try:
        df = pd.read_sql_query(sql_query, conn)
        return df
    finally:
        conn.close()

if __name__ == "__main__":
    init_db()