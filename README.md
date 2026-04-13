# NL2SQL Clinic Chatbot

An AI-powered Natural Language to SQL system built with **Vanna AI 2.0** and **FastAPI**. Users ask questions in plain English, the system generates or falls back to safe SQL, validates it, executes it against a clinic SQLite database, and returns structured results with optional Plotly charts.

## LLM Provider

This project uses **Google Gemini (`gemini-2.5-flash`)** through `GeminiLlmService`.

## Project Structure

```text
nl2sql_project/
├── setup_database.py
├── vanna_setup.py
├── memory_seed.py
├── seed_memory.py
├── fallback_sql.py
├── main.py
├── requirements.txt
├── README.md
├── RESULTS.md
└── clinic.db
```

## Setup

1. Create and activate a virtual environment:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

2. Install dependencies:

```powershell
pip install -r requirements.txt
```

3. Create a `.env` file and add your Gemini key:

```text
GOOGLE_API_KEY=your-key-here
```

4. Build the database:

```powershell
python setup_database.py
```

5. Seed agent memory:

```powershell
python seed_memory.py
```

6. Start the API server:

```powershell
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

Docs will be available at `http://127.0.0.1:8000/docs`.

## One-Liner

```powershell
pip install -r requirements.txt
python setup_database.py
python seed_memory.py
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

## Memory Seeding

`seed_memory.py` preloads **15 known-good question-to-SQL patterns** into `DemoAgentMemory` as successful `run_sql` tool usages. The FastAPI app also ensures those 15 patterns are loaded into the live agent process, so `/health` reports:

```json
{
  "status": "ok",
  "database": "connected",
  "agent_memory_items": 15
}
```

## API

### `POST /chat`

Request:

```json
{
  "question": "Show me the top 5 patients by total spending"
}
```

Response shape:

```json
{
  "message": "Found 5 results for: \"Show me the top 5 patients by total spending\"",
  "sql_query": "SELECT ...",
  "columns": ["first_name", "last_name", "total_spending"],
  "rows": [["John", "Smith", 4500], ["Jane", "Doe", 3200]],
  "row_count": 5,
  "chart": { "data": [], "layout": {} },
  "chart_type": "bar",
  "error": null
}
```

Example:

```powershell
curl -X POST http://127.0.0.1:8000/chat `
  -H "Content-Type: application/json" `
  -d "{\"question\":\"How many patients do we have?\"}"
```

### `GET /health`

```powershell
curl http://127.0.0.1:8000/health
```

## Architecture Overview

The app uses a **custom FastAPI endpoint layer** on top of a **Vanna 2.0 Agent**. The agent is initialized with:

- `GeminiLlmService`
- `ToolRegistry`
- `RunSqlTool`
- `VisualizeDataTool`
- `SaveQuestionToolArgsTool`
- `SearchSavedCorrectToolUsesTool`
- `DemoAgentMemory`
- `SqliteRunner`

For each `/chat` request, the system:

1. Validates input with Pydantic.
2. Checks the in-memory response cache.
3. Calls the Vanna agent to produce SQL.
4. Falls back to deterministic SQL for known clinic questions if the LLM is unavailable.
5. Validates SQL safety:
   - `SELECT` only
   - no dangerous keywords
   - no system-table access
6. Executes the SQL against `clinic.db`.
7. Returns rows, row count, and a Plotly chart when the result is chartable.

## SQL Validation and Error Handling

The app blocks unsafe SQL before execution and handles:

- invalid SQL generation
- database execution failures
- empty result sets
- upstream LLM/network failures
