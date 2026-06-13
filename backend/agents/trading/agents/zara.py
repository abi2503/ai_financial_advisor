"""
Zara Patel - Quantitative Strategist
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.base_agent import BaseAgent
from models import AgentVote, TradeAction
from prompts import zara as prompt_module


class ZaraAgent(BaseAgent):
    name = "Zara Patel"

    def __init__(self, model_id: str = "us.amazon.nova-pro-v1:0", sim_id: str = ""):
        super().__init__(model_id, sim_id)

    def vote(self, market_data, holding: dict, mode: str, data_ctx: str) -> AgentVote:
        ticker = market_data.ticker
        prompt = prompt_module.build_prompt(data_ctx, mode, ticker)
        data, metrics = self.invoke(prompt, ticker=ticker)
        if not data:
            data = self.default_vote()
        try:
            return AgentVote(
                agent               = "zara",
                action              = TradeAction(data.get("action", "HOLD")),
                confidence          = float(data.get("confidence", 50)),
                opening_statement   = data.get("opening_statement", ""),
                detailed_reasoning  = data.get("detailed_reasoning", ""),
                key_evidence        = data.get("key_evidence", []),
                counter_argument    = data.get("counter_argument", ""),
                target              = data.get("target"),
                stop_loss           = data.get("stop_loss"),
                position_suggestion = data.get("position_suggestion", ""),
                key_risks           = data.get("key_risks", []),
                data_used           = data.get("data_used", [])
            )
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Zara Patel vote error: {e}")
            return AgentVote(
                agent="zara", action=TradeAction.HOLD,
                confidence=50, detailed_reasoning=str(e)
            )
