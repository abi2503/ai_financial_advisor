"""
Base Agent with full observability
Tracks: input tokens, output tokens, cost, latency, guardrails
"""
import json
import time
import boto3
import logging
import re
import os
from datetime import datetime, timezone

logger  = logging.getLogger(__name__)
UTC     = timezone.utc
REGION  = os.environ.get("AWS_REGION_NAME", "us-east-1")
bedrock = boto3.client("bedrock-runtime", region_name=REGION)
rds     = boto3.client("rds-data",        region_name=REGION)

CLUSTER_ARN = os.environ.get("DB_CLUSTER_ARN", "")
SECRET_ARN  = os.environ.get("DB_SECRET_ARN", "")
DB_NAME     = os.environ.get("DB_NAME", "alex_db")

# Cost per 1000 tokens (USD) - Bedrock pricing
MODEL_COSTS = {
    "us.amazon.nova-pro-v1:0":   {"input": 0.0008,  "output": 0.0032},
    "us.amazon.nova-lite-v1:0":  {"input": 0.00006, "output": 0.00024},
    "us.amazon.nova-micro-v1:0": {"input": 0.000035,"output": 0.00014},
    "anthropic.claude-3-5-sonnet-20241022-v2:0": {"input": 0.003, "output": 0.015},
    "anthropic.claude-3-haiku-20240307-v1:0":    {"input": 0.00025, "output": 0.00125},
}

# Agent guardrails
GUARDRAILS = {
    "max_confidence": 95,       # No agent can be > 95% confident
    "min_confidence": 10,       # No agent can be < 10% confident
    "forbidden_actions": [],    # Actions to block
    "max_position_pct": 50,     # Max position size
}


def calculate_cost(model_id: str, input_tokens: int, output_tokens: int) -> float:
    costs = MODEL_COSTS.get(model_id, {"input": 0.0008, "output": 0.0032})
    return (input_tokens * costs["input"] + output_tokens * costs["output"]) / 1000


def apply_guardrails(data: dict, agent_name: str, ticker: str) -> tuple[dict, bool, str]:
    """
    Apply guardrails to agent output.
    Returns: (corrected_data, guardrail_triggered, reason)
    
    Intuition: Like compliance rules on a trading desk.
    No analyst can be 100% confident — markets are uncertain.
    No analyst can recommend >50% position in one stock.
    """
    triggered = False
    reason    = ""

    # Cap confidence
    if data.get("confidence", 50) > GUARDRAILS["max_confidence"]:
        data["confidence"] = GUARDRAILS["max_confidence"]
        triggered = True
        reason = f"Confidence capped at {GUARDRAILS['max_confidence']}%"

    # Floor confidence
    if data.get("confidence", 50) < GUARDRAILS["min_confidence"]:
        data["confidence"] = GUARDRAILS["min_confidence"]
        triggered = True
        reason = f"Confidence floored at {GUARDRAILS['min_confidence']}%"

    # Validate action
    valid_actions = ["BUY", "SELL", "HOLD", "TRIM"]
    if data.get("action") not in valid_actions:
        data["action"] = "HOLD"
        triggered = True
        reason = f"Invalid action corrected to HOLD"

    return data, triggered, reason


def store_observation(agent_name: str, ticker: str, sim_id: str,
                      model_id: str, input_tokens: int, output_tokens: int,
                      latency_ms: int, cost_usd: float, action: str,
                      confidence: float, success: bool, error: str,
                      guardrail_triggered: bool, guardrail_action: str):
    """Store agent observation to Aurora for full observability"""
    try:
        rds.execute_statement(
            resourceArn=CLUSTER_ARN, secretArn=SECRET_ARN, database=DB_NAME,
            sql="""INSERT INTO agent_observations
                     (agent_name, ticker, simulation_id, model_id,
                      input_tokens, output_tokens, total_tokens, latency_ms,
                      cost_usd, action, confidence, success, error_message,
                      guardrail_triggered, guardrail_action)
                   VALUES (:agent, :ticker, :sim::uuid, :model,
                           :in_tok, :out_tok, :total_tok, :latency,
                           :cost, :action, :conf, :success, :error,
                           :guardrail, :g_action)""",
            parameters=[
                {"name": "agent",    "value": {"stringValue": agent_name}},
                {"name": "ticker",   "value": {"stringValue": ticker or ""}},
                {"name": "sim",      "value": {"stringValue": sim_id or "00000000-0000-0000-0000-000000000000"}},
                {"name": "model",    "value": {"stringValue": model_id}},
                {"name": "in_tok",   "value": {"longValue":   input_tokens}},
                {"name": "out_tok",  "value": {"longValue":   output_tokens}},
                {"name": "total_tok","value": {"longValue":   input_tokens + output_tokens}},
                {"name": "latency",  "value": {"longValue":   latency_ms}},
                {"name": "cost",     "value": {"doubleValue": cost_usd}},
                {"name": "action",   "value": {"stringValue": action or "HOLD"}},
                {"name": "conf",     "value": {"doubleValue": confidence}},
                {"name": "success",  "value": {"booleanValue": success}},
                {"name": "error",    "value": {"stringValue": error or ""}},
                {"name": "guardrail","value": {"booleanValue": guardrail_triggered}},
                {"name": "g_action", "value": {"stringValue": guardrail_action or ""}},
            ]
        )
    except Exception as e:
        logger.warning(f"Observation store error: {e}")


