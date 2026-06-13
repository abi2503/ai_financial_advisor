"""
Marcus Chen - Senior Growth Analyst
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.base_agent import BaseAgent
from models import AgentVote, TradeAction
from prompts import marcus as prompt_module


class MarcusAgent(BaseAgent):
    name = "Marcus Chen"

    def __init__(self, model_id: str = "us.amazon.nova-pro-v1:0"):
        self.model_id = model_id

    def vote(self, market_data, holding: dict, mode: str, data_ctx: str) -> AgentVote:
        ticker = market_data.ticker
        prompt = prompt_module.build_prompt(data_ctx, mode, ticker)
        data   = self.invoke(prompt)
        if not data:
            data = self.default_vote(self.name)
        try:
            return AgentVote(
                agent               = "marcus",
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
            logging.getLogger(__name__).error(f"Marcus Chen vote error: {e}")
            return AgentVote(
                agent="marcus", action=TradeAction.HOLD,
                confidence=50, detailed_reasoning=str(e)
            )
