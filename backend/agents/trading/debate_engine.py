"""
Alex Trading Floor - Debate Engine
6 agents debate each ticker using rich market data.
Uses Pydantic for all structured outputs.
"""
import os
import json
import boto3
import logging
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, as_completed

from market_data import get_market_data, MarketData

logger  = logging.getLogger(__name__)
UTC     = timezone.utc
REGION  = os.environ.get("AWS_REGION_NAME", "us-east-1")
bedrock = boto3.client("bedrock-runtime", region_name=REGION)
rds     = boto3.client("rds-data",        region_name=REGION)

CLUSTER_ARN = os.environ.get("DB_CLUSTER_ARN", "")
SECRET_ARN  = os.environ.get("DB_SECRET_ARN", "")
DB_NAME     = os.environ.get("DB_NAME", "alex_db")


# ============================================
# Pydantic Models
# ============================================

class TradeAction(str, Enum):
    BUY  = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    TRIM = "TRIM"


class AgentVote(BaseModel):
    agent:      str
    action:     TradeAction
    confidence: float = Field(ge=0, le=100)
    rationale:  str
    target:     Optional[float] = None
    stop_loss:  Optional[float] = None
    key_risks:  list[str]       = []
    data_used:  list[str]       = []


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


# ============================================
# Mode Weights
# ============================================
MODE_WEIGHTS = {
    "aggressive": {"marcus": 2.0, "zara": 1.5, "reid": 1.0, "victoria": 0.5, "elena": 0.5},
    "neutral":    {"marcus": 1.0, "zara": 1.0, "reid": 1.0, "victoria": 1.0, "elena": 1.0},
    "safe":       {"marcus": 0.5, "zara": 0.5, "reid": 1.0, "victoria": 1.5, "elena": 2.0},
}

ACTION_VALUES = {"BUY": 1.0, "TRIM": 0.2, "HOLD": 0.0, "SELL": -1.0}


# ============================================
# Build rich prompt from MarketData
# ============================================
def build_data_context(market_data: MarketData, holding: dict) -> str:
    fund = market_data.fundamentals
    tech = market_data.technicals
    sent = market_data.sentiment
    news = market_data.news[:3]

    lines = [
        f"STOCK: {market_data.ticker}",
        f"Price:      ${market_data.price:.2f} ({market_data.change_pct:+.2f}% today)",
        f"Volume:     {market_data.volume:,}",
        f"52W Range:  ${market_data.week_52_low or 0:.2f} - ${market_data.week_52_high or 0:.2f}",
    ]

    if fund:
        lines += [
            "",
            "FUNDAMENTALS:",
            f"  P/E:            {fund.pe_ratio or 'N/A'}",
            f"  Forward P/E:    {fund.forward_pe or 'N/A'}",
            f"  Revenue Growth: {(fund.revenue_growth or 0)*100:.1f}%",
            f"  EPS Growth:     {(fund.earnings_growth or 0)*100:.1f}%",
            f"  Profit Margin:  {(fund.profit_margin or 0)*100:.1f}%",
            f"  Debt/Equity:    {fund.debt_to_equity or 'N/A'}",
            f"  Market Cap:     ${(fund.market_cap or 0)/1e9:.1f}B",
        ]

    if tech:
        lines += [
            "",
            "TECHNICALS:",
            f"  RSI (14):       {tech.rsi or 'N/A'}",
            f"  Signal:         {tech.technical_signal or 'N/A'}",
            f"  Above 50MA:     {tech.above_50ma}",
            f"  Above 200MA:    {tech.above_200ma}",
            f"  Options Flow:   {tech.options_sentiment or 'N/A'}",
            f"  Put/Call Ratio: {tech.put_call_ratio or 'N/A'}",
        ]

    if sent:
        lines += [
            "",
            "SENTIMENT:",
            f"  Analyst Rating: {sent.analyst_rating or 'N/A'}",
            f"  Price Target:   ${sent.analyst_target or 'N/A'}",
            f"  # Analysts:     {sent.analyst_count or 'N/A'}",
            f"  Fear & Greed:   {sent.fear_greed_score or 'N/A'}/100",
            f"  Short Interest: {sent.short_interest or 'N/A'}%",
            f"  Insider:        {sent.insider_sentiment or 'N/A'}",
        ]

    if news:
        lines += ["", "RECENT NEWS:"]
        for n in news:
            lines.append(f"  - {n.title} ({n.source})")

    pnl = (market_data.price - holding.get("purchase_price", 0)) * holding.get("shares", 0)
    lines += [
        "",
        "YOUR POSITION:",
        f"  Shares:   {holding.get('shares', 0)}",
        f"  Avg Cost: ${holding.get('purchase_price', 0):.2f}",
        f"  Value:    ${holding.get('total_value', 0):.2f}",
        f"  P&L:      ${pnl:.2f}",
        "",
        f"Data Sources: {', '.join(market_data.sources_used)}",
        f"Data Quality: {market_data.data_quality:.0%}",
    ]
    return "\n".join(lines)


