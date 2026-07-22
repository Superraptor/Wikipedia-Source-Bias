import config


def test_local_defaults_when_not_on_toolforge(monkeypatch):
    monkeypatch.delenv("TOOL_TOOLSDB_USER", raising=False)
    monkeypatch.delenv("DB_HOST", raising=False)
    monkeypatch.delenv("DB_NAME", raising=False)
    assert config.on_toolforge() is False
    params = config.db_params()
    assert params["host"] == "localhost"
    assert params["database"] == "sourcesbias"


def test_toolsdb_params_derived_from_injected_credentials(monkeypatch):
    monkeypatch.setenv("TOOL_TOOLSDB_USER", "s57898")
    monkeypatch.setenv("TOOL_TOOLSDB_PASSWORD", "hunter2")
    monkeypatch.delenv("DB_HOST", raising=False)
    monkeypatch.delenv("DB_NAME", raising=False)
    monkeypatch.delenv("DB_USER", raising=False)
    monkeypatch.delenv("DB_PASSWORD", raising=False)

    params = config.db_params()
    assert config.on_toolforge() is True
    assert params["host"] == "tools.db.svc.wikimedia.cloud"
    assert params["user"] == "s57898"
    assert params["password"] == "hunter2"
    # Toolforge only permits databases prefixed with the credential user and
    # exactly two underscores.
    assert params["database"] == "s57898__wikibias"
    assert params["database"].count("_") == 2


def test_explicit_db_env_overrides_toolsdb(monkeypatch):
    monkeypatch.setenv("TOOL_TOOLSDB_USER", "s57898")
    monkeypatch.setenv("DB_HOST", "127.0.0.1")
    monkeypatch.setenv("DB_NAME", "other")
    params = config.db_params()
    assert params["host"] == "127.0.0.1"
    assert params["database"] == "other"


def test_mock_is_disabled_by_default_on_toolforge(monkeypatch):
    monkeypatch.setenv("TOOL_TOOLSDB_USER", "s57898")
    monkeypatch.delenv("ALLOW_MOCK_ANALYSIS", raising=False)
    assert config.allow_mock() is False


def test_mock_allowed_by_default_locally(monkeypatch):
    monkeypatch.delenv("TOOL_TOOLSDB_USER", raising=False)
    monkeypatch.delenv("ALLOW_MOCK_ANALYSIS", raising=False)
    assert config.allow_mock() is True


def test_mock_can_be_forced_on(monkeypatch):
    monkeypatch.setenv("TOOL_TOOLSDB_USER", "s57898")
    monkeypatch.setenv("ALLOW_MOCK_ANALYSIS", "1")
    assert config.allow_mock() is True
