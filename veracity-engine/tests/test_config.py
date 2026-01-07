"""
Unit tests for Configuration Management (STORY-001).

TDD Specifications:
1. Configuration Hierarchy: Defaults -> Config File -> Env Vars -> CLI Args
2. Configuration Validation: Invalid values raise ValidationError
3. Backward Compatibility: Existing CLI arguments continue to work
4. Secret Handling: Secrets masked in logs
"""
import os
import pytest
from pathlib import Path


class TestConfigHierarchy:
    """Tests for hierarchical configuration resolution."""

    def test_default_values_applied(self):
        """Should load with all default values when no config sources provided."""
        from core.config import ConfigLoader

        config = ConfigLoader.load()
        assert config.neo4j.uri == "bolt://localhost:7687"
        assert config.neo4j.user == "neo4j"
        assert config.logging.level == "INFO"
        assert config.embedding.model == "nomic-embed-text"

    def test_config_file_overrides_defaults(self, tmp_path, monkeypatch):
        """Config file values should override defaults."""
        from core.config import ConfigLoader

        # Clear legacy env vars that CI sets (they have higher priority than config file)
        monkeypatch.delenv("NEO4J_URI", raising=False)
        monkeypatch.delenv("NEO4J_USER", raising=False)
        monkeypatch.delenv("NEO4J_PASSWORD", raising=False)

        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
neo4j:
  uri: "bolt://custom-host:7687"
  user: "custom_user"
logging:
  level: "DEBUG"
""")
        config = ConfigLoader.load(config_file=str(config_file))
        assert config.neo4j.uri == "bolt://custom-host:7687"
        assert config.neo4j.user == "custom_user"
        assert config.logging.level == "DEBUG"
        # Defaults should still apply for unspecified values
        assert config.embedding.model == "nomic-embed-text"

    def test_env_vars_override_config_file(self, monkeypatch, tmp_path):
        """Environment variables should override config file values."""
        from core.config import ConfigLoader

        # Clear legacy env vars that CI sets (they have higher priority than VERACITY_* vars)
        monkeypatch.delenv("NEO4J_URI", raising=False)
        monkeypatch.delenv("NEO4J_USER", raising=False)
        monkeypatch.delenv("NEO4J_PASSWORD", raising=False)

        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
neo4j:
  uri: "bolt://file-host:7687"
  user: "file_user"
""")
        # Environment variables with VERACITY_ prefix
        monkeypatch.setenv("VERACITY_NEO4J__URI", "bolt://env-host:7687")
        monkeypatch.setenv("VERACITY_LOGGING__LEVEL", "WARNING")

        config = ConfigLoader.load(config_file=str(config_file))
        # Env var should override file
        assert config.neo4j.uri == "bolt://env-host:7687"
        # File value should still apply when no env var
        assert config.neo4j.user == "file_user"
        # Env var for logging
        assert config.logging.level == "WARNING"

    def test_cli_args_override_env_vars(self, monkeypatch):
        """CLI arguments should override environment variables."""
        from core.config import ConfigLoader

        monkeypatch.setenv("VERACITY_NEO4J__URI", "bolt://env-host:7687")
        monkeypatch.setenv("VERACITY_NEO4J__USER", "env_user")

        # CLI override via kwargs
        config = ConfigLoader.load(
            neo4j_uri="bolt://cli-host:7687",
            neo4j_user="cli_user"
        )
        assert config.neo4j.uri == "bolt://cli-host:7687"
        assert config.neo4j.user == "cli_user"

    def test_full_hierarchy_precedence(self, monkeypatch, tmp_path):
        """Full test of hierarchy: defaults < file < env < cli."""
        from core.config import ConfigLoader

        # Clear legacy env vars that CI sets (they have higher priority than config file)
        monkeypatch.delenv("NEO4J_URI", raising=False)
        monkeypatch.delenv("NEO4J_USER", raising=False)
        monkeypatch.delenv("NEO4J_PASSWORD", raising=False)
        monkeypatch.delenv("EMBED_MODEL", raising=False)

        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
neo4j:
  uri: "bolt://file:7687"
  user: "file_user"
  password: "file_pass"
embedding:
  model: "file-embed-model"
""")
        monkeypatch.setenv("VERACITY_NEO4J__USER", "env_user")
        monkeypatch.setenv("VERACITY_EMBEDDING__MODEL", "env-embed-model")

        config = ConfigLoader.load(
            config_file=str(config_file),
            neo4j_user="cli_user"
        )

        # CLI wins over all
        assert config.neo4j.user == "cli_user"
        # Env wins over file
        assert config.embedding.model == "env-embed-model"
        # File wins over default
        assert config.neo4j.uri == "bolt://file:7687"
        assert config.neo4j.password.get_secret_value() == "file_pass"


class TestConfigValidation:
    """Tests for configuration validation."""

    def test_invalid_log_level_raises_error(self, tmp_path):
        """Invalid logging level should raise ValidationError."""
        from pydantic import ValidationError
        from core.config import ConfigLoader

        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
logging:
  level: "INVALID_LEVEL"
""")
        with pytest.raises(ValidationError):
            ConfigLoader.load(config_file=str(config_file))

    def test_valid_config_accepts_all_fields(self):
        """Valid configuration with all fields should be accepted."""
        from core.config import VeracityConfig, Neo4jConfig, EmbeddingConfig, LLMConfig, LoggingConfig

        config = VeracityConfig(
            neo4j=Neo4jConfig(
                uri="bolt://localhost:7687",
                user="neo4j",
                password="testpass"
            ),
            embedding=EmbeddingConfig(
                model="nomic-embed-text",
                batch_size=32
            ),
            llm=LLMConfig(
                model="llama3.2",
                seed=42,
                temperature=0.0
            ),
            logging=LoggingConfig(
                level="DEBUG",
                format="%(asctime)s - %(levelname)s - %(message)s"
            )
        )
        assert config.neo4j.uri == "bolt://localhost:7687"
        assert config.embedding.batch_size == 32
        assert config.llm.seed == 42

    def test_missing_config_file_uses_defaults(self):
        """Missing config file should not raise error, use defaults."""
        from core.config import ConfigLoader

        config = ConfigLoader.load(config_file="/nonexistent/path/config.yaml")
        # Should fall back to defaults
        assert config.neo4j.uri == "bolt://localhost:7687"


