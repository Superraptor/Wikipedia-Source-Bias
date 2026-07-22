-- ToolsDB schema.
--
-- Apply with:  toolforge jobs run schema --wait --image <img> --command schema
-- or locally:  python backend/schema.py
--
-- Three tables:
--   analysis_cache   thin metadata, and the job queue (status drives both)
--   analysis_result  the big payloads, split out so the queue stays cheap
--   kv_cache         the analyzer's lookup caches (MBFC, Wikidata, Crossref...)

-- Queue + metadata. Deliberately holds no payload: the status page and the
-- worker's claim_next() scan this table, and dragging multi-megabyte blobs
-- through those queries is pure waste. REPLACE INTO on a row holding a 5MB
-- result also rewrote the whole blob on every status change.
CREATE TABLE IF NOT EXISTS analysis_cache (
    -- Hex SHA-256. Pinned to ascii_bin rather than inheriting the table's
    -- utf8mb4_unicode_ci: a hash is bytes, not text, so this keeps the primary
    -- key a quarter the size, makes lookups a plain binary compare, and removes
    -- any chance of an "illegal mix of collations" against a differently
    -- collated session.
    url_hash     CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    page_url     VARCHAR(1024) NOT NULL,
    page_title   VARCHAR(255)      NULL,
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

-- Payloads, one row per (analysis, kind). `kind` separates the report JSON
-- from the GeoJSON map data so a caller can fetch just the one it needs.
-- LONGBLOB because the payload is zlib-compressed: these run 3-5MB raw for
-- large articles and compress roughly tenfold.
CREATE TABLE IF NOT EXISTS analysis_result (
    url_hash   CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    kind       VARCHAR(16) CHARACTER SET ascii NOT NULL DEFAULT 'json',
    payload    LONGBLOB    NOT NULL,
    compressed TINYINT(1)  NOT NULL DEFAULT 1,
    byte_size  INT         NOT NULL DEFAULT 0,
    updated_at TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP
               ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (url_hash, kind),
    CONSTRAINT fk_result_cache FOREIGN KEY (url_hash)
        REFERENCES analysis_cache (url_hash) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- The analyzer's own lookup caches, which on a container filesystem were wiped
-- on every restart and not shared between worker replicas -- so every analysis
-- re-hit Crossref, MBFC, Wikidata and archive.org from scratch, against their
-- rate limits. Keyed by hash because cache keys are URLs and author names,
-- which are too long and too variable to index directly.
CREATE TABLE IF NOT EXISTS kv_cache (
    namespace  VARCHAR(64) CHARACTER SET ascii NOT NULL,
    key_hash   CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    cache_key  TEXT      NOT NULL,
    value      LONGTEXT  NOT NULL,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
               ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (namespace, key_hash)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Progress reporting for in-flight analyses. Without this a long article sits
-- at "running" for tens of minutes with no indication of where it has got to
-- or how much is left.
ALTER TABLE analysis_cache
    ADD COLUMN IF NOT EXISTS stage VARCHAR(24) NULL,
    ADD COLUMN IF NOT EXISTS progress_done INT NULL,
    ADD COLUMN IF NOT EXISTS progress_total INT NULL;

-- ETA support. `started_at` separates analysis time from queue-wait time: the
-- first ETA implementation divided by "time since queued", so an article that
-- waited 20 minutes for a worker reported a wildly inflated rate. `eta_seconds`
-- is computed by the worker, which is the only process that knows how long
-- each individual source actually took.
ALTER TABLE analysis_cache
    ADD COLUMN IF NOT EXISTS started_at DATETIME NULL,
    ADD COLUMN IF NOT EXISTS eta_seconds INT NULL;
