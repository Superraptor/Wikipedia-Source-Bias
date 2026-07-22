"""Database configuration.

Toolforge's build service injects TOOL_TOOLSDB_USER / TOOL_TOOLSDB_PASSWORD
into the container. It does NOT inject a host or a database name, and the
credential user (e.g. s57898) is also the required prefix of every database
this tool is allowed to create -- hence the `{user}__{suffix}` convention.

Plain DB_* variables still win when set, so local development against a local
MariaDB keeps working unchanged.
"""
import os

TOOLSDB_HOST = "tools.db.svc.wikimedia.cloud"
TOOLSDB_SUFFIX = "wikibias"


def _toolsdb_user():
    return os.environ.get("TOOL_TOOLSDB_USER")


def db_params():
    """Connection kwargs for pymysql.connect()."""
    tools_user = _toolsdb_user()

    if tools_user:
        default_host = TOOLSDB_HOST
        default_user = tools_user
        default_password = os.environ.get("TOOL_TOOLSDB_PASSWORD", "")
        # Toolforge requires exactly two underscores between the credential
        # user and the database suffix.
        default_name = f"{tools_user}__{TOOLSDB_SUFFIX}"
    else:
        default_host = "localhost"
        default_user = "root"
        default_password = ""
        default_name = "sourcesbias"

    return {
        "host": os.environ.get("DB_HOST", default_host),
        "user": os.environ.get("DB_USER", default_user),
        "password": os.environ.get("DB_PASSWORD", default_password),
        "database": os.environ.get("DB_NAME", default_name),
        "charset": "utf8mb4",
    }


def connect(autocommit=True):
    import pymysql

    return pymysql.connect(autocommit=autocommit, **db_params())


def on_toolforge():
    return _toolsdb_user() is not None


def allow_mock():
    """Whether the demo mock may stand in for a real analysis.

    Defaults to OFF on Toolforge. The mock previously loaded via a bare
    `except ImportError`, which meant a misconfigured PYTHONPATH produced a
    green deploy serving entirely fabricated numbers. Making it explicit means
    a broken import fails loudly instead.
    """
    raw = os.environ.get("ALLOW_MOCK_ANALYSIS")
    if raw is None:
        return not on_toolforge()
    return raw.strip().lower() in ("1", "true", "yes", "on")
