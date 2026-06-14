"""
Tools available to the Alex research agent.
Hybrid approach: API for structured data, Playwright for context.
"""
import os
import httpx
import logging
from agents import function_tool
from datetime import datetime, UTC
from query_trace import record_tool, record_api, get_trace

logger = logging.getLogger(__name__)

@function_tool
async def get_sec_filings(ticker: str, form_type: str = "10-K") -> str:
    """
    Get SEC filing content using EdgarTools.
    Legally compliant — respects SEC rate limits.
    Returns actual filing content not just metadata.

    Why EdgarTools over Playwright for SEC:
      - Respects SEC rate limits automatically
      - Returns structured data not HTML
      - Access to risk factors, MD&A, financials
      - Much more reliable than browser scraping

    Args:
        ticker:    Stock ticker e.g. NVDA AAPL TSLA
        form_type: Filing type — 10-K, 10-Q, 8-K, 4

    Returns:
        Structured filing content as text
    """
    apis = [
        "SEC EDGAR (EdgarTools)",
        "https://www.sec.gov/cgi-bin/browse-edgar",
    ]
    t0 = __import__("time").monotonic()
    try:
        import edgar
        import asyncio

        # Set identity — required by SEC
        # Why: SEC requires identification for programmatic access
        edgar.set_identity("Alex AI Research alexai@example.com")

        # Run in executor since edgar is synchronous
        loop = asyncio.get_event_loop()

        def fetch_filing():
            company = edgar.Company(ticker.upper())
            filing  = company.get_filings(form=form_type).latest(1)

            if not filing:
                return f"No {form_type} filings found for {ticker}"

            result_parts = [
                f"{ticker.upper()} — {form_type} Filing",
                f"Filed: {filing.filing_date}",
                f"Period: {filing.period_of_report}",
                f"Accession: {filing.accession_no}",
                "---"
            ]

            # Get document object for structured access
            try:
                doc = filing.obj()

                # Risk Factors
                if hasattr(doc, 'risk_factors') and doc.risk_factors:
                    rf_text = str(doc.risk_factors)[:2000]
                    result_parts.append("RISK FACTORS:")
                    result_parts.append(rf_text)
                    result_parts.append("---")

                # Management Discussion
                if hasattr(doc, 'management_discussion') and doc.management_discussion:
                    md_text = str(doc.management_discussion)[:2000]
                    result_parts.append("MANAGEMENT DISCUSSION & ANALYSIS:")
                    result_parts.append(md_text)
                    result_parts.append("---")

                # Business section
                if hasattr(doc, 'business') and doc.business:
                    biz_text = str(doc.business)[:1000]
                    result_parts.append("BUSINESS OVERVIEW:")
                    result_parts.append(biz_text)
                    result_parts.append("---")

            except Exception as e:
                result_parts.append(f"Note: Could not parse filing content: {e}")

            return "\n".join(result_parts)

        result = await loop.run_in_executor(None, fetch_filing)
        logger.info(f"EdgarTools fetched {form_type} for {ticker}")
        ok = not result.startswith("No ") and "Could not" not in result
        ms = int((__import__("time").monotonic() - t0) * 1000)
        record_tool("get_sec_filings", success=ok, error="" if ok else result[:120], latency_ms=ms, apis=apis)
        record_api("SEC EDGAR (EdgarTools)", success=ok, error="" if ok else result[:120], latency_ms=ms)
        return result

    except Exception as e:
        logger.error(f"EdgarTools error for {ticker}: {e}")
        ms = int((__import__("time").monotonic() - t0) * 1000)
        err = str(e)[:120]
        record_tool("get_sec_filings", success=False, error=err, latency_ms=ms, apis=apis)
        record_api("SEC EDGAR (EdgarTools)", success=False, error=err, latency_ms=ms)
        return f"Could not fetch {form_type} for {ticker}: {str(e)}"

