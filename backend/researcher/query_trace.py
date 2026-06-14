"""
Per-request trace — tools, MCP servers, and external APIs hit during a query.

Each entry records pass/fail so /observe can validate every external call.

Future addons:
  record_tool(name, success=True/False, error="...", apis=[...])
  record_api(name, success=True/False, url="...")
  record_mcp(name, success=True/False)
"""
from __future__ import annotations

import time
from contextvars import ContextVar
from dataclasses import dataclass, field, asdict
from typing import Optional

_trace_var: ContextVar[Optional["QueryTrace"]] = ContextVar("query_trace", default=None)


@dataclass
class ToolHit:
    name:       str
    success:    bool  = True
    error:      str   = ""
    latency_ms: int   = 0


@dataclass
class ApiHit:
    name:       str
    url:        str   = ""
    latency_ms: int   = 0
    success:    bool  = True
    error:      str   = ""


@dataclass
class McpHit:
    name:    str
    success: bool = True
    error:   str  = ""


@dataclass
class QueryTrace:
    tools:        list[ToolHit] = field(default_factory=list)
    mcp_servers:  list[McpHit]  = field(default_factory=list)
    apis:         list[ApiHit]   = field(default_factory=list)
    _api_started: dict[str, float] = field(default_factory=dict, repr=False)

    def _find_tool(self, name: str) -> Optional[ToolHit]:
        for t in self.tools:
            if t.name == name:
                return t
        return None

    def _find_api(self, name: str, url: str) -> Optional[ApiHit]:
        for a in self.apis:
            if a.name == name and a.url == url:
                return a
        return None

    def record_tool(
        self,
        name:       str,
        success:    bool = True,
        error:      str  = "",
        latency_ms: int  = 0,
        apis:       list[str] | None = None,
    ) -> None:
        hit = self._find_tool(name)
        if hit:
            hit.success    = success
            hit.error      = error[:200] if error else ""
            hit.latency_ms = latency_ms or hit.latency_ms
        else:
            self.tools.append(ToolHit(
                name=name, success=success,
                error=error[:200] if error else "",
                latency_ms=latency_ms,
            ))
        for api in apis or []:
            self.record_api(api, success=success, error=error)

    def record_mcp(self, name: str, success: bool = True, error: str = "") -> None:
        for m in self.mcp_servers:
            if m.name == name:
                m.success = success
                m.error   = error[:200] if error else ""
                return
        self.mcp_servers.append(McpHit(
            name=name, success=success,
            error=error[:200] if error else "",
        ))

    def start_api(self, name: str, url: str = "") -> None:
        self._api_started[f"{name}|{url}"] = time.monotonic()

    def record_api(
        self,
        name:       str,
        url:        str  = "",
        success:    bool = True,
        error:      str  = "",
        latency_ms: int  = 0,
    ) -> None:
        key = f"{name}|{url}"
        if latency_ms == 0 and key in self._api_started:
            latency_ms = int((time.monotonic() - self._api_started.pop(key)) * 1000)

        hit = self._find_api(name, url)
        if hit:
            hit.success    = success
            hit.error      = error[:200] if error else ""
            hit.latency_ms = latency_ms or hit.latency_ms
        else:
            self.apis.append(ApiHit(
                name=name, url=url, latency_ms=latency_ms,
                success=success, error=error[:200] if error else "",
            ))

    def end_api(self, name: str, url: str = "", success: bool = True, error: str = "") -> None:
        self.record_api(name, url=url, success=success, error=error)

    def to_dict(self) -> dict:
        return {
            "tools": [asdict(t) for t in self.tools],
            "mcp_servers": [asdict(m) for m in self.mcp_servers],
            "data_sources": [asdict(a) for a in self.apis],
        }

    def pass_fail_summary(self) -> dict:
        tools_ok = sum(1 for t in self.tools if t.success)
        apis_ok  = sum(1 for a in self.apis if a.success)
        mcps_ok  = sum(1 for m in self.mcp_servers if m.success)
        return {
            "tools_passed": tools_ok,
            "tools_failed": len(self.tools) - tools_ok,
            "apis_passed":  apis_ok,
            "apis_failed":  len(self.apis) - apis_ok,
            "mcps_passed":  mcps_ok,
            "mcps_failed":  len(self.mcp_servers) - mcps_ok,
        }


def activate_trace(trace: QueryTrace):
    return _trace_var.set(trace)


def deactivate_trace(token) -> None:
    _trace_var.reset(token)


def get_trace() -> Optional[QueryTrace]:
    return _trace_var.get()


def record_tool(
    name:       str,
    success:    bool = True,
    error:      str  = "",
    latency_ms: int  = 0,
    apis:       list[str] | None = None,
) -> None:
    trace = get_trace()
    if trace:
        trace.record_tool(name, success=success, error=error, latency_ms=latency_ms, apis=apis)


def record_mcp(name: str, success: bool = True, error: str = "") -> None:
    trace = get_trace()
    if trace:
        trace.record_mcp(name, success=success, error=error)


def record_api(
    name:       str,
    url:        str  = "",
    success:    bool = True,
    error:      str  = "",
    latency_ms: int  = 0,
) -> None:
    trace = get_trace()
    if trace:
        trace.record_api(name, url=url, success=success, error=error, latency_ms=latency_ms)
