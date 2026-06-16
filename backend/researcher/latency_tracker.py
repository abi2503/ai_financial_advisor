"""
Persist per-query latency + trace metadata to Aurora query_latency_metrics.

Extension guide (future phases):
  1. Create LatencyTracker at the route entrypoint with route='fast'|'deep'|...
  2. activate_trace(QueryTrace()) alongside activate_tracker(tracker)
  3. Call tracker.mark_context_ms() / mark_agent_ms() / mark_first_token_ms()
  4. In new tools: record_tool('my_tool', apis=['Some API'])
  5. await tracker.flush() on success or failure — no schema change needed for new tools
"""
from __future__ import annotations

import json
import logging
import time
import uuid
from contextvars import ContextVar
from typing import Optional

import boto3

from query_trace import QueryTrace, get_trace

logger = logging.getLogger(__name__)

_tracker_var: ContextVar[Optional["LatencyTracker"]] = ContextVar("latency_tracker", default=None)

CLUSTER_ARN = __import__("os").environ.get("DB_CLUSTER_ARN", "")
SECRET_ARN  = __import__("os").environ.get("DB_SECRET_ARN", "")
DB_NAME     = __import__("os").environ.get("DB_NAME", "alex_db")
REGION      = __import__("os").environ.get("AWS_REGION", "us-east-1")


def activate_tracker(tracker: "LatencyTracker"):
    return _tracker_var.set(tracker)


def deactivate_tracker(token) -> None:
    try:
        _tracker_var.reset(token)
    except ValueError:
        # StreamingResponse runs finally in a different async context — non-fatal
        pass


def get_tracker() -> Optional["LatencyTracker"]:
    return _tracker_var.get()


