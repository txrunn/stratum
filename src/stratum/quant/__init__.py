"""Pure functions over the store: composites, regimes, event conditioning.

No network, no LLM calls, no I/O beyond the database connection passed in.
Every function here is unit-testable against fixtures (see ARCHITECTURE.md
"quant/").
"""
