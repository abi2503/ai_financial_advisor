"""
Alex Trading Floor - Configurable Market Data Layer
Pluggable provider system - add sources via SSM
"""
import os
import json
import boto3
import logging
import urllib.request
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel
from enum import Enum

logger = logging.getLogger(__name__)
UTC    = timezone.utc
REGION = os.environ.get("AWS_REGION_NAME", "us-east-1")
ssm    = boto3.client("ssm", region_name=REGION)


class TechnicalSignal(str, Enum):
    STRONG_BUY  = "STRONG_BUY"
    BUY         = "BUY"
    NEUTRAL     = "NEUTRAL"
    SELL        = "SELL"
    STRONG_SELL = "STRONG_SELL"


class SentimentData(BaseModel):
    fear_greed_score:  Optional[float] = None
    analyst_rating:    Optional[str]   = None
    analyst_target:    Optional[float] = None
    analyst_count:     Optional[int]   = None
    short_interest:    Optional[float] = None
    insider_sentiment: Optional[str]   = None


class TechnicalData(BaseModel):
    rsi:               Optional[float]          = None
    macd_signal:       Optional[str]            = None
    above_50ma:        Optional[bool]           = None
    above_200ma:       Optional[bool]           = None
    volume_trend:      Optional[str]            = None
    bb_position:       Optional[str]            = None
    options_sentiment: Optional[str]            = None
    put_call_ratio:    Optional[float]          = None
    technical_signal:  Optional[TechnicalSignal] = None


class FundamentalData(BaseModel):
    pe_ratio:        Optional[float] = None
    forward_pe:      Optional[float] = None
    peg_ratio:       Optional[float] = None
    price_to_sales:  Optional[float] = None
    revenue_growth:  Optional[float] = None
    earnings_growth: Optional[float] = None
    profit_margin:   Optional[float] = None
    debt_to_equity:  Optional[float] = None
    free_cash_flow:  Optional[float] = None
    market_cap:      Optional[float] = None


class NewsItem(BaseModel):
    title:     str
    source:    str
    sentiment: Optional[str] = None
    date:      Optional[str] = None


class MarketData(BaseModel):
    ticker:       str
    price:        float
    change_pct:   float
    volume:       int
    week_52_high: Optional[float] = None
    week_52_low:  Optional[float] = None
    fundamentals: Optional[FundamentalData] = None
    technicals:   Optional[TechnicalData]   = None
    sentiment:    Optional[SentimentData]   = None
    news:         list[NewsItem]            = []
    sources_used: list[str]                = []
    data_quality: float                    = 0.0
    fetched_at:   str                      = ""


def get_enabled_sources() -> dict:
    try:
        prefix = "/alex/trading/data_sources"
        result = ssm.get_parameters_by_path(Path=prefix, Recursive=True)
        return {p["Name"].replace(f"{prefix}/", ""): p["Value"]
                for p in result.get("Parameters", [])}
    except Exception:
        return {"yfinance/enabled": "true", "fear_greed/enabled": "true"}


def rsi_to_signal(rsi: Optional[float]) -> Optional[str]:
    if rsi is None:
        return None
    if rsi >= 70:
        return "STRONG_SELL"
    if rsi >= 60:
        return "SELL"
    if rsi <= 30:
        return "STRONG_BUY"
    if rsi <= 40:
        return "BUY"
    return "NEUTRAL"


