-- ToolsDB schema for the analysis cache + job queue.
--
-- Apply with:  toolforge jobs run schema --image tool-wikibias-analyzer/tool-wikibias-analyzer:latest --command schema --wait
-- or locally:  python backend/schema.py
--
-- The same row is both the cache entry and the queue item: `status` drives the
-- async flow. The web tier only ever INSERTs a 'pending' row and reads; the
-- worker is the only writer of results.

CREATE TABLE IF NOT EXISTS analysis_cache (
    -- Hex SHA-256. Pinned to ascii_bin rather than inheriting the table's
    -- utf8mb4_unicode_ci: a hash is bytes, not text, so this keeps the primary
    -- key a quarter the size, makes lookups a plain binary compare, and removes
    -- any chance of an "illegal mix of collations" against a differently
    -- collated session.
    url_hash     CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    page_url     VARCHAR(1024) NOT NULL,
    page_title   VARCHAR(255)      NULL,
    result       LONGTEXT          NULL,
    source_count INT               NULL,
    status       VARCHAR(16)   NOT NULL DEFAULT 'pending',
    error        TEXT              NULL,
    attempts     INT           NOT NULL DEFAULT 0,
    created_at   TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at   TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP
                 ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (url_hash),
    KEY idx_queue (status, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
