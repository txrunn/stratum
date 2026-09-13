-- News/think-tank articles and their versioned semantic labels.
-- Used by: #1 (consensus fade), #2 (class-weighted sentiment), #6 (policy
-- dispersion, via policy_stance_labels in a later migration).

CREATE TABLE articles (
    article_id      TEXT PRIMARY KEY,     -- sha256(source|url|body_hash)
    source          TEXT NOT NULL,
    title           TEXT NOT NULL,
    url             TEXT NOT NULL,
    published_at    TEXT NOT NULL,
    knowledge_time  TEXT NOT NULL,        -- fetch timestamp
    body_hash       TEXT,
    outlet_class    TEXT NOT NULL CHECK (outlet_class IN ('capital', 'labor', 'mixed', 'think_tank'))
);

CREATE INDEX idx_articles_published ON articles(published_at);
CREATE INDEX idx_articles_outlet_class ON articles(outlet_class, published_at);

-- Labels are versioned data (see ARCHITECTURE.md "semantic/"). A prompt
-- change creates a new classifier_version; old and new rows coexist so
-- label sets can be diffed and a study's conclusion checked for survival.
CREATE TABLE article_labels (
    article_id          TEXT NOT NULL REFERENCES articles(article_id),
    classifier_version  TEXT NOT NULL,
    sentiment           REAL CHECK (sentiment BETWEEN -1 AND 1),
    confidence          REAL CHECK (confidence BETWEEN 0 AND 1),
    circuit             TEXT CHECK (circuit IN ('money', 'productive', 'consumption', 'mixed')),
    evidence            TEXT,
    model_id            TEXT,
    prompt_hash         TEXT,
    knowledge_time      TEXT NOT NULL,
    PRIMARY KEY (article_id, classifier_version)
);

CREATE INDEX idx_article_labels_version ON article_labels(classifier_version);
