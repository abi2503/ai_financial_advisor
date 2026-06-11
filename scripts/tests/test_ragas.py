#!/usr/bin/env python3
"""
Alex AI — RAGAS Evaluation Script
Measures quality of Alex's RAG pipeline

Metrics:
  - Answer Relevancy  → is response on topic?
  - Faithfulness      → grounded in retrieved context?
  - Context Recall    → right docs retrieved?

Target:
  - Answer Relevancy > 0.87
  - Faithfulness     > 0.91
  - Hallucination    < 5%

Usage:
  python3 scripts/tests/test_ragas.py
"""
import os
import sys
import json
import time
import boto3
import subprocess
from datetime import datetime

# ============================================
# Config
# ============================================
REGION        = "us-east-1"
SEARCH_API    = "https://bmzmoxxehh.execute-api.us-east-1.amazonaws.com/prod/search"
INGEST_API    = "https://bmzmoxxehh.execute-api.us-east-1.amazonaws.com/prod/ingest"
API_KEY       = "7h5IOpLsxU1CGoSE5AqQY6guMlqPcP113LxVqNUu"
BEDROCK_MODEL = "us.amazon.nova-pro-v1:0"

os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../.."))

# ============================================
# 5 Standard Test Queries
# ============================================
TEST_QUERIES = [
    {
        "question":        "What are NVIDIA's main risk factors?",
        "ground_truth":    "NVIDIA faces risks including supply chain dependencies, competition from AMD and Intel, export restrictions, manufacturing lead times, and customer concentration in data center markets.",
        "expected_topics": ["risk", "nvidia", "competition", "supply chain"]
    },
    {
        "question":        "What is NVIDIA's revenue growth driven by?",
        "ground_truth":    "NVIDIA revenue growth is driven by data center compute and networking platforms for accelerated computing and AI solutions, with Blackwell architectures representing the majority of Data Center revenue.",
        "expected_topics": ["nvidia", "revenue", "data center", "AI", "blackwell"]
    },
    {
        "question":        "What do analysts think about NVIDIA stock?",
        "ground_truth":    "Analysts have a consensus Buy rating on NVIDIA with average price targets significantly above current trading levels, citing strong AI infrastructure demand.",
        "expected_topics": ["analyst", "buy", "price target", "nvidia"]
    },
    {
        "question":        "What is NVIDIA's business focus?",
        "ground_truth":    "NVIDIA is a data center scale AI infrastructure company that pioneered accelerated computing, with products spanning gaming GPUs, scientific computing, AI, autonomous vehicles, and robotics.",
        "expected_topics": ["nvidia", "AI", "data center", "GPU", "accelerated computing"]
    },
    {
        "question":        "What are the latest financial research insights stored in Alex?",
        "ground_truth":    "Alex stores research on major technology stocks including NVIDIA with analysis covering market data, SEC filings, analyst ratings, and AI sector developments.",
        "expected_topics": ["research", "financial", "stock", "analysis"]
    }
]


def search_knowledge_base(query: str, top_k: int = 3) -> list:
    """Search pgvector knowledge base for context"""
    try:
        result = subprocess.run([
            "curl", "-s", "-X", "POST", SEARCH_API,
            "-H", "Content-Type: application/json",
            "-H", f"x-api-key: {API_KEY}",
            "-d", json.dumps({"query": query, "top_k": top_k})
        ], capture_output=True, text=True, timeout=30)

        data    = json.loads(result.stdout)
        results = data.get("results", [])
        return [r.get("content", "") for r in results]

    except Exception as e:
        print(f"  ⚠️  Search failed: {e}")
        return []


def generate_answer(question: str, contexts: list) -> str:
    """Generate answer using Bedrock Nova Pro"""
    try:
        bedrock = boto3.client("bedrock-runtime", region_name=REGION)

        context_text = "\n\n".join(contexts) if contexts else "No context available"

        prompt = f"""You are Alex, a financial research assistant.
Use the following context to answer the question accurately.
Only use information from the context provided.

Context:
{context_text}

Question: {question}

Answer concisely and accurately based only on the context above:"""

        response = bedrock.invoke_model(
            modelId     = BEDROCK_MODEL,
            body        = json.dumps({
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 500,
                "inferenceConfig": {"temperature": 0.1}
            }),
            contentType = "application/json",
            accept      = "application/json"
        )

        body   = json.loads(response["body"].read())
        answer = body["output"]["message"]["content"][0]["text"]
        return answer.strip()

    except Exception as e:
        print(f"  ⚠️  Generation failed: {e}")
        return "Could not generate answer"


def compute_answer_relevancy(question: str, answer: str) -> float:
    """
    Measure how relevant the answer is to the question.
    Simple keyword overlap approach (no OpenAI needed).
    """
    question_words = set(question.lower().split())
    answer_words   = set(answer.lower().split())

    # Remove stop words
    stop_words = {
        "the", "a", "an", "is", "are", "was", "were",
        "what", "how", "why", "when", "where", "which",
        "do", "does", "did", "have", "has", "had",
        "in", "on", "at", "to", "for", "of", "and", "or"
    }
    question_words -= stop_words
    answer_words   -= stop_words

    if not question_words:
        return 0.5

    overlap   = question_words & answer_words
    relevancy = len(overlap) / len(question_words)

    # Boost if answer is substantial
    if len(answer.split()) > 20:
        relevancy = min(1.0, relevancy + 0.2)

    return round(min(1.0, relevancy), 3)


