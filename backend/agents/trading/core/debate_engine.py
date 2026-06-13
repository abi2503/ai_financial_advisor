"""
Alex Trading Floor - Core Debate Engine
Orchestrates 6-agent debate using clean architecture
"""
import os, json, boto3, logging, time
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

logger      = logging.getLogger(__name__)
UTC         = timezone.utc
REGION      = os.environ.get("AWS_REGION_NAME", "us-east-1")
CLUSTER_ARN = os.environ.get("DB_CLUSTER_ARN", "")
SECRET_ARN  = os.environ.get("DB_SECRET_ARN", "")
DB_NAME     = os.environ.get("DB_NAME", "alex_db")
bedrock     = boto3.client("bedrock-runtime", region_name=REGION)
rds         = boto3.client("rds-data",        region_name=REGION)
ssm         = boto3.client("ssm",             region_name=REGION)

# Import models
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models import AgentVote, DebateResult, TradeAction

# Mode weights for voting
MODE_WEIGHTS = {
    "aggressive": {"marcus": 2.0, "zara": 1.5, "reid": 1.0, "victoria": 0.5, "elena": 0.5},
    "neutral":    {"marcus": 1.0, "zara": 1.0, "reid": 1.0, "victoria": 1.0, "elena": 1.0},
    "safe":       {"marcus": 0.5, "zara": 0.5, "reid": 1.0, "victoria": 1.5, "elena": 2.0},
}
ACTION_VALUES = {"BUY": 1.0, "TRIM": 0.2, "HOLD": 0.0, "SELL": -1.0}


def get_ssm(key, default=""):
    try:
        return ssm.get_parameter(Name=f"/alex/trading/{key}")["Parameter"]["Value"]
    except:
        return default


def build_data_context(market_data, holding: dict) -> str:
    """Build rich context string from MarketData for agent prompts"""
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
            "", "FUNDAMENTALS:",
            f"  P/E:            {fund.pe_ratio or 'N/A'}",
            f"  Forward P/E:    {fund.forward_pe or 'N/A'}",
            f"  Revenue Growth: {(fund.revenue_growth or 0)*100:.1f}%",
            f"  EPS Growth:     {(fund.earnings_growth or 0)*100:.1f}%",
            f"  Profit Margin:  {(fund.profit_margin or 0)*100:.1f}%",
            f"  Market Cap:     ${(fund.market_cap or 0)/1e9:.1f}B",
        ]
    if tech:
        lines += [
            "", "TECHNICALS:",
            f"  RSI (14):       {tech.rsi or 'N/A'}",
            f"  Signal:         {tech.technical_signal or 'N/A'}",
            f"  Above 50MA:     {tech.above_50ma}",
            f"  Above 200MA:    {tech.above_200ma}",
            f"  Options Flow:   {tech.options_sentiment or 'N/A'}",
        ]
    if sent:
        lines += [
            "", "SENTIMENT:",
            f"  Analyst Rating: {sent.analyst_rating or 'N/A'}",
            f"  Price Target:   ${sent.analyst_target or 'N/A'}",
            f"  Fear & Greed:   {sent.fear_greed_score or 'N/A'}/100",
            f"  Short Interest: {sent.short_interest or 'N/A'}%",
        ]
    if news:
        lines += ["", "RECENT NEWS:"]
        for n in news:
            lines.append(f"  - {n.title} ({n.source})")

    pnl = (market_data.price - holding.get("purchase_price", 0)) * holding.get("shares", 0)
    lines += [
        "", "YOUR POSITION:",
        f"  Shares:   {holding.get('shares', 0)}",
        f"  Avg Cost: ${holding.get('purchase_price', 0):.2f}",
        f"  Value:    ${holding.get('total_value', 0):.2f}",
        f"  P&L:      ${pnl:.2f}",
        "",
        f"Data Sources: {', '.join(market_data.sources_used)}",
        f"Data Quality: {market_data.data_quality:.0%}",
    ]
    return "\n".join(lines)


def calculate_decision(votes: list, mode: str) -> tuple:
    weights = MODE_WEIGHTS.get(mode, MODE_WEIGHTS["neutral"])
    total_w = total_s = 0
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


def calculate_shares(action, price, confidence, holding, config) -> int:
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


def run_executor(ticker, votes, action, confidence, market_data, mode, model_id) -> str:
    from prompts.executor import build_prompt
    votes_str = "\n".join([
        f"  {v.agent.upper()} ({v.action.value} {v.confidence:.0f}%): {v.opening_statement} — {v.detailed_reasoning[:100]}"
        for v in votes
    ])
    prompt = build_prompt(votes_str, action.value, confidence, ticker, market_data.price, mode)
    try:
        response = bedrock.invoke_model(
            modelId=model_id, contentType="application/json", accept="application/json",
            body=json.dumps({
                "messages": [{"role": "user", "content": [{"text": prompt}]}],
                "inferenceConfig": {"maxTokens": 250, "temperature": 0.3}
            })
        )
        result = json.loads(response["body"].read())
        return result["output"]["message"]["content"][0]["text"].strip()
    except Exception as e:
        logger.error(f"Executor error: {e}")
        return f"{action.value} {ticker} at ${market_data.price:.2f} — {confidence:.0f}% confidence."


