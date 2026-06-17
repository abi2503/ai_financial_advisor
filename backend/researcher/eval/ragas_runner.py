"""
RAGAS evaluation with Bedrock LLM judge.

Pipeline:
  benchmark query → search API (pgvector) → Bedrock answer → RAGAS metrics → Aurora
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import boto3
import httpx
from datasets import Dataset
from dotenv import load_dotenv
from langchain_aws import BedrockEmbeddings, ChatBedrockConverse
from pydantic import BaseModel
from ragas import evaluate
from ragas.embeddings import LangchainEmbeddingsWrapper
from ragas.llms import LangchainLLMWrapper
from ragas.metrics import answer_relevancy, context_precision, context_recall, faithfulness

from eval.benchmark_queries import SMOKE_QUERIES, TEST_QUERIES
from eval.db import is_configured, new_run_id, save_eval_run

logger = logging.getLogger(__name__)

load_dotenv(override=True)

REGION         = os.environ.get("AWS_REGION", os.environ.get("AWS_REGION_NAME", "us-east-1"))
SEARCH_API     = os.environ.get("ALEX_SEARCH_API", os.environ.get("SEARCH_API", ""))
SEARCH_API_KEY = os.environ.get("ALEX_SEARCH_API_KEY", os.environ.get("ALEX_API_KEY", ""))
if not SEARCH_API:
    _ingest = os.environ.get("ALEX_API_ENDPOINT", "")
    if _ingest.endswith("/ingest"):
        SEARCH_API = _ingest.replace("/ingest", "/search")
if not SEARCH_API_KEY:
    SEARCH_API_KEY = os.environ.get("ALEX_API_KEY", "")
JUDGE_MODEL    = os.environ.get("RAGAS_JUDGE_MODEL", "us.amazon.nova-lite-v1:0")
GEN_MODEL      = os.environ.get("RAGAS_GEN_MODEL", "us.amazon.nova-pro-v1:0")
EMBED_MODEL    = os.environ.get("RAGAS_EMBED_MODEL", "amazon.titan-embed-text-v2:0")

# Gate thresholds (deploy block per P17)
THRESHOLDS = {
    "answer_relevancy":   0.85,
    "faithfulness":       0.88,
    "hallucination_rate": 0.08,
    "context_recall":     0.70,
}


class QueryMetrics(BaseModel):
    faithfulness:       float
    answer_relevancy:   float
    context_precision:  float
    context_recall:     float
    hallucination_rate: float
    overall_score:      float
    passed:             bool


@dataclass
class EvalRunResult:
    run_id:             str
    gate:               str
    judge_model:        str
    passed:             bool
    query_count:        int
    faithfulness:       float
    answer_relevancy:   float
    context_precision:  float
    context_recall:     float
    hallucination_rate: float
    overall_score:      float
    queries:            list[dict[str, Any]] = field(default_factory=list)
    evaluated_at:       str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _search_knowledge_base(query: str, top_k: int = 3) -> list[str]:
    if not SEARCH_API:
        logger.warning("ALEX_SEARCH_API not set")
        return []
    headers = {"Content-Type": "application/json"}
    if SEARCH_API_KEY:
        headers["x-api-key"] = SEARCH_API_KEY
    try:
        with httpx.Client(timeout=30) as client:
            resp = client.post(
                SEARCH_API,
                headers=headers,
                json={"query": query, "top_k": top_k},
            )
            resp.raise_for_status()
            data = resp.json()
        return [r.get("content", "") for r in data.get("results", []) if r.get("content")]
    except Exception as e:
        logger.error(f"Search failed: {e}")
        return []


def _generate_answer(question: str, contexts: list[str]) -> str:
    bedrock = boto3.client("bedrock-runtime", region_name=REGION)
    context_text = "\n\n".join(contexts) if contexts else "No context available."
    prompt = f"""You are Alex, a financial research assistant.
Use ONLY the context below. Do not invent prices or facts.

Context:
{context_text}

Question: {question}

