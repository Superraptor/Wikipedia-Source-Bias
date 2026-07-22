"""The schema splitter must not be confused by semicolons inside comments.

toolforge/schema.sql documents the queue design in prose, and that prose
contains semicolons. Splitting on ';' before stripping comments tore a comment
in half and sent the tail to MariaDB, which failed the schema job with a syntax
error pointing at English text.
"""
import os

import schema


def test_comment_semicolons_do_not_split_statements():
    sql = """
-- This is the cache and the queue; status distinguishes them.
CREATE TABLE a (id INT);
-- Another; comment; with; semicolons.
CREATE TABLE b (id INT);
"""
    stmts = schema.statements(sql)
    assert len(stmts) == 2
    assert stmts[0].startswith("CREATE TABLE a")
    assert stmts[1].startswith("CREATE TABLE b")


def test_trailing_comment_is_stripped():
    stmts = schema.statements("CREATE TABLE a (id INT);  -- trailing; note\n")
    assert len(stmts) == 1
    assert "trailing" not in stmts[0]


def test_real_schema_file_parses_to_one_create_table():
    with open(schema.SCHEMA_PATH, encoding="utf-8") as f:
        stmts = schema.statements(f.read())
    assert len(stmts) == 1, f"expected 1 statement, got {len(stmts)}: {stmts}"
    assert stmts[0].upper().startswith("CREATE TABLE")
    assert "url_hash" in stmts[0]


def test_schema_path_resolves():
    assert os.path.isfile(schema.SCHEMA_PATH)
