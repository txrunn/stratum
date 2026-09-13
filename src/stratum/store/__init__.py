"""SQLite store: schema migrations, loaders, point-in-time query helpers.

See ARCHITECTURE.md "store/" for the two-clock discipline every table
follows, and HETERODOX_STRATEGIES.md for how macro_series / articles /
labor_activity_series feed the six heterodox signal studies.
"""

from stratum.store.connection import connect, migrate

__all__ = ["connect", "migrate"]
