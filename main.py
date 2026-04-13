"""
main.py
FastAPI application for the NL2SQL Clinic Chatbot.

Endpoints:
  POST /chat    – Ask a natural-language question, get SQL + results + chart
  GET  /health  – Health check

Run:
    uvicorn main:app --port 8000 --reload
"""

import re
import time
import uuid
import logging
import sqlite3
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from vanna.core.user import RequestContext

from fallback_sql import get_fallback_sql
from vanna_setup import get_agent, ensure_agent_seeded, DB_PATH

# ─── Logging ──────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# ─── App ──────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="NL2SQL Clinic Chatbot",
    description="Ask questions about the clinic database in plain English.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Simple in-memory cache ───────────────────────────────────────────────────

_CACHE: dict[str, dict] = {}   # question.lower() → response dict
CACHE_MAX = 200


# ─── SQL Validation ───────────────────────────────────────────────────────────

# Patterns that indicate dangerous or write operations
_DANGEROUS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|EXEC|EXECUTE|"
    r"GRANT|REVOKE|SHUTDOWN|xp_|sp_)\b",
    re.IGNORECASE,
)
_SYSTEM_TABLES = re.compile(
    r"\bsqlite_master\b|\bsqlite_sequence\b|\binformation_schema\b",
    re.IGNORECASE,
)
_MUST_BE_SELECT = re.compile(r"^\s*SELECT\b", re.IGNORECASE)


def validate_sql(sql: str) -> tuple[bool, str]:
    """
    Returns (is_valid, reason).
    SQL must be a SELECT statement with no dangerous keywords or system table access.
    """
    if not _MUST_BE_SELECT.match(sql):
        return False, "Only SELECT queries are permitted."
    if _DANGEROUS.search(sql):
        return False, "Query contains disallowed keywords."
    if _SYSTEM_TABLES.search(sql):
        return False, "Access to system tables is not permitted."
    return True, "ok"


# ─── Request / Response models ────────────────────────────────────────────────

class ChatRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=3,
        max_length=500,
        example="Show me the top 5 patients by total spending",
    )


class ChatResponse(BaseModel):
    message: str
    sql_query: str | None = None
    columns: list[str] | None = None
    rows: list[list[Any]] | None = None
    row_count: int | None = None
    chart: dict | None = None
    chart_type: str | None = None
    error: str | None = None


# ─── Helper: run SQL directly on clinic.db ────────────────────────────────────

def execute_sql(sql: str) -> tuple[list[str], list[list]]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.execute(sql)
        rows_raw = cur.fetchall()
        columns  = [desc[0] for desc in cur.description] if cur.description else []
        rows     = [list(r) for r in rows_raw]
        return columns, rows
    finally:
        conn.close()


# ─── Helper: extract SQL from agent response ──────────────────────────────────

def extract_sql(agent_response: str) -> str | None:
    """Pull the first SQL code block from a markdown-style response."""
    # ```sql``` and ```sqlite``` fences are both common model outputs.
    block = re.search(
        r"```(?:sqlite|sql)?(?:\r?\n|\s)+([\s\S]+?)```",
        agent_response,
        re.IGNORECASE,
    )
    if block:
        return block.group(1).strip()
    # Bare SELECT …; on a single logical line
    bare = re.search(r"(SELECT[\s\S]+?;)", agent_response, re.IGNORECASE)
    if bare:
        return bare.group(1).strip()
    return None


# ─── Helper: build a simple Plotly-compatible chart spec ─────────────────────

def build_chart(columns: list[str], rows: list[list]) -> tuple[dict | None, str | None]:
    """
    Returns (plotly_dict, chart_type) or (None, None) if not chartable.
    Tries: bar chart for ≤20 rows with a label + numeric column.
    """
    if not rows or len(columns) < 2:
        return None, None
    try:
        import plotly.graph_objects as go
        import json

        numeric_idx = None
        for idx in range(len(columns) - 1, 0, -1):
            try:
                values = [float(row[idx]) for row in rows]
                numeric_idx = idx
                break
            except (TypeError, ValueError):
                continue

        if numeric_idx is None:
            return None, None

        label_parts = max(1, numeric_idx)
        labels = [" ".join(str(row[i]) for i in range(label_parts)) for row in rows]
        label_col = " / ".join(columns[:label_parts])
        num_col = columns[numeric_idx]

        fig = go.Figure(
            go.Bar(x=labels, y=values, name=num_col)
        )
        fig.update_layout(
            title=f"{num_col} by {label_col}",
            xaxis_title=label_col,
            yaxis_title=num_col,
            template="plotly_white",
        )
        chart_dict = json.loads(fig.to_json())
        return chart_dict, "bar"
    except Exception:
        return None, None


