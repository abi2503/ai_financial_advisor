"""
Alex Trading Floor - All Pydantic Models
Single source of truth for all data structures
"""
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum
from datetime import datetime


class TradeAction(str, Enum):
    BUY  = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    TRIM = "TRIM"


class TradingMode(str, Enum):
    AGGRESSIVE = "aggressive"
    NEUTRAL    = "neutral"
    SAFE       = "safe"


class AgentVote(BaseModel):
    agent:             str
    action:            TradeAction
    confidence:        float = Field(ge=0, le=100)
    opening_statement: str   = ""
    detailed_reasoning: str  = ""
    key_evidence:      list[str] = []
    counter_argument:  str   = ""
    target:            Optional[float] = None
    stop_loss:         Optional[float] = None
    position_suggestion: str = ""
    key_risks:         list[str] = []
    data_used:         list[str] = []


class DebateResult(BaseModel):
    ticker:        str
    final_action:  TradeAction
    confidence:    float
    shares:        int
    price:         float
    total_value:   float
    target_price:  Optional[float] = None
    stop_loss:     Optional[float] = None
    rationale:     str
    votes:         list[AgentVote]
    mode:          str
    llm_used:      str
    debate_time_s: float = 0
    timestamp:     str   = ""
    data_quality:  float = 0.0
    sources_used:  list[str] = []


class AgentPerformance(BaseModel):
    agent_name:   str
    total_calls:  int   = 0
    correct:      int   = 0
    win_rate:     float = 0.0
    avg_pnl:      float = 0.0
    best_sector:  str   = ""
    worst_sector: str   = ""
    model_id:     str   = ""
    vote_weight:  float = 1.0


class TradingConfig(BaseModel):
    mode:             TradingMode = TradingMode.NEUTRAL
    autonomous:       bool        = True
    max_position_pct: float       = 25.0
    stop_loss_pct:    float       = 8.0
    max_daily_trades: int         = 10
    models:           dict        = {}
    enabled:          bool        = True
