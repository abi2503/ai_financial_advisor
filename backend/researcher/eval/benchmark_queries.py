"""Standard benchmark queries for RAGAS evaluation."""

TEST_QUERIES = [
    {
        "question": "What are NVIDIA's main risk factors?",
        "ground_truth": (
            "NVIDIA faces risks including supply chain dependencies, competition from AMD and Intel, "
            "export restrictions, manufacturing lead times, and customer concentration in data center markets."
        ),
        "expected_topics": ["risk", "nvidia", "competition", "supply chain"],
    },
    {
        "question": "What is NVIDIA's revenue growth driven by?",
        "ground_truth": (
            "NVIDIA revenue growth is driven by data center compute and networking platforms for "
            "accelerated computing and AI solutions, with Blackwell architectures representing much of Data Center revenue."
        ),
        "expected_topics": ["nvidia", "revenue", "data center", "AI", "blackwell"],
    },
    {
        "question": "What do analysts think about NVIDIA stock?",
        "ground_truth": (
            "Analysts have a consensus Buy rating on NVIDIA with average price targets above current "
            "trading levels, citing strong AI infrastructure demand."
        ),
        "expected_topics": ["analyst", "buy", "price target", "nvidia"],
    },
    {
        "question": "What is NVIDIA's business focus?",
        "ground_truth": (
            "NVIDIA is a data center scale AI infrastructure company that pioneered accelerated computing, "
            "with products spanning gaming GPUs, scientific computing, AI, autonomous vehicles, and robotics."
        ),
        "expected_topics": ["nvidia", "AI", "data center", "GPU", "accelerated computing"],
    },
    {
        "question": "What are the latest financial research insights stored in Alex?",
        "ground_truth": (
            "Alex stores research on major technology stocks including NVIDIA with analysis covering "
            "market data, SEC filings, analyst ratings, and AI sector developments."
        ),
        "expected_topics": ["research", "financial", "stock", "analysis"],
    },
]

# Smoke subset for quick CI / observe checks
SMOKE_QUERIES = TEST_QUERIES[:3]
