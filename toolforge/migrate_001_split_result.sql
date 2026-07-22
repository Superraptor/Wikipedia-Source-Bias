-- One-off migration: move payloads out of analysis_cache.result into
-- analysis_result, then drop the legacy column.
--
-- New deployments do not need this: schema.sql already creates the split
-- shape. Run only against a database created before the split.
--
-- Rows are copied with compressed=0, i.e. the raw JSON text. Deliberately NOT
-- MySQL's COMPRESS(): that prepends a 4-byte length header and is not a zlib
-- stream, so Python's zlib.decompress would reject it. _decode() reads
-- compressed=0 rows as plain JSON, and the next write re-saves them
-- zlib-compressed.

INSERT IGNORE INTO analysis_result (url_hash, kind, payload, compressed, byte_size)
SELECT url_hash, 'json', result, 0, LENGTH(result)
FROM analysis_cache
WHERE result IS NOT NULL;

ALTER TABLE analysis_cache DROP COLUMN result;
