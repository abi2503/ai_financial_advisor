"""
Bedrock model pricing for per-query cost attribution (USD per 1K tokens).
Mirrors trading floor base_agent.py — keep rates in sync.
"""
from __future__ import annotations

MODEL_COSTS: dict[str, dict[str, float]] = {
    "us.amazon.nova-pro-v1:0":   {"input": 0.0008,  "output": 0.0032},
    "us.amazon.nova-lite-v1:0":  {"input": 0.00006, "output": 0.00024},
    "us.amazon.nova-micro-v1:0": {"input": 0.000035, "output": 0.00014},
    "anthropic.claude-3-5-sonnet-20241022-v2:0": {"input": 0.003, "output": 0.015},
    "anthropic.claude-3-haiku-20240307-v1:0":    {"input": 0.00025, "output": 0.00125},
}


def normalize_model_id(model: str) -> str:
    """bedrock/us.amazon.nova-lite-v1:0 → us.amazon.nova-lite-v1:0"""
    return (model or "").replace("bedrock/", "").strip()


def calculate_cost(model_id: str, input_tokens: int, output_tokens: int) -> float:
    mid = normalize_model_id(model_id)
    rates = MODEL_COSTS.get(mid, MODEL_COSTS["us.amazon.nova-lite-v1:0"])
    return (input_tokens * rates["input"] + output_tokens * rates["output"]) / 1000.0


def estimate_tokens(text: str) -> int:
    """Rough token estimate when Bedrock usage metadata is unavailable."""
    return max(1, len(text or "") // 4)