@function_tool
async def get_stock_data(ticker: str) -> str:
    """
    Get real-time stock data AND recent news for a ticker.
    Uses Yahoo Finance API for metrics and RSS for news.
    Call this once per stock you are researching.

    Args:
        ticker: Stock ticker symbol e.g. NVDA AAPL TSLA

    Returns:
        Current stock metrics and recent news headlines
    """
    import time as time_mod
    apis = [
        "Yahoo Finance API (yfinance)",
        "Yahoo Finance RSS (feeds.finance.yahoo.com)",
    ]
    t0 = time_mod.monotonic()
    try:
        import yfinance as yf
        import xml.etree.ElementTree as ET

        ticker = ticker.upper().strip()

        # Retry yfinance up to 3 times
        # Why: Yahoo Finance rate limits ECS IPs
        #      Retry with backoff fixes most cases
        info = {}
        for attempt in range(2):
            try:
                stock = yf.Ticker(ticker)
                info  = stock.info
                # Verify we got real data not empty
                if info.get('currentPrice') or info.get('regularMarketPrice'):
                    break
                print(f"yfinance attempt {attempt+1} returned empty — retrying...")
                time_mod.sleep(1)
            except Exception as e:
                print(f"yfinance attempt {attempt+1} failed: {e}")
                if attempt < 1:
                    time_mod.sleep(1)

        # Extract metrics with safe fallbacks
        price     = info.get('currentPrice') or info.get('regularMarketPrice') or info.get('previousClose', 'N/A')
        mkt_cap   = info.get('marketCap', 'N/A')
        pe_ratio  = info.get('trailingPE', 'N/A')
        fwd_pe    = info.get('forwardPE', 'N/A')
        div_yield = info.get('dividendYield', 'N/A')
        week_high = info.get('fiftyTwoWeekHigh', 'N/A')
        week_low  = info.get('fiftyTwoWeekLow', 'N/A')
        revenue   = info.get('totalRevenue', 'N/A')
        margins   = info.get('profitMargins', 'N/A')
        name      = info.get('longName') or info.get('shortName') or ticker
        sector    = info.get('sector', 'N/A')
        analyst   = info.get('recommendationKey', 'N/A')
        target    = info.get('targetMeanPrice', 'N/A')

        # Format numbers
        if isinstance(mkt_cap,   (int, float)): mkt_cap   = f"${mkt_cap/1e9:.2f}B"
        if isinstance(revenue,   (int, float)): revenue   = f"${revenue/1e9:.2f}B"
        if isinstance(div_yield, float):        div_yield = f"{div_yield*100:.2f}%"
        if isinstance(margins,   float):        margins   = f"{margins*100:.2f}%"
        if isinstance(pe_ratio,  float):        pe_ratio  = f"{pe_ratio:.2f}x"
        if isinstance(fwd_pe,    float):        fwd_pe    = f"{fwd_pe:.2f}x"

        # If we couldn't get price show clear message
        yf_ok = price != 'N/A'
        if not yf_ok:
            print(f"Warning: Could not get price for {ticker} after retries")
        record_api("Yahoo Finance API (yfinance)", success=yf_ok,
                   error="" if yf_ok else "No price data returned", latency_ms=int((time_mod.monotonic() - t0) * 1000))

        # Build keywords from company name for news filtering
        keywords = [ticker.lower()]
        for word in name.split():
            if len(word) > 3 and word.lower() not in [
                'inc.', 'inc', 'corp', 'corp.', 'ltd',
                'ltd.', 'the', 'and', 'corporation', 'company'
            ]:
                keywords.append(word.lower())

        # Fetch news from Yahoo Finance RSS
        news_lines = []
        try:
            url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US"
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(url, headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                })

            if resp.status_code == 200:
                root    = ET.fromstring(resp.text)
                channel = root.find('channel')
                items   = channel.findall('item') if channel else []

                relevant = []
                fallback = []

                for item in items[:20]:
                    title    = item.findtext('title', '')
                    desc     = item.findtext('description', '')
                    combined = (title + ' ' + desc).lower()
                    pubdate  = item.findtext('pubDate', '')

                    if pubdate:
                        try:
                            from email.utils import parsedate_to_datetime
                            dt      = parsedate_to_datetime(pubdate)
                            pubdate = dt.strftime('%b %d %Y')
                        except Exception:
                            pubdate = pubdate[:16]

                    link  = item.findtext('link', '')
                    entry = f"- [{pubdate}] [{title}]({link})" if link else f"- [{pubdate}] {title}"
                    fallback.append(entry)

                    if any(kw in combined for kw in keywords):
                        relevant.append(entry)

                headlines  = relevant[:5] if len(relevant) >= 2 else fallback[:5]
                news_lines = headlines
                record_api("Yahoo Finance RSS (feeds.finance.yahoo.com)", url=url,
                           success=True, latency_ms=int((time_mod.monotonic() - t0) * 1000))

        except Exception as e:
            logger.warning(f"News fetch failed for {ticker}: {e}")
            news_lines = ["- News temporarily unavailable"]
            record_api("Yahoo Finance RSS (feeds.finance.yahoo.com)", success=False, error=str(e)[:120])

        news_text = "\n".join(news_lines) if news_lines else "- No recent news found"

        timestamp = datetime.now(UTC).strftime('%B %d, %Y at %H:%M UTC')

        result = f"""
{name} ({ticker}) — Market Data
Retrieved: {timestamp}
Source: Yahoo Finance API + RSS

MARKET DATA:
Price:          ${price}
Market Cap:     {mkt_cap}
Sector:         {sector}
P/E Ratio:      {pe_ratio}
Forward P/E:    {fwd_pe}
Dividend Yield: {div_yield}
Profit Margins: {margins}
52-Week High:   ${week_high}
52-Week Low:    ${week_low}
Annual Revenue: {revenue}
Analyst Rating: {analyst}
Analyst Target: ${target}

RECENT NEWS:
{news_text}

NOTE: Use this data directly. Do not override with memory.
"""
        logger.info(f"Fetched {ticker}: ${price} + {len(news_lines)} news items")
        tool_ok = yf_ok
        record_tool("get_stock_data", success=tool_ok,
                    error="" if tool_ok else "Price data unavailable", latency_ms=int((time_mod.monotonic() - t0) * 1000), apis=apis)
        return result

    except Exception as e:
        logger.error(f"Error fetching {ticker}: {type(e).__name__}: {e}")
        record_tool("get_stock_data", success=False, error=str(e)[:120],
                    latency_ms=int((time_mod.monotonic() - t0) * 1000), apis=apis)
        record_api("Yahoo Finance API (yfinance)", success=False, error=str(e)[:120])
        return f"""
{ticker} — Data temporarily limited
Note: Yahoo Finance rate limiting detected.

Please analyze {ticker} based on:
- General market knowledge for this sector
- Any news context available
- Acknowledge data limitations in your response

Do NOT make up specific prices or metrics.
State clearly that live data is temporarily unavailable.
"""




