"""
Tests for Secrets Management (STORY-003).

Tests cover:
1. Secret validation (default password warnings, minimum length)
2. Secret redaction in logs and config dumps
3. Environment file permission checks
"""
import os
import stat
import pytest
import warnings
from pathlib import Path

from core.config import (
    ConfigLoader,
    validate_secrets,
    check_env_file_permissions,
    redact_config,
    log_config_summary,
    ConfigSecurityError,
    DEFAULT_INSECURE_PASSWORDS,
    MINIMUM_PASSWORD_LENGTH,
)


class TestSecretValidation:
    """Tests for secret validation functionality."""

    def test_default_password_triggers_warning(self, caplog):
        """Using default password 'password' should trigger warning."""
        import logging
        caplog.set_level(logging.WARNING)

        config = ConfigLoader.load(neo4j_password="password")
        issues = validate_secrets(config)

        assert len(issues) > 0
        assert any("insecure default" in issue for issue in issues)
        assert any("password" in record.message.lower() for record in caplog.records)

    def test_known_insecure_passwords_trigger_warning(self, caplog):
        """All known insecure passwords should trigger warnings."""
        import logging
        caplog.set_level(logging.WARNING)

        for bad_password in ["password", "secret", "admin", "123456", "neo4j"]:
            ConfigLoader._instance = None  # Reset singleton
            config = ConfigLoader.load(neo4j_password=bad_password)
            issues = validate_secrets(config)
            assert len(issues) > 0, f"Password '{bad_password}' should trigger warning"

    def test_short_password_triggers_warning(self, caplog):
        """Password shorter than minimum should trigger warning."""
        import logging
        caplog.set_level(logging.WARNING)

        config = ConfigLoader.load(neo4j_password="abc")  # 3 chars
        issues = validate_secrets(config)

        assert len(issues) > 0
        assert any("too short" in issue for issue in issues)

    def test_short_password_strict_mode_raises(self):
        """In strict mode, short password should raise ConfigSecurityError."""
        config = ConfigLoader.load(neo4j_password="short")  # 5 chars

        with pytest.raises(ConfigSecurityError) as exc_info:
            validate_secrets(config, strict=True)

        assert "too short" in str(exc_info.value)

    def test_secure_password_passes_validation(self):
        """A secure password should pass validation without issues."""
        config = ConfigLoader.load(neo4j_password="SecureP@ssw0rd123!")
        issues = validate_secrets(config)

        assert len(issues) == 0

    def test_minimum_password_length_enforced(self):
        """Password at exactly minimum length should pass."""
        # Create password of exactly minimum length
        password = "A" * MINIMUM_PASSWORD_LENGTH
        config = ConfigLoader.load(neo4j_password=password)
        issues = validate_secrets(config)

        # Should not have length-related issues (might still have insecure default issue if it matches)
        length_issues = [i for i in issues if "too short" in i]
        assert len(length_issues) == 0


class TestSecretRedaction:
    """Tests for secret redaction in logs and dumps."""

    def test_password_redacted_in_config_dump(self):
        """Password should be redacted in config dump."""
        config = ConfigLoader.load(neo4j_password="super_secret_123")
        redacted = redact_config(config)

        assert redacted["neo4j"]["password"] == "****REDACTED****"
        assert "super_secret_123" not in str(redacted)

    def test_password_not_exposed_in_str(self):
        """Password should not be exposed in string representation."""
        config = ConfigLoader.load(neo4j_password="my_secret_password")

        config_str = str(config)
        config_repr = repr(config)

        assert "my_secret_password" not in config_str
        assert "my_secret_password" not in config_repr

    def test_password_accessible_via_get_secret_value(self):
        """Password should be accessible via get_secret_value()."""
        config = ConfigLoader.load(neo4j_password="accessible_password")

        actual = config.neo4j.password.get_secret_value()
        assert actual == "accessible_password"

    def test_log_config_summary_no_secrets(self, caplog):
        """log_config_summary should not expose secrets."""
        import logging
        caplog.set_level(logging.INFO)

        config = ConfigLoader.load(neo4j_password="hidden_password")
        log_config_summary(config)

        # Check no password in logs
        full_log = "\n".join(record.message for record in caplog.records)
        assert "hidden_password" not in full_log

        # But should have other info
        assert "Neo4j" in full_log


class TestEnvFilePermissions:
    """Tests for environment file permission checks."""

    def test_env_file_not_exist_returns_true(self, tmp_path):
        """Non-existent .env file should return True (no issue)."""
        non_existent = tmp_path / ".env.nonexistent"
        result = check_env_file_permissions(str(non_existent))
        assert result is True

    def test_secure_permissions_returns_true(self, tmp_path):
        """File with mode 600 should return True."""
        env_file = tmp_path / ".env"
        env_file.write_text("SECRET=value\n")
        env_file.chmod(0o600)

        result = check_env_file_permissions(str(env_file))
        assert result is True

    def test_world_readable_triggers_warning(self, tmp_path):
        """File with world-readable permission should warn."""
        env_file = tmp_path / ".env"
        env_file.write_text("SECRET=value\n")
        env_file.chmod(0o644)  # World readable

        with pytest.warns(UserWarning) as warning_info:
            result = check_env_file_permissions(str(env_file))

        assert result is False
        assert any("insecure permissions" in str(w.message) for w in warning_info)

    def test_group_readable_triggers_warning(self, tmp_path):
        """File with group-readable permission should warn."""
        env_file = tmp_path / ".env"
        env_file.write_text("SECRET=value\n")
        env_file.chmod(0o640)  # Group readable

        with pytest.warns(UserWarning) as warning_info:
            result = check_env_file_permissions(str(env_file))

        assert result is False
        assert any("insecure permissions" in str(w.message) for w in warning_info)


class TestSecurityConstants:
    """Tests for security-related constants."""

    def test_default_insecure_passwords_defined(self):
        """DEFAULT_INSECURE_PASSWORDS should contain common bad passwords."""
        assert "password" in DEFAULT_INSECURE_PASSWORDS
        assert "secret" in DEFAULT_INSECURE_PASSWORDS
        assert "admin" in DEFAULT_INSECURE_PASSWORDS

    def test_minimum_password_length_reasonable(self):
        """MINIMUM_PASSWORD_LENGTH should be at least 8."""
        assert MINIMUM_PASSWORD_LENGTH >= 8


class TestGitignoreSecurityPatterns:
    """Tests to verify .gitignore has security patterns."""

    def test_gitignore_excludes_env_files(self):
        """Gitignore should exclude .env files."""
        gitignore_path = Path(__file__).parent.parent / ".gitignore"
        content = gitignore_path.read_text()

        assert ".env" in content
        assert ".env.local" in content

    def test_gitignore_excludes_key_files(self):
        """Gitignore should exclude key and certificate files."""
        gitignore_path = Path(__file__).parent.parent / ".gitignore"
        content = gitignore_path.read_text()

        assert "*.key" in content
        assert "*.pem" in content