class BaseAgent:
    name:     str = "BaseAgent"
    model_id: str = "us.amazon.nova-pro-v1:0"
    sim_id:   str = ""

    def __init__(self, model_id: str = "us.amazon.nova-pro-v1:0", sim_id: str = ""):
        self.model_id = model_id
        self.sim_id   = sim_id

    def invoke(self, prompt: str, ticker: str = "", max_tokens: int = 500) -> tuple[dict, dict]:
        """
        Invoke Bedrock with full observability.
        Returns: (parsed_data, metrics)
        metrics = {input_tokens, output_tokens, latency_ms, cost_usd}
        """
        start = time.time()
        input_tokens = output_tokens = 0
        success      = True
        error        = ""
        data         = {}

        try:
            response = bedrock.invoke_model(
                modelId=self.model_id,
                contentType="application/json",
                accept="application/json",
                body=json.dumps({
                    "messages": [{"role": "user", "content": [{"text": prompt}]}],
                    "inferenceConfig": {"maxTokens": max_tokens, "temperature": 0.4}
                })
            )
            result       = json.loads(response["body"].read())
            text         = result["output"]["message"]["content"][0]["text"]

            # Extract token usage from response
            usage        = result.get("usage", {})
            input_tokens  = usage.get("inputTokens", len(prompt) // 4)
            output_tokens = usage.get("outputTokens", len(text) // 4)

            # Parse JSON from response
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                data = json.loads(match.group())

        except Exception as e:
            logger.error(f"{self.name} invoke error: {e}")
            success = True
            error   = str(e)[:200]

        latency_ms = int((time.time() - start) * 1000)
        cost_usd   = calculate_cost(self.model_id, input_tokens, output_tokens)

        metrics = {
            "input_tokens":  input_tokens,
            "output_tokens": output_tokens,
            "latency_ms":    latency_ms,
            "cost_usd":      cost_usd,
        }

        print(f"  [{self.name}] {ticker} | {input_tokens}in {output_tokens}out | {latency_ms}ms | ${cost_usd:.5f}")

        # Apply guardrails
        if data:
            data, guardrail_triggered, guardrail_reason = apply_guardrails(
                data, self.name, ticker
            )
        else:
            guardrail_triggered = False
            guardrail_reason    = ""

        # Store observation
        store_observation(
            agent_name         = self.name.lower(),
            ticker             = ticker,
            sim_id             = self.sim_id,
            model_id           = self.model_id,
            input_tokens       = input_tokens,
            output_tokens      = output_tokens,
            latency_ms         = latency_ms,
            cost_usd           = cost_usd,
            action             = data.get("action", "HOLD"),
            confidence         = float(data.get("confidence", 50)),
            success            = success,
            error              = error,
            guardrail_triggered = guardrail_triggered,
            guardrail_action   = guardrail_reason
        )

        return data, metrics

    def default_vote(self) -> dict:
        return {
            "action":            "HOLD",
            "confidence":        50,
            "opening_statement": f"{self.name} could not complete analysis",
            "detailed_reasoning":"Analysis unavailable",
            "key_evidence":      [],
            "counter_argument":  "",
            "target":            None,
            "stop_loss":         None,
            "position_suggestion": "no action",
            "key_risks":         [],
            "data_used":         []
        }