def fetch_yfinance(ticker: str) -> dict:
    try:
        import yfinance as yf
        stock = yf.Ticker(ticker)
        info  = stock.info
        hist  = stock.history(period="5d")
        if len(hist) >= 2:
            prev = float(hist["Close"].iloc[-2])
            curr = float(hist["Close"].iloc[-1])
            chg  = ((curr - prev) / prev) * 100
            vol  = int(hist["Volume"].iloc[-1])
        else:
            curr = float(info.get("currentPrice", info.get("regularMarketPrice", 0)) or 0)
            chg  = float(info.get("regularMarketChangePercent", 0) or 0)
            vol  = int(info.get("volume", 0) or 0)

        hist_long = stock.history(period="1y")
        above_50  = None
        above_200 = None
        rsi       = None

        if len(hist_long) >= 50:
            ma50     = hist_long["Close"].rolling(50).mean().iloc[-1]
            above_50 = curr > float(ma50)
        if len(hist_long) >= 200:
            ma200     = hist_long["Close"].rolling(200).mean().iloc[-1]
            above_200 = curr > float(ma200)
        if len(hist_long) >= 15:
            delta = hist_long["Close"].diff()
            gain  = delta.clip(lower=0).rolling(14).mean()
            loss  = (-delta.clip(upper=0)).rolling(14).mean()
            rs    = gain / loss.replace(0, 1e-10)
            rsi   = float(100 - (100 / (1 + rs.iloc[-1])))

        news_items = []
        try:
            for n in (stock.news or [])[:5]:
                news_items.append({
                    "title":  n.get("title", "")[:100],
                    "source": n.get("publisher", "Yahoo Finance"),
                    "date":   str(n.get("providerPublishTime", ""))
                })
        except Exception:
            pass

        return {
            "price":        round(curr, 2),
            "change_pct":   round(chg, 2),
            "volume":       vol,
            "week_52_high": info.get("fiftyTwoWeekHigh"),
            "week_52_low":  info.get("fiftyTwoWeekLow"),
            "fundamentals": {
                "pe_ratio":        info.get("trailingPE"),
                "forward_pe":      info.get("forwardPE"),
                "peg_ratio":       info.get("pegRatio"),
                "price_to_sales":  info.get("priceToSalesTrailing12Months"),
                "revenue_growth":  info.get("revenueGrowth"),
                "earnings_growth": info.get("earningsGrowth"),
                "profit_margin":   info.get("profitMargins"),
                "debt_to_equity":  info.get("debtToEquity"),
                "free_cash_flow":  info.get("freeCashflow"),
                "market_cap":      info.get("marketCap"),
            },
            "technicals": {
                "rsi":             round(rsi, 1) if rsi else None,
                "above_50ma":      above_50,
                "above_200ma":     above_200,
                "technical_signal": rsi_to_signal(rsi)
            },
            "sentiment": {
                "analyst_rating": (info.get("recommendationKey") or "").upper(),
                "analyst_target": info.get("targetMeanPrice"),
                "analyst_count":  info.get("numberOfAnalystOpinions"),
            },
            "news":   news_items,
            "source": "yfinance"
        }
    except Exception as e:
        logger.error(f"yfinance error {ticker}: {e}")
        return {}


def fetch_fear_greed(ticker: str) -> dict:
    try:
        url = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        r   = urllib.request.urlopen(req, timeout=5)
        data = json.loads(r.read())
        score = data.get("fear_and_greed", {}).get("score", 50)
        return {"sentiment": {"fear_greed_score": float(score)}, "source": "fear_greed"}
    except Exception as e:
        logger.warning(f"Fear&Greed error: {e}")
        return {}


def fetch_polygon(ticker: str) -> dict:
    api_key = os.environ.get("POLYGON_API_KEY", "")
    if not api_key:
        return {}
    try:
        url  = f"https://api.polygon.io/v3/snapshot/options/{ticker}?limit=10&apiKey={api_key}"
        r    = urllib.request.urlopen(url, timeout=10)
        data = json.loads(r.read())
        puts  = sum(1 for x in data.get("results", [])
                   if x.get("details", {}).get("contract_type") == "put")
        calls = sum(1 for x in data.get("results", [])
                   if x.get("details", {}).get("contract_type") == "call")
        pc    = puts / max(calls, 1)
        return {
            "technicals": {
                "put_call_ratio":    round(pc, 2),
                "options_sentiment": "BEARISH" if pc > 1.2 else "BULLISH" if pc < 0.8 else "NEUTRAL"
            },
            "source": "polygon"
        }
    except Exception as e:
        logger.warning(f"Polygon error: {e}")
        return {}


