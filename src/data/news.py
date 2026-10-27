"""
src/data/news.py
Real news provider using Finnhub API.
"""

import os
import logging
import finnhub
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

FINNHUB_KEY = os.getenv("FINNHUB_API_KEY")
if not FINNHUB_KEY:
    logger.error("Finnhub API key not found in .env file!")

finnhub_client = finnhub.Client(api_key=FINNHUB_KEY)

def get_recent_news(ticker: str) -> list:
    """Fetches recent headlines for a ticker from Finnhub."""
    try:
        # Get news from the last 3 days
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d')
        
        news = finnhub_client.company_news(ticker, _from=start_date, to=end_date)
        
        # Extract just the headlines (limit to 5 to keep the prompt small)
        headlines = [item['headline'] for item in news[:5]]
        logger.info(f"[{ticker}] Fetched {len(headlines)} headlines.")
        return headlines
        
    except Exception as e:
        logger.error(f"Failed to fetch news for {ticker}: {e}")
        return []