# ============================================
# Generic Agent Runner
# ============================================
def run_agent(name: str, personality: str, data_focus: str,
              market_data: MarketData, holding: dict,
              mode: str, model_id: str) -> AgentVote:
    import re
    data_ctx = build_data_context(market_data, holding)

    prompt = f"""You are {name}, a specialist trading analyst on Alex Trading Floor.

PERSONALITY: {personality}

YOUR FOCUS: {data_focus}

{data_ctx}

TRADING MODE: {mode.upper()}
  aggressive = higher risk tolerance, larger positions
  neutral    = balanced approach
  safe       = capital preservation first

Analyze the data through your specific lens and give your recommendation.

Respond ONLY with valid JSON - no other text:
{{
  "action": "BUY or SELL or HOLD or TRIM",
  "confidence": 75,
  "rationale": "2-3 sentences using specific data points from above",
  "target": 210.00,
  "stop_loss": 185.00,
  "key_risks": ["specific risk 1", "specific risk 2"],
  "data_used": ["RSI value", "analyst rating", "etc"]
}}"""

    try:
        response = bedrock.invoke_model(
            modelId=model_id,
            contentType="application/json",
            accept="application/json",
            body=json.dumps({
                "messages": [{"role": "user", "content": [{"text": prompt}]}],
                "inferenceConfig": {"maxTokens": 300, "temperature": 0.4}
            })
        )
        result = json.loads(response["body"].read())
        text   = result["output"]["message"]["content"][0]["text"]

        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            data = json.loads(match.group())
            return AgentVote(
                agent      = name.lower(),
                action     = TradeAction(data.get("action", "HOLD")),
                confidence = float(data.get("confidence", 50)),
                rationale  = data.get("rationale", ""),
                target     = data.get("target"),
                stop_loss  = data.get("stop_loss"),
                key_risks  = data.get("key_risks", []),
                data_used  = data.get("data_used", [])
            )
    except Exception as e:
        logger.error(f"{name} error: {e}")

    return AgentVote(
        agent=name.lower(), action=TradeAction.HOLD,
        confidence=50, rationale=f"{name} could not complete analysis"
    )


# ============================================
# 5 Specialist Agents
# ============================================
def run_marcus(md, holding, mode, model_id) -> AgentVote:
    return run_agent(
        "Marcus", 
        "Optimistic bull. Always finds reasons to buy. Focus on growth and momentum.",
        "Revenue growth, earnings beats, analyst upgrades, insider buying, momentum",
        md, holding, mode, model_id
    )

def run_victoria(md, holding, mode, model_id) -> AgentVote:
    return run_agent(
        "Victoria",
        "Skeptical bear. Always finds reasons to sell. Focus on downside risks.",
        "Overvaluation, short interest, earnings misses, sector headwinds, macro risks",
        md, holding, mode, model_id
    )

def run_zara(md, holding, mode, model_id) -> AgentVote:
    return run_agent(
        "Zara",
        "Pure quant. Only data and signals. No opinions.",
        "RSI, MACD, moving averages, options flow, put/call ratio, volume trends",
        md, holding, mode, model_id
    )