def fetch_alpha_vantage(ticker: str) -> dict:
    api_key = os.environ.get("ALPHA_VANTAGE_KEY", "")
    if not api_key:
        return {}
    try:
        url  = f"https://www.alphavantage.co/query?function=OVERVIEW&symbol={ticker}&apikey={api_key}"
        r    = urllib.request.urlopen(url, timeout=10)
        data = json.loads(r.read())
        return {
            "fundamentals": {
                "pe_ratio":       float(data.get("PERatio", 0) or 0) or None,
                "peg_ratio":      float(data.get("PEGRatio", 0) or 0) or None,
                "profit_margin":  float(data.get("ProfitMargin", 0) or 0) or None,
                "debt_to_equity": float(data.get("DebtToEquityRatio", 0) or 0) or None,
            },
            "source": "alpha_vantage"
        }
    except Exception as e:
        logger.warning(f"Alpha Vantage error: {e}")
        return {}


PROVIDERS = {
    "yfinance":      (fetch_yfinance,    True),
    "fear_greed":    (fetch_fear_greed,  True),
    "polygon":       (fetch_polygon,     False),
    "alpha_vantage": (fetch_alpha_vantage, False),
}


def deep_merge(base: dict, update: dict) -> dict:
    result = base.copy()
    for k, v in update.items():
        if k == "source":
            existing = result.get("sources_used", [])
            if v not in existing:
                existing.append(v)
            result["sources_used"] = existing
        elif isinstance(v, dict) and k in result and isinstance(result[k], dict):
            result[k] = deep_merge(result[k], v)
        elif v is not None:
            result[k] = v
    return result


def get_market_data(ticker: str) -> MarketData:
    config = get_enabled_sources()
    merged = {
        "ticker": ticker, "price": 0, "change_pct": 0,
        "volume": 0, "sources_used": [],
        "fetched_at": datetime.now(UTC).isoformat()
    }

    for name, (fn, default_on) in PROVIDERS.items():
        enabled = config.get(f"{name}/enabled", "true" if default_on else "false")
        if enabled.lower() != "true":
            continue
        try:
            print(f"  [{name}] fetching {ticker}...")
            data = fn(ticker)
            if data:
                merged = deep_merge(merged, data)
        except Exception as e:
            logger.warning(f"Provider {name} error: {e}")

    quality_checks = [
        merged.get("fundamentals", {}).get("pe_ratio"),
        merged.get("technicals", {}).get("rsi"),
        merged.get("sentiment", {}).get("analyst_rating"),
        merged.get("sentiment", {}).get("fear_greed_score"),
        len(merged.get("news", [])) > 0,
    ]
    quality = sum(1 for x in quality_checks if x) / len(quality_checks)
    merged["data_quality"] = round(quality, 2)

    try:
        fund_raw = merged.get("fundamentals")
        tech_raw = merged.get("technicals")
        sent_raw = merged.get("sentiment")
        news_raw = merged.get("news", [])

        return MarketData(
            ticker       = ticker,
            price        = merged.get("price", 0),
            change_pct   = merged.get("change_pct", 0),
            volume       = merged.get("volume", 0),
            week_52_high = merged.get("week_52_high"),
            week_52_low  = merged.get("week_52_low"),
            fundamentals = FundamentalData(**fund_raw) if fund_raw else None,
            technicals   = TechnicalData(**tech_raw)   if tech_raw else None,
            sentiment    = SentimentData(**sent_raw)    if sent_raw else None,
            news         = [NewsItem(**n) if isinstance(n, dict) else n
                           for n in news_raw],
            sources_used = merged.get("sources_used", []),
            data_quality = merged.get("data_quality", 0),
            fetched_at   = merged.get("fetched_at", "")
        )
    except Exception as e:
        logger.error(f"MarketData build error: {e}")
        return MarketData(
            ticker=ticker, price=merged.get("price", 0),
            change_pct=merged.get("change_pct", 0),
            volume=merged.get("volume", 0)
        )


def enable_source(name: str, api_key: str = ""):
    ssm.put_parameter(
        Name=f"/alex/trading/data_sources/{name}/enabled",
        Value="true", Type="String", Overwrite=True
    )
    if api_key:
        ssm.put_parameter(
            Name=f"/alex/trading/data_sources/{name}/api_key",
            Value=api_key, Type="SecureString", Overwrite=True
        )
    print(f"Enabled: {name}")


def disable_source(name: str):
    ssm.put_parameter(
        Name=f"/alex/trading/data_sources/{name}/enabled",
        Value="false", Type="String", Overwrite=True
    )
    print(f"Disabled: {name}")