@function_tool
def get_current_date() -> str:
    """
    Get the current date and time in UTC.
    Call this at the start of every research session.
    Use this timestamp in all analysis and citations.

    Returns:
        Current date and time string
    """
    now = datetime.now(UTC)
    return f"Current date and time: {now.strftime('%B %d, %Y at %H:%M UTC')}"


@function_tool
async def get_news(ticker: str) -> str:
    """
    Get recent news headlines for a stock ticker.
    Uses Yahoo Finance RSS feed.
    Call this after get_stock_data.

    Args:
        ticker: Stock ticker symbol like NVDA or AAPL

    Returns:
        Recent news headlines as text
    """
    try:
        import xml.etree.ElementTree as ET
        import yfinance as yf

        ticker = ticker.upper().strip()

        # Get company name dynamically from yfinance
        # No hardcoding — works for any ticker
        try:
            stock        = yf.Ticker(ticker)
            info         = stock.info
            company_name = info.get('longName', '')
            short_name   = info.get('shortName', '')

            # Build keywords from real company data
            keywords = [ticker.lower()]

            # Add company name words (filter short words)
            for name in [company_name, short_name]:
                if name:
                    words = [
                        w.lower() for w in name.split()
                        if len(w) > 3  # skip "Inc", "Ltd", "Corp" etc
                        and w.lower() not in
                        ['inc.', 'inc', 'corp', 'corp.',
                         'ltd', 'ltd.', 'the', 'and']
                    ]
                    keywords.extend(words)

            # Remove duplicates
            keywords = list(set(keywords))

        except Exception:
            # If yfinance fails just use ticker
            keywords = [ticker.lower()]

        url = (
            f"https://feeds.finance.yahoo.com/rss/2.0/headline"
            f"?s={ticker}&region=US&lang=en-US"
        )

        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                }
            )

        if response.status_code != 200:
            return f"News unavailable for {ticker}"

        root    = ET.fromstring(response.text)
        channel = root.find('channel')
        items   = channel.findall('item') if channel else []

        if not items:
            return f"No recent news found for {ticker}"

        # Filter articles to company-relevant only
        relevant = []
        fallback  = []

        for item in items[:20]:
            title       = item.findtext('title', '')
            description = item.findtext('description', '')
            combined    = (title + ' ' + description).lower()

            pubdate = item.findtext('pubDate', '')
            if pubdate:
                try:
                    from email.utils import parsedate_to_datetime
                    dt      = parsedate_to_datetime(pubdate)
                    pubdate = dt.strftime('%b %d %Y')
                except Exception:
                    pubdate = pubdate[:16]

            link  = item.findtext('link', '')
            entry = f"- [{pubdate}] [{title}]({link})" if link else f"- [{pubdate}] {title}"
            fallback.append(entry)

            # Check relevance dynamically
            if any(kw in combined for kw in keywords):
                relevant.append(entry)

        # Use relevant if we found enough, else fallback
        if len(relevant) >= 2:
            headlines   = relevant[:5]
            source_note = f"Yahoo Finance RSS (filtered for {ticker})"
        else:
            headlines   = fallback[:5]
            source_note = f"Yahoo Finance RSS (broader results)"

        lines = [f"Latest news for {ticker} (Source: {source_note}):"]
        lines.extend(headlines)

        logger.info(
            f"News for {ticker}: {len(relevant)} relevant "
            f"of {len(fallback)} total"
        )

        return "\n".join(lines)

    except ET.ParseError as e:
        logger.error(f"RSS parse error for {ticker}: {e}")
        return f"Could not parse news for {ticker}"
    except Exception as e:
        logger.error(f"News error for {ticker}: {type(e).__name__}: {e}")
        return f"Could not fetch news for {ticker}: {str(e)}"