def run_reid(md, holding, mode, model_id) -> AgentVote:
    return run_agent(
        "Reid",
        "Macro economist. Big picture thinker. Sector rotation and cycles.",
        "Interest rates, sector positioning, macro environment, geopolitical risks",
        md, holding, mode, model_id
    )

def run_elena(md, holding, mode, model_id) -> AgentVote:
    return run_agent(
        "Elena",
        "Risk manager. Portfolio protector. Capital preservation first.",
        "Position sizing, concentration risk, stop loss levels, portfolio correlation",
        md, holding, mode, model_id
    )


# ============================================
# Weighted Vote Calculator
# ============================================
def calculate_decision(votes: list[AgentVote], mode: str) -> tuple[TradeAction, float]:
    weights = MODE_WEIGHTS.get(mode, MODE_WEIGHTS["neutral"])
    total_w = 0
    total_s = 0

    for vote in votes:
        w = weights.get(vote.agent.lower(), 1.0)
        s = ACTION_VALUES.get(vote.action.value, 0) * w * (vote.confidence / 100)
        total_s += s
        total_w += w

    avg = total_s / max(total_w, 1)

    if avg > 0.3:
        action = TradeAction.BUY
    elif avg > 0.05:
        action = TradeAction.HOLD
    elif avg > -0.3:
        action = TradeAction.TRIM
    else:
        action = TradeAction.SELL

    confidence = min(max(abs(avg) * 100, 10), 95)
    return action, round(confidence, 1)


# ============================================
# Position Size Calculator
# ============================================
def calculate_shares(action: TradeAction, price: float,
                     confidence: float, holding: dict, config: dict) -> int:
    if action == TradeAction.HOLD or price <= 0:
        return 0
    current = holding.get("shares", 0)
    value   = holding.get("total_value", 10000)

    if action == TradeAction.BUY:
        budget = value * 0.05 * (confidence / 100)
        return max(1, int(budget / price))
    elif action == TradeAction.SELL:
        return current
    elif action == TradeAction.TRIM:
        return max(1, int(current * 0.25))
    return 0


# ============================================
# Executor Rationale
# ============================================
def run_executor(ticker: str, votes: list[AgentVote],
                 action: TradeAction, confidence: float,
                 market_data: MarketData, mode: str, model_id: str) -> str:
    votes_str = "\n".join([
        f"  {v.agent.upper()}: {v.action.value} ({v.confidence:.0f}%) - {v.rationale}"
        for v in votes
    ])
    prompt = f"""You are Alex, head trader. Synthesize this debate for {ticker} at ${market_data.price:.2f}:

{votes_str}

Decision: {action.value} (confidence: {confidence:.0f}%, mode: {mode})

Write 2-3 sentences explaining:
1. Why this decision was made
2. Which agents drove the decision  
3. Key risk to watch

Be specific. Use ticker name and price. Under 80 words."""

    try:
        r = bedrock.invoke_model(
            modelId=model_id, contentType="application/json", accept="application/json",
            body=json.dumps({
                "messages": [{"role": "user", "content": [{"text": prompt}]}],
                "inferenceConfig": {"maxTokens": 150, "temperature": 0.3}
            })
        )
        result = json.loads(r["body"].read())
        return result["output"]["message"]["content"][0]["text"].strip()
    except Exception as e:
        logger.error(f"Executor error: {e}")
        return f"{action.value} {ticker} at ${market_data.price:.2f} — {confidence:.0f}% confidence."


