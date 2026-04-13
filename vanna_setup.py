"""
vanna_setup.py
Assignment-compliant Vanna 2.0 agent setup.
"""

import os
import sqlite3
from functools import lru_cache
from typing import Optional

from dotenv import load_dotenv

from memory_seed import preload_agent_memory
from vanna import Agent, AgentConfig
from vanna.core.registry import ToolRegistry
from vanna.core.system_prompt import SystemPromptBuilder
from vanna.core.user import RequestContext, User, UserResolver
from vanna.integrations.google import GeminiLlmService
from vanna.integrations.local.agent_memory import DemoAgentMemory
from vanna.integrations.sqlite import SqliteRunner
from vanna.tools import RunSqlTool, VisualizeDataTool
from vanna.tools.agent_memory import (
    SaveQuestionToolArgsTool,
    SearchSavedCorrectToolUsesTool,
)

load_dotenv()

DB_PATH = os.getenv("DB_PATH", "clinic.db")


class DefaultUserResolver(UserResolver):
    async def resolve_user(self, context: RequestContext) -> User:
        return User(id="default", username="clinic-user")


class ClinicSystemPromptBuilder(SystemPromptBuilder):
    def __init__(self, db_path: str):
        self.db_path = db_path

    async def build_system_prompt(self, user: User, tools: list) -> Optional[str]:
        tool_names = ", ".join(tool.name for tool in tools) if tools else "none"
        return (
            "You are a helpful clinic data analyst.\n"
            "You work with a SQLite clinic database.\n"
            "Generate exactly one SQLite SELECT query that answers the user's question.\n"
            "Return only a SQL code block.\n"
            "Never write INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, PRAGMA, or system-table queries.\n"
            f"Available tools: {tool_names}\n\n"
            f"{_schema_prompt(self.db_path)}"
        )


def _schema_prompt(db_path: str) -> str:
    conn = sqlite3.connect(db_path)
    try:
        tables = conn.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type = 'table' AND name NOT LIKE 'sqlite_%' "
            "ORDER BY name"
        ).fetchall()

        schema_lines = []
        for (table_name,) in tables:
            columns = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
            column_defs = ", ".join(f"{column[1]} {column[2]}" for column in columns)
            schema_lines.append(f"- {table_name}({column_defs})")
        return "Schema:\n" + "\n".join(schema_lines)
    finally:
        conn.close()


def _build_tool_registry(sql_runner: SqliteRunner) -> ToolRegistry:
    registry = ToolRegistry()
    registry.register_local_tool(RunSqlTool(sql_runner=sql_runner), access_groups=[])
    registry.register_local_tool(VisualizeDataTool(), access_groups=[])
    registry.register_local_tool(SaveQuestionToolArgsTool(), access_groups=[])
    registry.register_local_tool(SearchSavedCorrectToolUsesTool(), access_groups=[])
    return registry


@lru_cache(maxsize=1)
def get_agent() -> Agent:
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise EnvironmentError("GOOGLE_API_KEY not set")

    llm_service = GeminiLlmService(api_key=api_key, model="gemini-2.5-flash")
    memory = DemoAgentMemory()
    sql_runner = SqliteRunner(database_path=DB_PATH)
    registry = _build_tool_registry(sql_runner)
    user_resolver = DefaultUserResolver()
    prompt_builder = ClinicSystemPromptBuilder(DB_PATH)
    config = AgentConfig(stream_responses=False, include_thinking_indicators=False)

    return Agent(
        llm_service=llm_service,
        tool_registry=registry,
        user_resolver=user_resolver,
        agent_memory=memory,
        config=config,
        system_prompt_builder=prompt_builder,
    )


async def ensure_agent_seeded(agent: Agent) -> None:
    memory = agent.agent_memory
    if getattr(memory, "_assignment_seeded", False):
        return

    await preload_agent_memory(
        memory, conversation_id="startup-seed", request_id="startup-seed"
    )
    setattr(memory, "_assignment_seeded", True)


if __name__ == "__main__":
    get_agent()
    print("Vanna agent initialized successfully.")