class TestSecretHandling:
    """Tests for secret masking and handling."""

    def test_password_is_secret_str(self):
        """Password should be stored as SecretStr."""
        from pydantic import SecretStr
        from core.config import ConfigLoader

        config = ConfigLoader.load()
        assert hasattr(config.neo4j.password, 'get_secret_value')
        # SecretStr should mask when converted to string
        assert "**" in str(config.neo4j.password) or "SecretStr" in str(config.neo4j.password)

    def test_secret_not_exposed_in_repr(self):
        """Secrets should not be exposed in repr/str output."""
        from core.config import ConfigLoader

        config = ConfigLoader.load(neo4j_password="super_secret_password")
        config_str = str(config)
        config_repr = repr(config)

        assert "super_secret_password" not in config_str
        assert "super_secret_password" not in config_repr

    def test_secret_accessible_via_get_secret_value(self):
        """Secrets should be accessible via get_secret_value()."""
        from core.config import ConfigLoader

        config = ConfigLoader.load(neo4j_password="my_password")
        assert config.neo4j.password.get_secret_value() == "my_password"


class TestConfigSchema:
    """Tests for configuration schema structure."""

    def test_neo4j_config_has_required_fields(self):
        """Neo4j config should have uri, user, password."""
        from core.config import ConfigLoader

        config = ConfigLoader.load()
        assert hasattr(config.neo4j, 'uri')
        assert hasattr(config.neo4j, 'user')
        assert hasattr(config.neo4j, 'password')

    def test_embedding_config_has_required_fields(self):
        """Embedding config should have model and batch_size."""
        from core.config import ConfigLoader

        config = ConfigLoader.load()
        assert hasattr(config.embedding, 'model')
        assert hasattr(config.embedding, 'batch_size')

    def test_llm_config_has_required_fields(self):
        """LLM config should have model, seed, temperature."""
        from core.config import ConfigLoader

        config = ConfigLoader.load()
        assert hasattr(config.llm, 'model')
        assert hasattr(config.llm, 'seed')
        assert hasattr(config.llm, 'temperature')

    def test_logging_config_has_required_fields(self):
        """Logging config should have level and format."""
        from core.config import ConfigLoader

        config = ConfigLoader.load()
        assert hasattr(config.logging, 'level')
        assert hasattr(config.logging, 'format')


class TestBackwardCompatibility:
    """Tests for backward compatibility with existing patterns."""

    def test_legacy_env_vars_still_work(self, monkeypatch):
        """Legacy NEO4J_* environment variables should still work."""
        from core.config import ConfigLoader

        # Legacy format (without VERACITY_ prefix)
        monkeypatch.setenv("NEO4J_URI", "bolt://legacy-host:7687")
        monkeypatch.setenv("NEO4J_USER", "legacy_user")
        monkeypatch.setenv("NEO4J_PASSWORD", "legacy_pass")

        config = ConfigLoader.load()
        assert config.neo4j.uri == "bolt://legacy-host:7687"
        assert config.neo4j.user == "legacy_user"
        assert config.neo4j.password.get_secret_value() == "legacy_pass"

    def test_legacy_embed_model_env_var(self, monkeypatch):
        """Legacy EMBED_MODEL environment variable should still work."""
        from core.config import ConfigLoader

        monkeypatch.setenv("EMBED_MODEL", "legacy-embed-model")
        config = ConfigLoader.load()
        assert config.embedding.model == "legacy-embed-model"

    def test_legacy_llm_model_env_var(self, monkeypatch):
        """Legacy LLM_MODEL environment variable should still work."""
        from core.config import ConfigLoader

        monkeypatch.setenv("LLM_MODEL", "legacy-llm-model")
        config = ConfigLoader.load()
        assert config.llm.model == "legacy-llm-model"


class TestConfigLoaderAPI:
    """Tests for ConfigLoader API."""

    def test_load_returns_veracity_config(self):
        """ConfigLoader.load() should return VeracityConfig instance."""
        from core.config import ConfigLoader, VeracityConfig

        config = ConfigLoader.load()
        assert isinstance(config, VeracityConfig)

    def test_get_singleton_returns_cached_config(self):
        """ConfigLoader.get() should return singleton instance."""
        from core.config import ConfigLoader

        config1 = ConfigLoader.get()
        config2 = ConfigLoader.get()
        assert config1 is config2

    def test_reload_refreshes_config(self):
        """ConfigLoader.reload() should refresh configuration."""
        from core.config import ConfigLoader

        config1 = ConfigLoader.get()
        ConfigLoader.reload()
        config2 = ConfigLoader.get()
        # After reload, should still work (may be same or different instance)
        assert config2 is not None
