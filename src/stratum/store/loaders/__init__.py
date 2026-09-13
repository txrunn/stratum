"""Raw JSON (from data/raw/**) → normalized store rows.

Each loader is a pure function: (connection, raw file path) -> rows inserted.
No network, no MCP calls — the agent already wrote the raw JSON per
ARCHITECTURE.md's ingestion boundary. Loaders are tested entirely offline
against fixtures in tests/store/fixtures/data/raw/, which mirror the real
data/raw/ shape exactly.
"""