# ─── /chat endpoint ───────────────────────────────────────────────────────────

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, raw_request: Request):
    question = request.question.strip()
    cache_key = question.lower()

    # Check cache
    if cache_key in _CACHE:
        log.info("Cache hit: %s", question)
        return _CACHE[cache_key]

    log.info("Question: %s", question)
    t0 = time.perf_counter()

    agent = get_agent()
    await ensure_agent_seeded(agent)

    try:
        request_context = RequestContext(
            headers=dict(raw_request.headers),
            cookies=raw_request.cookies,
            query_params=dict(raw_request.query_params),
            remote_addr=raw_request.client.host if raw_request.client else None,
        )
        agent_reply = await _collect_agent_reply(agent, request_context, question)
    except Exception as exc:
        log.error("Agent error: %s", exc)
        fallback_sql = get_fallback_sql(question)
        if not fallback_sql:
            raise HTTPException(status_code=500, detail=f"Agent error: {exc}")
        log.warning("Using fallback SQL for question after agent failure: %s", question)
        agent_reply = f"```sql\n{fallback_sql}\n```"

    sql = extract_sql(agent_reply)

    if not sql:
        # Agent answered without SQL (e.g. a clarification question or prose answer)
        fallback_sql = get_fallback_sql(question)
        if fallback_sql:
            sql = fallback_sql
        else:
            result = ChatResponse(message=agent_reply or "I could not generate SQL for that question.")
            _cache_put(cache_key, result)
            return result

    # Validate SQL
    valid, reason = validate_sql(sql)
    if not valid:
        log.warning("SQL validation failed: %s  →  %s", sql, reason)
        result = ChatResponse(
            message=f"I generated a query but it was blocked for safety: {reason}",
            sql_query=sql,
            error=reason,
        )
        return result

    # Execute SQL
    try:
        columns, rows = execute_sql(sql)
    except Exception as exc:
        log.error("DB execution error: %s", exc)
        result = ChatResponse(
            message="The query ran into a database error.",
            sql_query=sql,
            error=str(exc),
        )
        return result

    if not rows:
        result = ChatResponse(
            message="No data found for your question.",
            sql_query=sql,
            columns=columns,
            rows=[],
            row_count=0,
        )
        _cache_put(cache_key, result)
        return result

    # Build chart
    chart, chart_type = build_chart(columns, rows)

    # Build a friendly summary message
    summary = _build_summary(question, columns, rows)

    elapsed = time.perf_counter() - t0
    log.info("Answered in %.2fs | rows=%d", elapsed, len(rows))

    result = ChatResponse(
        message=summary,
        sql_query=sql,
        columns=columns,
        rows=rows,
        row_count=len(rows),
        chart=chart,
        chart_type=chart_type,
    )
    _cache_put(cache_key, result)
    return result


def _build_summary(question: str, columns: list[str], rows: list[list]) -> str:
    n = len(rows)
    if n == 1 and len(columns) == 1:
        return f"Result: {rows[0][0]}"
    return f"Found {n} result{'s' if n != 1 else ''} for: \"{question}\""


def _cache_put(key: str, value: ChatResponse):
    if len(_CACHE) >= CACHE_MAX:
        # Evict oldest entry
        oldest = next(iter(_CACHE))
        del _CACHE[oldest]
    _CACHE[key] = value.model_dump()


async def _collect_agent_reply(agent: Any, request_context: RequestContext, question: str) -> str:
    parts: list[str] = []
    conversation_id = str(uuid.uuid4())

    async for component in agent.send_message(
        request_context=request_context,
        message=question,
        conversation_id=conversation_id,
    ):
        text = _component_text(component)
        if text:
            parts.append(text)

    return "\n".join(parts).strip()


def _component_text(component: Any) -> str:
    simple = getattr(component, "simple_component", None)
    if simple and getattr(simple, "text", None):
        return simple.text

    rich = getattr(component, "rich_component", None)
    if rich and getattr(rich, "content", None):
        return rich.content

    return ""


# ─── /health endpoint ─────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    # Check DB connection
    db_status = "connected"
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("SELECT 1")
        conn.close()
    except Exception as exc:
        db_status = f"error: {exc}"

    # Count memory items
    try:
        agent = get_agent()
        await ensure_agent_seeded(agent)
        memory = getattr(agent, "agent_memory", None)
        memory_items = len(getattr(memory, "_memories", [])) if memory else "unknown"
    except Exception:
        memory_items = "unknown"

    return {
        "status": "ok",
        "database": db_status,
        "agent_memory_items": memory_items,
    }


# ─── Global exception handler ─────────────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    log.error("Unhandled exception: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"error": "An unexpected error occurred.", "detail": str(exc)},
    )
