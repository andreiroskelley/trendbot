"""
tests/test_agent.py
"""

import pytest
from src.agent.news_judge import NewsJudgeAgent

# ==========================================
# Mock LLM Implementation
# ==========================================
class MockLLMClient:
    def __init__(self, return_material_risk: bool):
        self.return_material_risk = return_material_risk

    def analyze_news(self, ticker: str, headlines: list) -> bool:
        # We just return whatever the test told us to return
        return self.return_material_risk

@pytest.fixture
def news_config():
    return {
        'lookback_hours': 24,
        'veto_on_material': True,
        'trusted_sources': ['Reuters', 'Bloomberg', 'SEC']
    }

# ==========================================
# Tests
# ==========================================

def test_no_news_does_not_veto(news_config):
    """If there's no news, we definitely don't veto the trade."""
    # We don't even need a real LLM here because it shouldn't be called
    agent = NewsJudgeAgent(llm_client=None, config=news_config)
    
    should_veto = agent.should_veto_trade("AAPL", [])
    assert should_veto is False

def test_material_risk_vetoes_trade(news_config):
    """If the LLM says the news is real (e.g., SEC investigation), we veto."""
    # Simulate the LLM saying "Yes, this is material risk"
    mock_llm = MockLLMClient(return_material_risk=True)
    agent = NewsJudgeAgent(llm_client=mock_llm, config=news_config)

    headlines = ["Apple CEO steps down amid accounting scandal"]
    
    should_veto = agent.should_veto_trade("AAPL", headlines)
    assert should_veto is True

def test_noise_does_not_veto_trade(news_config):
    """If the LLM says the news is fake (e.g., a fake tweet), we do not veto."""
    # Simulate the LLM saying "No, this is just noise"
    mock_llm = MockLLMClient(return_material_risk=False)
    agent = NewsJudgeAgent(llm_client=mock_llm, config=news_config)

    headlines = ["Baseless rumor on Twitter claims Apple is going bankrupt"]
    
    should_veto = agent.should_veto_trade("AAPL", headlines)
    assert should_veto is False