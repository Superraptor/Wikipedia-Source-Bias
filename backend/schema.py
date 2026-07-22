"""Apply toolforge/schema.sql to the configured database. Idempotent.

    toolforge jobs run schema \
        --image tool-wikibias-analyzer/tool-wikibias-analyzer:latest \
        --command schema --wait
"""
import os
import sys

import config

SCHEMA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "toolforge",
    "schema.sql",
)


def statements(sql):
    """Split a .sql file into executable statements.

    Comments are stripped BEFORE splitting on ';'. Prose comments legitimately
    contain semicolons, and splitting first tears a comment in half and feeds
    the remainder to the server as if it were SQL.
    """
    lines = []
    for line in sql.splitlines():
        stripped = line.strip()
        if stripped.startswith("--"):
            continue
        # Trailing comment on a code line. This deliberately does not try to
        # handle '--' inside a string literal; the schema contains none.
        idx = line.find("--")
        lines.append(line[:idx] if idx != -1 else line)
    return [s.strip() for s in "\n".join(lines).split(";") if s.strip()]


def main():
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        sql = f.read()

    params = config.db_params()
    print(f"Applying schema to {params['user']}@{params['host']}/{params['database']}")

    conn = config.connect()
    try:
        cur = conn.cursor()
        try:
            for stmt in statements(sql):
                cur.execute(stmt)
        finally:
            cur.close()
        conn.commit()
    finally:
        conn.close()
    print("Schema applied.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"FAILED: {e}", file=sys.stderr)
        sys.exit(1)
