"""
Tools available to the Alex research agent.
Hybrid approach: API for structured data, Playwright for context.
"""
import os
import httpx
import logging
from agents import function_tool
from datetime import datetime, UTC

logger = logging.getLogger(__name__)


@function_tool
async def get_stock_data(ticker: str) -> str:
    """
    Get real-time stock data for a ticker symbol via Yahoo Finance API.
    Use this for ALL financial metrics — prices, ratios, market cap.
    This is MORE reliable than browser scraping for structured data.
    ALWAYS call this before browser tools when researching a stock.

    Args:
        ticker: Stock ticker symbol e.g. AVGO, IBM, NVDA, AAPL

    Returns:
        Current stock data as formatted string with source citation
    """
    try:
        import yfinance as yf

        stock = yf.Ticker(ticker.upper().strip())
        info  = stock.info

        # Extract key metrics safely
        price     = info.get('currentPrice') or info.get('regularMarketPrice', 'N/A')
        mkt_cap   = info.get('marketCap', 'N/A')
        pe_ratio  = info.get('trailingPE', 'N/A')
        fwd_pe    = info.get('forwardPE', 'N/A')
        div_yield = info.get('dividendYield', 'N/A')
        week_high = info.get('fiftyTwoWeekHigh', 'N/A')
        week_low  = info.get('fiftyTwoWeekLow', 'N/A')
        revenue   = info.get('totalRevenue', 'N/A')
        margins   = info.get('profitMargins', 'N/A')
        name      = info.get('longName', ticker)
        sector    = info.get('sector', 'N/A')
        analyst   = info.get('recommendationKey', 'N/A')
        target    = info.get('targetMeanPrice', 'N/A')

        # Format large numbers
        if isinstance(mkt_cap, (int, float)):
            mkt_cap = f"${mkt_cap/1e9:.2f}B"
        if isinstance(revenue, (int, float)):
            revenue = f"${revenue/1e9:.2f}B"
        if isinstance(div_yield, float):
            div_yield = f"{div_yield*100:.2f}%"
        if isinstance(margins, float):
            margins = f"{margins*100:.2f}%"
        if isinstance(pe_ratio, float):
            pe_ratio = f"{pe_ratio:.2f}x"
        if isinstance(fwd_pe, float):
            fwd_pe = f"{fwd_pe:.2f}x"

        timestamp = datetime.now(UTC).strftime('%B %d, %Y at %H:%M UTC')

        result = f"""
═══════════════════════════════════════
{name} ({ticker.upper()}) — Live Data
Retrieved: {timestamp}
Source: Yahoo Finance API (yfinance library)
═══════════════════════════════════════
Current Price:      ${price}
Market Cap:         {mkt_cap}
Sector:             {sector}
P/E Ratio:          {pe_ratio}
Forward P/E:        {fwd_pe}
Dividend Yield:     {div_yield}
Profit Margins:     {margins}
52-Week High:       ${week_high}
52-Week Low:        ${week_low}
Annual Revenue:     {revenue}
Analyst Rating:     {analyst}
Analyst Target:     ${target}
═══════════════════════════════════════
NOTE: This data is from Yahoo Finance API.
      Prices are real-time/delayed 15 min.
      Do NOT override with memory estimates.
"""
        logger.info(f"Successfully fetched {ticker}: ${price}")
        return result

    except ImportError:
        return "Error: yfinance not installed. Use browser tools instead."
    except Exception as e:
        logger.error(f"Error fetching {ticker}: {type(e).__name__}: {e}")
        return f"Error fetching data for {ticker}: {str(e)}"




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

            entry = f"- [{pubdate}] {title}"
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

    logger.info(f"Storing research — Topic: {topic}")
    logger.info(f"Content length: {len(content)} chars")
    logger.info(f"API endpoint configured: {bool(api_endpoint)}")

    if not api_endpoint or not api_key:
        return "Error: ALEX_API_ENDPOINT or ALEX_API_KEY not configured"

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                api_endpoint,
                headers={
                    "Content-Type": "application/json",
                    "x-api-key":    api_key
                },
                json={
                    "content": content,
                    "topic":   topic
                }
            )
            logger.info(f"Ingest response: {response.status_code}")

        if response.status_code == 200:
            logger.info(f"Successfully stored: {topic}")
            return f"Successfully stored research for topic: {topic}"
        else:
            logger.error(f"Failed: {response.status_code} — {response.text}")
            return f"Failed to store: {response.status_code} — {response.text}"

    except httpx.TimeoutException:
        logger.error("Timeout calling ingest API")
        return "Error: Ingest API timed out after 30 seconds"

    except httpx.ConnectError as e:
        logger.error(f"Connection error: {e}")
        return "Error: Could not connect to ingest API endpoint"

    except Exception as e:
        logger.error(f"Unexpected error: {type(e).__name__}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return f"Error storing research: {type(e).__name__}: {str(e)}"