# ============================================
# Store Trade to Aurora
# ============================================
def store_trade(result: DebateResult,im_id: str, user_id: str):
    try:
        rds.execute_statement(
            resourceArn=CLUSTER_ARN, secretArn=SECRET_ARN, database=DB_NAME,
            sql="""INSERT INTO simulated_trades
                     (simulation_id, user_id, ticker, action, shares,
                      price, total_value, target_price, stop_loss,
                      rationale, agent_votes, agent_debate, confidence, mode, llm_used)
                   SELECT :sim, u.id, :ticker, :action, :shares,
                          :price, :value, :target, :stop,
                          :rationale, :votes::jsonb, :debate::jsonb,
                          :conf, :mode, :llm
                   FROM users WHERE clerk_id = :uid""",
            parameters=[
                {"name": "sim",       "value": {"stringValue": sim_id}},
                {"name": "ticker",    "value": {"stringValue": result.ticker}},
                {"name": "action",    "value": {"stringValue": result.final_action.value}},
                {"name": "shares",    "value": {"longValue":   result.shares}},
                {"name": "price",     "value": {"doubleValue": result.price}},
                {"name": "value",     "value": {"doubleValue": result.total_value}},
                {"name": "target",    "value": {"doubleValue": result.target_price or 0}},
                {"name": "stop",      "value": {"doubleValue": result.stop_loss or 0}},
                {"name": "rationale", "value": {"stringValue": result.rationale}},
                {"name": "votes",     "value": {"stringValue": json.dumps([v.model_dump() for v in result.votes])}},
                {"name": "debate",    "value": {"stringValue": json.dumps([{"agent": v.agent, "action": v.action.value, "confidence": v.confidence, "rationale": v.rationale} for v in result.votes])}},
                {"name": "conf",      "value": {"doubleValue": result.confidence}},
                {"name": "mode",      "value": {"stringValue": result.mode}},
                {"name": "llm",       "value": {"stringValue": result.llm_used}},
                {"name": "uid",       "value": {"stringValue": user_id}},
            ]
        )
        print(f"Stored: {result.ticker} {result.final_action.value}")
    except Exception as e:
        logger.error(f"Store trade error: {e}")


# ============================================
# Main Debate Runner
# ============================================
def run_debate(ticker: str, holding: dict, sim_id: str,
               user_id: str, mode: str, config: dict) -> dict:
    import time
    start  = time.time()
    models = config.get("models", {})
    lite   = "us.amazon.nova-lite-v1:0"
    pro    = "us.amazon.nova-pro-v1:0"

    print(f"Debate: {ticker}")

    # Get rich market data from all enabled providers
    market_data = get_market_data(ticker)
    print(f"  Price: ${market_data.price:.2f} | Quality: {market_data.data_quality:.0%} | Sources: {market_data.sources_used}")

    # Run 5 agents in parallel
    agent_fns = [
        (run_marcus,   models.get("marcus",   pro)),
        (run_victoria, models.get("victoria", pro)),
        (run_zara,     models.get("zara",     pro)),
        (run_reid,     models.get("reid",     pro)),
        (run_elena,    models.get("elena",    lite)),
    ]

    votes = []
    with ThreadPoolExecutor(max_workers=5) as ex:
        futures = {ex.submit(fn, market_data, holding, mode, mid): fn.__name__
                   for fn, mid in agent_fns}
        for future in as_completed(futures):
            try:
                vote = future.result(timeout=30)
                votes.append(vote)
                print(f"  {vote.agent}: {vote.action.value} ({vote.confidence:.0f}%)")
            except Exception as e:
                print(f"  Agent error: {e}")

    if not votes:
        return {"ticker": ticker, "action": "HOLD", "error": "No votes"}

    action, confidence = calculate_decision(votes, mode)
    rationale = run_executor(ticker, votes, action, confidence,
                             market_data, mode, models.get("executor", pro))
    shares = calculate_shares(action, market_data.price, confidence, holding, config)

    result = DebateResult(
        ticker       = ticker,
        final_action = action,
        confidence   = confidence,
        shares       = shares,
        price        = market_data.price,
        total_value  = shares * market_data.price,
        target_price = next((v.target for v in votes if v.target), None),
        stop_loss    = next((v.stop_loss for v in votes if v.stop_loss), None),
        rationale    = rationale,
        votes        = votes,
        mode         = mode,
        llm_used     = models.get("marcus", pro),
        debate_time_s = round(time.time() - start, 1),
        timestamp    = datetime.now(UTC).isoformat()
    )

    store_trade(result, sim_id, user_id)
    return result.model_dump()