@function_tool
async def ingest_financial_document(content: str, topic: str) -> str:
    """
    Store financial research in the Alex knowledge base.
    Call this AFTER completing research to save findings.
    This makes the research searchable by other parts of Alex.

    Args:
        content: The complete research analysis text to store
        topic:   Short descriptive label e.g. "AVGO Analysis Jun 2026"

    Returns:
        Success or error message
    """
    api_endpoint = os.getenv("ALEX_API_ENDPOINT")
    api_key      = os.getenv("ALEX_API_KEY")
    ingest_url   = api_endpoint or ""
    apis = [
        f"Alex Ingest API ({ingest_url or 'not configured'})",
        "Aurora pgvector (research_vectors)",
        "SageMaker alex-embedding",
    ]
    import time as time_mod
    t0 = time_mod.monotonic()

    logger.info(f"Storing research — Topic: {topic}")
    logger.info(f"Content length: {len(content)} chars")
    logger.info(f"API endpoint configured: {bool(api_endpoint)}")

    payload = {"content": content, "topic": topic}
    try:
        from latency_tracker import get_tracker
        tracker = get_tracker()
        if tracker:
            if tracker.clerk_id:
                payload["user_id"] = tracker.clerk_id
            if tracker.session_id:
                payload["session_id"] = tracker.session_id
    except ImportError:
        pass

    if not api_endpoint or not api_key:
        record_tool("ingest_financial_document", success=False, error="API not configured", apis=apis)
        return "Error: ALEX_API_ENDPOINT or ALEX_API_KEY not configured"

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                api_endpoint,
                headers={
                    "Content-Type": "application/json",
                    "x-api-key":    api_key
                },
                json=payload
            )
            logger.info(f"Ingest response: {response.status_code}")

        ms = int((time_mod.monotonic() - t0) * 1000)
        if response.status_code == 200:
            logger.info(f"Successfully stored: {topic}")
            record_tool("ingest_financial_document", success=True, latency_ms=ms, apis=apis)
            record_api(f"Alex Ingest API ({ingest_url})", success=True, latency_ms=ms)
            return f"Successfully stored research for topic: {topic}"
        else:
            err = f"HTTP {response.status_code}"
            logger.error(f"Failed: {response.status_code} — {response.text}")
            record_tool("ingest_financial_document", success=False, error=err, latency_ms=ms, apis=apis)
            record_api(f"Alex Ingest API ({ingest_url})", success=False, error=err, latency_ms=ms)
            return f"Failed to store: {response.status_code} — {response.text}"

    except httpx.TimeoutException:
        logger.error("Timeout calling ingest API")
        record_tool("ingest_financial_document", success=False, error="Timeout 30s", apis=apis)
        record_api(f"Alex Ingest API ({ingest_url})", success=False, error="Timeout 30s")
        return "Error: Ingest API timed out after 30 seconds"

    except httpx.ConnectError as e:
        logger.error(f"Connection error: {e}")
        record_tool("ingest_financial_document", success=False, error=str(e)[:120], apis=apis)
        record_api(f"Alex Ingest API ({ingest_url})", success=False, error=str(e)[:120])
        return "Error: Could not connect to ingest API endpoint"

    except Exception as e:
        logger.error(f"Unexpected error: {type(e).__name__}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        record_tool("ingest_financial_document", success=False, error=str(e)[:120], apis=apis)
        return f"Error storing research: {type(e).__name__}: {str(e)}"