def sttrade(result: DebateResult, sim_id: str, user_id: str):
    try:
        rds.execute_statement(
            resourceArn=CLUSTER_ARN, secretArn=SECRET_ARN, database=DB_NAME,
            sql="""INSERT INTO simulated_trades
                     (simulation_id, user_id, ticker, action, shares,
                      price, total_value, target_price, stop_loss,
                      rationale, agent_votes, agent_debate, confidence, mode, llm_used)
                   SELECT :sim, id, :ticker, :action, :shares,
                          :price, :value, :target, :stop,
                          :rationale, :votes::jsonb, :debate::jsonb,
                          :conf, :mode, :llm
                   FROM users WHERE clerk_id = :uid""",
            parameters=[
                {"name": "sim",      "value": {"stringValue": sim_id}},
                {"name": "ticker",   "value": {"stringValue": result.ticker}},
                {"name": "action",   "value": {"stringValue": result.final_action.value}},
                {"name": "shares",   "value": {"longValue":   result.shares}},
                {"name": "price",    "value": {"doubleValue": result.price}},
                {"name": "value",    "value": {"doubleValue": result.total_value}},
                {"name": "target",   "value": {"doubleValue": result.target_price or 0}},
                {"name": "stop",     "value": {"doubleValue": result.stop_loss or 0}},
                {"name": "rationale","value": {"stringValue": result.rationale}},
                {"name": "votes",    "value": {"stringValue": json.dumps([v.model_dump() for v in result.votes])}},
                {"name": "debate",   "value": {"stringValue": json.dumps([{
                    "agent": v.agent, "action": v.action.value,
                    "confidence": v.confidence,
                    "opening": v.opening_statement,
                    "reasoning": v.detailed_reasoning,
                    "evidence": v.key_evidence,
                    "counter": v.counter_argument,
                    "risks": v.key_risks
                } for v in result.votes])}},
                {"name": "conf",     "value": {"doubleValue": result.confidence}},
                {"name": "mode",     "value": {"stringValue": result.mode}},
                {"name": "llm",      "value": {"stringValue": result.llm_used}},
                {"name": "uid",      "value": {"stringValue": user_id}},
            ]
        )
        print(f"Stored: {result.ticker} {result.final_action.value}")
    except Exception as e:
        logger.error(f"Store error: {e}")


def run_debate(ticker: str, holding: dict, sim_id: str,
               user_id: str, mode: str, config: dict) -> dict:
    start  = time.time()
    models = config.get("models", {})
    pro    = "us.amazon.nova-pro-v1:0"
    lite   = "us.amazon.nova-lite-v1:0"

    # Import agents
    from agents.marcus   import MarcusAgent
    from agents.victoria import VictoriaAgent
    from agents.zara     import ZaraAgent
    from agents.reid     import ReidAgent
    from agents.elena    import ElenaAgent
    from tools.market_data import get_market_data

    print(f"Debate: {ticker}")
    market_data = get_market_data(ticker)
    print(f"  Price: ${market_data.price:.2f} | Quality: {market_data.data_quality:.0%}")

    data_ctx = build_data_context(market_data, holding)

    # Instantiate agents with configurable models
    agent_list = [
        MarcusAgent(models.get("marcus",   pro)),
        VictoriaAgent(models.get("victoria", pro)),
        ZaraAgent(models.get("zara",       pro)),
        ReidAgent(models.get("reid",       pro)),
        ElenaAgent(models.get("elena",     lite)),
    ]

    # Run all 5 agents in parallel
    votes = []
    with ThreadPoolExecutor(max_workers=5) as ex:
        futures = {ex.submit(a.vote, market_data, holding, mode, data_ctx): a.name
                   for a in agent_list}
        for future in as_completed(futures):
            try:
                vote = future.result(timeout=45)
                votes.append(vote)
                print(f"  {vote.agent}: {vote.action.value} ({vote.confidence:.0f}%) — {vote.opening_statement[:60]}")
            except Exception as e:
                print(f"  Agent error: {e}")

    if not votes:
        return {"ticker": ticker, "action": "HOLD", "error": "No votes"}

    action, confidence = calculate_decision(votes, mode)
    rationale = run_executor(ticker, votes, action, confidence,
                            market_data, mode, models.get("executor", pro))
    shares = calculate_shares(action, market_data.price, confidence, holding, config)

    result = DebateResult(
        ticker        = ticker,
        final_action  = action,
        confidence    = confidence,
        shares        = shares,
        price         = market_data.price,
        total_value   = shares * market_data.price,
        target_price  = next((v.target for v in votes if v.target), None),
        stop_loss     = next((v.stop_loss for v in votes if v.stop_loss), None),
        rationale     = rationale,
        votes         = votes,
        de          = mode,
        llm_used      = models.get("marcus", pro),
        debate_time_s = round(time.time() - start, 1),
        timestamp     = datetime.now(UTC).isoformat(),
        data_quality  = market_data.data_quality,
        sources_used  = market_data.sources_used,
    )

    store_trade(result, sim_id, user_id)
    return result.model_dump()
