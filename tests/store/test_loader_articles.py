from stratum.store.loaders.articles import load_articles
from stratum.store.pit import articles_asof
from tests.store.conftest import FIXTURES

WSJ_FIXTURE = FIXTURES / "rss" / "feeds" / "wsj_markets" / "2026-09-04.json"
JACOBIN_FIXTURE = FIXTURES / "rss" / "feeds" / "jacobin" / "2026-09-04.json"


def test_load_articles_row_count(conn):
    inserted = load_articles(conn, WSJ_FIXTURE)
    assert inserted == 2
    row_count = conn.execute("SELECT COUNT(*) AS n FROM articles").fetchone()["n"]
    assert row_count == 2


def test_load_articles_sets_outlet_class_and_knowledge_time(conn):
    load_articles(conn, WSJ_FIXTURE)
    row = conn.execute(
        "SELECT outlet_class, knowledge_time, published_at FROM articles LIMIT 1"
    ).fetchone()
    assert row["outlet_class"] == "capital"
    assert row["knowledge_time"] == "2026-09-04T18:40:00Z"
    # knowledge_time (fetch) is after published_at for this fixture, as expected.
    assert row["knowledge_time"] >= row["published_at"]


def test_load_articles_is_idempotent(conn):
    load_articles(conn, WSJ_FIXTURE)
    load_articles(conn, WSJ_FIXTURE)
    row_count = conn.execute("SELECT COUNT(*) AS n FROM articles").fetchone()["n"]
    assert row_count == 2


def test_article_id_stable_across_reloads(conn):
    load_articles(conn, WSJ_FIXTURE)
    ids_first = {row["article_id"] for row in conn.execute("SELECT article_id FROM articles")}
    load_articles(conn, WSJ_FIXTURE)
    ids_second = {row["article_id"] for row in conn.execute("SELECT article_id FROM articles")}
    assert ids_first == ids_second


def test_articles_asof_filters_by_knowledge_time(conn):
    load_articles(conn, WSJ_FIXTURE)
    load_articles(conn, JACOBIN_FIXTURE)

    # Jacobin's knowledge_time (19:10) is after this window; WSJ's (18:40) is inside it.
    rows = articles_asof(conn, as_of_start="2026-09-04T00:00:00Z", as_of_end="2026-09-04T19:00:00Z")
    sources = {row["source"] for row in rows}
    assert sources == {"wsj_markets"}


def test_articles_asof_filters_by_outlet_class(conn):
    load_articles(conn, WSJ_FIXTURE)
    load_articles(conn, JACOBIN_FIXTURE)

    rows = articles_asof(
        conn,
        as_of_start="2026-09-04T00:00:00Z",
        as_of_end="2026-09-05T00:00:00Z",
        outlet_class="labor",
    )
    assert len(rows) == 1
    assert rows[0]["source"] == "jacobin"


def test_articles_asof_filters_by_source_list(conn):
    load_articles(conn, WSJ_FIXTURE)
    load_articles(conn, JACOBIN_FIXTURE)

    rows = articles_asof(
        conn,
        as_of_start="2026-09-04T00:00:00Z",
        as_of_end="2026-09-05T00:00:00Z",
        source_in=["wsj_markets"],
    )
    assert len(rows) == 2
    assert all(row["source"] == "wsj_markets" for row in rows)