class LatencyTracker:
    def __init__(
        self,
        query:      str,
        route:      str,
        clerk_id:   str = "",
        session_id: str = "",
        model:      str = "",
    ):
        self.query_id     = str(uuid.uuid4())
        self.query        = query[:500]
        self.route        = route
        self.clerk_id     = clerk_id
        self.session_id   = session_id
        self.model        = model
        self.t0           = time.monotonic()
        self.context_ms   = 0
        self.agent_ms     = 0
        self.guardrail_ms = 0
        self.first_token_ms: Optional[int] = None
        self.total_ms     = 0
        self.response_chars = 0
        self.success      = True
        self.partial      = False
        self.input_tokens  = 0
        self.output_tokens = 0
        self.cost_usd      = 0.0

    def mark_context_ms(self, ms: int) -> None:
        self.context_ms = ms

    def mark_agent_ms(self, ms: int) -> None:
        self.agent_ms = ms

    def mark_guardrail_ms(self, ms: int) -> None:
        self.guardrail_ms = ms

    def mark_first_token_ms(self, ms: Optional[int] = None) -> None:
        if ms is None:
            ms = int((time.monotonic() - self.t0) * 1000)
        if self.first_token_ms is None:
            self.first_token_ms = ms

    def set_model(self, model: str) -> None:
        self.model = model

    def set_response(self, text: str) -> None:
        self.response_chars = len(text or "")

    def set_token_usage(self, input_tokens: int, output_tokens: int) -> None:
        """Record Bedrock usage from response metadata."""
        from bedrock_cost import calculate_cost, normalize_model_id
        self.input_tokens  = max(0, int(input_tokens))
        self.output_tokens = max(0, int(output_tokens))
        self.cost_usd      = calculate_cost(normalize_model_id(self.model), self.input_tokens, self.output_tokens)

    def _finalize_tokens(self) -> None:
        """Estimate tokens/cost when Bedrock did not return usage metadata."""
        if self.input_tokens or self.output_tokens:
            return
        if self.response_chars <= 0:
            return
        from bedrock_cost import estimate_tokens, calculate_cost, normalize_model_id
        self.input_tokens  = estimate_tokens(self.query)
        self.output_tokens = estimate_tokens("x" * self.response_chars)
        self.cost_usd      = calculate_cost(
            normalize_model_id(self.model), self.input_tokens, self.output_tokens,
        )

    def _resolve_db_user_id(self, rds) -> Optional[str]:
        if not self.clerk_id or not CLUSTER_ARN:
            return None
        try:
            rds.execute_statement(
                resourceArn=CLUSTER_ARN,
                secretArn=SECRET_ARN,
                database=DB_NAME,
                sql="""
                    INSERT INTO users (clerk_id, email, name)
                    VALUES (:cid, '', 'User')
                    ON CONFLICT (clerk_id) DO UPDATE SET updated_at = NOW()
                """,
                parameters=[{"name": "cid", "value": {"stringValue": self.clerk_id}}],
            )
            r = rds.execute_statement(
                resourceArn=CLUSTER_ARN,
                secretArn=SECRET_ARN,
                database=DB_NAME,
                sql="SELECT id::text FROM users WHERE clerk_id = :cid LIMIT 1",
                parameters=[{"name": "cid", "value": {"stringValue": self.clerk_id}}],
            )
            if r.get("records"):
                return r["records"][0][0].get("stringValue")
        except Exception as e:
            logger.warning(f"User resolve failed: {e}")
        return None

    def flush(self, trace: Optional[QueryTrace] = None) -> None:
        """Write metrics to Aurora (non-fatal)."""
        if not CLUSTER_ARN or not SECRET_ARN:
            return

        trace = trace or get_trace()
        self.total_ms = int((time.monotonic() - self.t0) * 1000)
        self._finalize_tokens()

        trace_dict = trace.to_dict() if trace else {"tools": [], "mcp_servers": [], "data_sources": []}
        tools = trace_dict["tools"]
        mcps  = trace_dict["mcp_servers"]
        apis  = trace_dict["data_sources"]

        try:
            rds     = boto3.client("rds-data", region_name=REGION)
            db_user = self._resolve_db_user_id(rds)

            params = [
                {"name": "qid",    "value": {"stringValue": self.query_id}},
                {"name": "query",  "value": {"stringValue": self.query}},
                {"name": "route",  "value": {"stringValue": self.route}},
                {"name": "sid",    "value": {"stringValue": self.session_id or ""}},
                {"name": "total",  "value": {"longValue":   self.total_ms}},
                {"name": "ctx",    "value": {"longValue":   self.context_ms}},
                {"name": "agent",  "value": {"longValue":   self.agent_ms}},
                {"name": "guard",  "value": {"longValue":   self.guardrail_ms}},
                {"name": "model",  "value": {"stringValue": self.model or ""}},
                {"name": "chars",  "value": {"longValue":   self.response_chars}},
                {"name": "tools",  "value": {"stringValue": json.dumps(tools)}},
                {"name": "mcps",   "value": {"stringValue": json.dumps(mcps)}},
                {"name": "apis",   "value": {"stringValue": json.dumps(apis)}},
                {"name": "ok",     "value": {"booleanValue": self.success}},
                {"name": "part",   "value": {"booleanValue": self.partial}},
                {"name": "in_tok", "value": {"longValue":   self.input_tokens}},
                {"name": "out_tok","value": {"longValue":   self.output_tokens}},
                {"name": "cost",   "value": {"doubleValue": float(self.cost_usd)}},
            ]

            user_sql = ""
            if db_user:
                user_sql = ", user_id = :uid::uuid"
                params.append({"name": "uid", "value": {"stringValue": db_user}})

            ft_sql = ""
            if self.first_token_ms is not None:
                ft_sql = ", first_token_ms = :ft"
                params.append({"name": "ft", "value": {"longValue": self.first_token_ms}})

            rds.execute_statement(
                resourceArn=CLUSTER_ARN,
                secretArn=SECRET_ARN,
                database=DB_NAME,
                sql=f"""
                    INSERT INTO query_latency_metrics (
                        query_id, query, route, session_id,
                        total_ms, context_ms, agent_ms, guardrail_ms,
                        rag_ms, synthesis_ms,
                        model, response_chars,
                        tools_called, mcp_servers, data_sources,
                        success, partial,
                        input_tokens, output_tokens, cost_usd
                        {', user_id' if db_user else ''}
                        {', first_token_ms' if self.first_token_ms is not None else ''}
                    ) VALUES (
                        :qid, :query, :route, :sid,
                        :total, :ctx, :agent, :guard,
                        :ctx, :agent,
                        :model, :chars,
                        :tools::jsonb, :mcps::jsonb, :apis::jsonb,
                        :ok, :part,
                        :in_tok, :out_tok, :cost
                        {', :uid::uuid' if db_user else ''}
                        {', :ft' if self.first_token_ms is not None else ''}
                    )
                """,
                parameters=params,
            )
            logger.info(
                f"Latency flushed: route={self.route} total={self.total_ms}ms "
                f"tokens={self.input_tokens}in/{self.output_tokens}out cost=${self.cost_usd:.6f} "
                f"summary={trace.pass_fail_summary() if trace else {}}"
            )
        except Exception as e:
            logger.warning(f"Latency flush failed (non-fatal): {e}")