Answer concisely based only on the context:"""

    body = json.dumps({
        "messages": [{"role": "user", "content": [{"text": prompt}]}],
        "inferenceConfig": {"maxTokens": 500, "temperature": 0.1},
    })
    try:
        resp = bedrock.invoke_model(
            modelId=GEN_MODEL,
            contentType="application/json",
            accept="application/json",
            body=body,
        )
        out = json.loads(resp["body"].read())
        return out["output"]["message"]["content"][0]["text"].strip()
    except Exception as e:
        logger.error(f"Generation failed: {e}")
        return "Could not generate answer."


def _build_ragas_judge():
    llm = LangchainLLMWrapper(
        ChatBedrockConverse(model=JUDGE_MODEL, region_name=REGION, temperature=0)
    )
    embeddings = LangchainEmbeddingsWrapper(
        BedrockEmbeddings(model_id=EMBED_MODEL, region_name=REGION)
    )
    return llm, embeddings


def _score_single(
    question: str,
    answer: str,
    contexts: list[str],
    ground_truth: str,
    llm,
    embeddings,
) -> QueryMetrics:
    """Run RAGAS library metrics for one query (LLM-as-judge)."""
    if not contexts:
        return QueryMetrics(
            faithfulness=0.0, answer_relevancy=0.0, context_precision=0.0,
            context_recall=0.0, hallucination_rate=1.0, overall_score=0.0, passed=False,
        )

    ds = Dataset.from_dict({
        "question":     [question],
        "answer":       [answer],
        "contexts":     [contexts],
        "ground_truth": [ground_truth],
    })
    result = evaluate(
        ds,
        metrics=[faithfulness, answer_relevancy, context_recall, context_precision],
        llm=llm,
        embeddings=embeddings,
    )
    scores = dict(result)
    f  = float(scores.get("faithfulness") or 0)
    ar = float(scores.get("answer_relevancy") or 0)
    cp = float(scores.get("context_precision") or 0)
    cr = float(scores.get("context_recall") or 0)
    hall = round(max(0.0, 1.0 - f), 3)
    overall = round((f + ar + cp + cr) / 4, 3)
    passed = (
        ar >= THRESHOLDS["answer_relevancy"]
        and f >= THRESHOLDS["faithfulness"]
        and hall <= THRESHOLDS["hallucination_rate"]
    )
    return QueryMetrics(
        faithfulness=round(f, 3),
        answer_relevancy=round(ar, 3),
        context_precision=round(cp, 3),
        context_recall=round(cr, 3),
        hallucination_rate=hall,
        overall_score=overall,
        passed=passed,
    )


def _aggregate_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    n = max(len(rows), 1)
    avg = lambda k: round(sum(r["metrics"][k] for r in rows) / n, 3)
    summary = {
        "faithfulness":       avg("faithfulness"),
        "answer_relevancy":   avg("answer_relevancy"),
        "context_precision":  avg("context_precision"),
        "context_recall":     avg("context_recall"),
        "hallucination_rate": avg("hallucination_rate"),
        "overall_score":      avg("overall_score"),
        "query_count":        len(rows),
        "backend":            "pgvector",
    }
    summary["passed"] = (
        summary["answer_relevancy"] >= THRESHOLDS["answer_relevancy"]
        and summary["faithfulness"] >= THRESHOLDS["faithfulness"]
        and summary["hallucination_rate"] <= THRESHOLDS["hallucination_rate"]
    )
    return summary


def run_evaluation(
    gate: str = "manual",
    smoke: bool = False,
    persist: bool = True,
    report_path: str | None = None,
) -> EvalRunResult:
    """
    Run full RAGAS eval with Bedrock judge.

    Args:
        gate: manual | ci | weekly | observe
        smoke: use 3 queries instead of 5
        persist: write to Aurora ragas_eval_runs + ragas_evaluations
        report_path: local JSON report (relative to repo root)
    """
    queries_cfg = SMOKE_QUERIES if smoke else TEST_QUERIES
    run_id = new_run_id()
    llm, embeddings = _build_ragas_judge()

    print("\n🧪 Alex RAGAS Evaluation (LLM judge)")
    print("=" * 50)
    print(f"Gate:    {gate}")
    print(f"Judge:   {JUDGE_MODEL}")
    print(f"Queries: {len(queries_cfg)}")
    print(f"Run ID:  {run_id}")
    print("=" * 50)

    rows: list[dict[str, Any]] = []

    for i, test in enumerate(queries_cfg):
        question = test["question"]
        print(f"\nQuery {i + 1}/{len(queries_cfg)}: {question[:70]}...")

        contexts = _search_knowledge_base(question)
        print(f"  Context chunks: {len(contexts)}")

        answer = _generate_answer(question, contexts)
        print(f"  Answer: {answer[:100]}...")

        metrics = _score_single(
            question, answer, contexts, test["ground_truth"], llm, embeddings
        )
        print(f"  faithfulness={metrics.faithfulness} relevancy={metrics.answer_relevancy} "
              f"recall={metrics.context_recall} hall={metrics.hallucination_rate}")

        rows.append({
            "question":     question,
            "answer":       answer,
            "ground_truth": test["ground_truth"],
            "contexts":     contexts,
            "expected_topics": test.get("expected_topics", []),
            "metrics":      metrics.model_dump(),
            "audit": {
                "judge_model": JUDGE_MODEL,
                "gen_model":   GEN_MODEL,
                "search_api":  SEARCH_API[:60] if SEARCH_API else "",
                "method":      "ragas_library_bedrock_judge",
            },
        })
        time.sleep(0.5)

    summary = _aggregate_metrics(rows)
    evaluated_at = datetime.now(timezone.utc).isoformat()

    result = EvalRunResult(
        run_id=run_id,
        gate=gate,
        judge_model=JUDGE_MODEL,
        passed=summary["passed"],
        query_count=len(rows),
        faithfulness=summary["faithfulness"],
        answer_relevancy=summary["answer_relevancy"],
        context_precision=summary["context_precision"],
        context_recall=summary["context_recall"],
        hallucination_rate=summary["hallucination_rate"],
        overall_score=summary["overall_score"],
        queries=rows,
        evaluated_at=evaluated_at,
    )

    print("\n" + "=" * 50)
    print("📊 RAGAS SUMMARY (LLM judge)")
    print(f"  Faithfulness:     {summary['faithfulness']:.3f}  (gate ≥ {THRESHOLDS['faithfulness']})")
    print(f"  Answer Relevancy: {summary['answer_relevancy']:.3f}  (gate ≥ {THRESHOLDS['answer_relevancy']})")
    print(f"  Context Recall:   {summary['context_recall']:.3f}")
    print(f"  Hallucination:    {summary['hallucination_rate']:.3f}  (gate ≤ {THRESHOLDS['hallucination_rate']})")
    print(f"  Overall:          {summary['overall_score']:.3f}")
    print(f"  PASSED:           {'✅ YES' if summary['passed'] else '❌ NO'}")
    print("=" * 50)

    if persist:
        if is_configured():
            try:
                save_eval_run(run_id, gate, JUDGE_MODEL, summary, rows)
                print(f"  ✅ Saved to Aurora (run_id={run_id})")
            except Exception as e:
                print(f"  ⚠️  Aurora persist failed: {e}")
        else:
            print("  ⚠️  Aurora not configured — skipped persist")

    if report_path:
        root = Path(__file__).resolve().parents[3]
        out = root / report_path
        try:
            out.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "date": evaluated_at,
                "run_id": run_id,
                "gate": gate,
                "judge_model": JUDGE_MODEL,
                "method": "ragas_library_bedrock_judge",
                "summary": summary,
                "thresholds": THRESHOLDS,
                "queries": rows,
            }
            out.write_text(json.dumps(payload, indent=2))
            print(f"  Report: {out}")
        except OSError as e:
            logger.warning(f"Could not write RAGAS report: {e}")

    return result