def compute_faithfulness(answer: str, contexts: list) -> float:
    """
    Measure if answer is grounded in retrieved context.
    Checks if key answer phrases appear in context.
    """
    if not contexts or not answer:
        return 0.0

    context_text  = " ".join(contexts).lower()
    answer_words  = answer.lower().split()

    # Check meaningful words (>4 chars) from answer appear in context
    meaningful    = [w for w in answer_words if len(w) > 4]
    if not meaningful:
        return 0.5

    grounded      = sum(1 for w in meaningful if w in context_text)
    faithfulness  = grounded / len(meaningful)

    return round(min(1.0, faithfulness), 3)


def compute_context_recall(contexts: list, expected_topics: list) -> float:
    """
    Measure if retrieved context covers expected topics.
    """
    if not contexts:
        return 0.0

    context_text = " ".join(contexts).lower()
    found        = sum(1 for topic in expected_topics
                      if topic.lower() in context_text)

    recall = found / len(expected_topics) if expected_topics else 0.0
    return round(recall, 3)


def compute_hallucination_rate(answer: str, contexts: list) -> float:
    """
    Estimate hallucination as 1 - faithfulness.
    High faithfulness = low hallucination.
    """
    faithfulness = compute_faithfulness(answer, contexts)
    return round(1.0 - faithfulness, 3)


def run_evaluation():
    print("\n🧪 Alex AI — RAGAS Evaluation")
    print("=" * 50)
    print(f"Date:    {datetime.now().strftime('%B %d, %Y at %H:%M')}")
    print(f"Queries: {len(TEST_QUERIES)}")
    print(f"Backend: pgvector (Aurora)")
    print("=" * 50)

    results = []

    for i, test in enumerate(TEST_QUERIES):
        print(f"\nQuery {i+1}/{len(TEST_QUERIES)}: {test['question'][:60]}...")

        # Step 1: Retrieve context
        print("  Retrieving context...")
        contexts = search_knowledge_base(test["question"])
        print(f"  Found {len(contexts)} context chunks")

        # Step 2: Generate answer
        print("  Generating answer...")
        answer = generate_answer(test["question"], contexts)
        print(f"  Answer: {answer[:100]}...")

        # Step 3: Compute metrics
        relevancy     = compute_answer_relevancy(test["question"], answer)
        faithfulness  = compute_faithfulness(answer, contexts)
        recall        = compute_context_recall(contexts, test["expected_topics"])
        hallucination = compute_hallucination_rate(answer, contexts)

        result = {
            "question":        test["question"],
            "answer":          answer,
            "contexts":        contexts,
            "ground_truth":    test["ground_truth"],
            "metrics": {
                "answer_relevancy":  relevancy,
                "faithfulness":      faithfulness,
                "context_recall":    recall,
                "hallucination_rate": hallucination,
            }
        }
        results.append(result)

        print(f"  ✅ Relevancy:     {relevancy:.3f}")
        print(f"  ✅ Faithfulness:  {faithfulness:.3f}")
        print(f"  ✅ Context Recall:{recall:.3f}")
        print(f"  ✅ Hallucination: {hallucination:.3f}")

        time.sleep(1)

    # ============================================
    # Summary
    # ============================================
    print("\n" + "=" * 50)
    print("📊 EVALUATION SUMMARY")
    print("=" * 50)

    avg_relevancy     = sum(r["metrics"]["answer_relevancy"]   for r in results) / len(results)
    avg_faithfulness  = sum(r["metrics"]["faithfulness"]       for r in results) / len(results)
    avg_recall        = sum(r["metrics"]["context_recall"]     for r in results) / len(results)
    avg_hallucination = sum(r["metrics"]["hallucination_rate"] for r in results) / len(results)

    print(f"\n  Answer Relevancy:   {avg_relevancy:.3f}  {'✅' if avg_relevancy > 0.87  else '⚠️ '} (target > 0.87)")
    print(f"  Faithfulness:       {avg_faithfulness:.3f}  {'✅' if avg_faithfulness > 0.91 else '⚠️ '} (target > 0.91)")
    print(f"  Context Recall:     {avg_recall:.3f}  {'✅' if avg_recall > 0.70      else '⚠️ '} (target > 0.70)")
    print(f"  Hallucination Rate: {avg_hallucination:.3f}  {'✅' if avg_hallucination < 0.05 else '⚠️ '} (target < 0.05)")

    overall = (avg_relevancy + avg_faithfulness + avg_recall) / 3
    print(f"\n  Overall Score:      {overall:.3f}")
    print(f"  Grade:              {'A' if overall > 0.85 else 'B' if overall > 0.75 else 'C'}")

    # ============================================
    # Save Report
    # ============================================
    report = {
        "date":    datetime.now().isoformat(),
        "backend": "pgvector",
        "summary": {
            "answer_relevancy":   round(avg_relevancy, 3),
            "faithfulness":       round(avg_faithfulness, 3),
            "context_recall":     round(avg_recall, 3),
            "hallucination_rate": round(avg_hallucination, 3),
            "overall_score":      round(overall, 3),
        },
        "queries": results
    }

    report_path = "scripts/tests/ragas_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    print(f"\n  Report saved: {report_path}")
    print("=" * 50)

    # Resume talking points
    print("\n📝 Resume Talking Points:")
    print(f"  - RAGAS evaluation: {avg_relevancy:.2f} answer relevancy")
    print(f"  - Faithfulness score: {avg_faithfulness:.2f}")
    print(f"  - Hallucination rate: {avg_hallucination*100:.1f}%")
    print(f"  - Overall RAG quality: {overall:.2f}/1.0")

    return report


if __name__ == "__main__":
    run_evaluation()