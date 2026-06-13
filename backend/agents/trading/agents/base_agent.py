"""
Base Agent - Shared agent class for all trading agents
"""
import json
import boto3
import logging
import re
from datetime import datetime, timezone

logger  = logging.getLogger(__name__)
UTC     = timezone.utc
bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")


class BaseAgent:
    name:     str = "BaseAgent"
    model_id: str = "us.amazon.nova-pro-v1:0"

    def invoke(self, prompt: str, max_tokens: int = 400) -> dict:
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
            result = json.loads(response["body"].read())
            text   = result["output"]["message"]["content"][0]["text"]
            match  = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                return json.loads(match.group())
            return {}
        except Exception as e:
            logger.error(f"{self.name} invoke error: {e}")
            return {}

    def default_vote(self, agent_name: str) -> dict:
        return {
            "action": "HOLD",
            "confidence": 50,
            "opening_statement": f"{agent_name} could not complete analysis",
            "detailed_reasoning": "Analysis unavailable",
            "key_evidence": [],
            "counter_argument": "",
            "target": None,
            "stop_loss": None,
            "position_suggestion": "no action",
            "key_risks": [],
            "data_used": []
        }
