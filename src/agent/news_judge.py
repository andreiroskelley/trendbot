"""
src/agent/news_judge.py
Real News Judge using local Ollama (DeepSeek).
"""

import os
import logging
import json
from typing import List, Protocol
from ollama import chat
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# 1. The Interface (unchanged)
class LLMClient(Protocol):
    def analyze_news(self, ticker: str, headlines: List[str]) -> bool:
        ...

# 2. The Real Ollama Implementation
class OllamaClient:
    def __init__(self):
        self.model = os.getenv("OLLAMA_MODEL", "deepseek-r1:8b")

    def analyze_news(self, ticker: str, headlines: List[str]) -> bool:
        if not headlines:
            return False

        # Format the headlines for the prompt
        news_text = "\n".join([f"- {h}" for h in headlines])
        
        prompt = f"""You are a financial risk analyst. Evaluate these recent headlines for {ticker}:
{news_text}

Determine if the negative price movement is likely due to:
A) MATERIAL RISK: Verifiable, serious events (earnings miss, SEC investigation, CEO resignation, bankruptcy).
B) NOISE: Unverified rumors, fake tweets, satire, or baseless claims from non-authoritative sources.

Answer ONLY with a JSON object in this format: {{"veto": true}} if it is MATERIAL RISK, or {{"veto": false}} if it is NOISE."""

        try:
            # Ask Ollama to enforce JSON format
            response = chat(
                model=self.model,
                messages=[{'role': 'user', 'content': prompt}],
                format='json',
                options={'temperature': 0},
                host='http://192.168.0.3:11434' # <--- Replace with YOUR Mac's IP
            )
            
            # Parse the JSON response
            result = json.loads(response.message.content)
            is_material_risk = result.get('veto', False)
            
            logger.info(f"[Ollama] Analysis for {ticker}: Veto={is_material_risk}")
            return is_material_risk

        except Exception as e:
            logger.error(f"Ollama analysis failed: {e}")
            # If the AI fails, default to vetoing to protect capital
            return True 

# 3. The Agent (unchanged)
class NewsJudgeAgent:
    def __init__(self, llm_client: LLMClient, config: dict):
        self.llm = llm_client
        self.config = config

    def should_veto_trade(self, ticker: str, headlines: List[str]) -> bool:
        if not headlines:
            logger.info(f"[{ticker}] No news found. Safe to trade.")
            return False

        logger.info(f"[{ticker}] Analyzing {len(headlines)} headlines via local AI...")
        return self.llm.analyze_news(ticker, headlines)