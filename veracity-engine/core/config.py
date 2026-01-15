"""
Configuration Management for Veracity Engine (STORY-001, STORY-003).

This module provides a hierarchical configuration system with the following
precedence (highest to lowest):
1. CLI arguments (passed to ConfigLoader.load())
2. Environment variables (VERACITY_* prefix with __ delimiter)
3. Configuration file (YAML)
4. Default values

Supports:
- Pydantic validation for type safety
- SecretStr for sensitive values (passwords, API keys)
- Legacy environment variable support (NEO4J_*, EMBED_MODEL, LLM_MODEL)
- YAML configuration files
- Secret validation and redaction (STORY-003)
"""
import os
import stat
import logging
import warnings
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Type

import yaml
from pydantic import BaseModel, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict

logger = logging.getLogger(__name__)

# Valid log levels for validation
VALID_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}

# Security constants (STORY-003)
DEFAULT_INSECURE_PASSWORDS = {"password", "secret", "admin", "123456", "neo4j"}
MINIMUM_PASSWORD_LENGTH = 8


class ConfigSecurityError(Exception):
    """Raised when configuration fails security validation."""
    pass


class Neo4jConfig(BaseModel):
    """Neo4j database connection configuration."""
    uri: str = Field(default="bolt://localhost:7687", description="Neo4j connection URI")
    user: str = Field(default="neo4j", description="Neo4j username")
    password: SecretStr = Field(default=SecretStr("password"), description="Neo4j password")
    pool_size: int = Field(default=50, description="Connection pool size")


class EmbeddingConfig(BaseModel):
    """Embedding model configuration."""
    model: str = Field(default="nomic-embed-text", description="Ollama embedding model name")
    version: Optional[str] = Field(default=None, description="Model version for reproducibility (e.g., 'latest')")
    digest: Optional[str] = Field(default=None, description="Model SHA256 digest for exact version pinning")
    dimensions: int = Field(default=768, description="Embedding vector dimensions")
    batch_size: int = Field(default=32, description="Batch size for embedding generation")
    document_prefix: str = Field(default="search_document:", description="Prefix for document embeddings")
    query_prefix: str = Field(default="search_query:", description="Prefix for query embeddings")
    verify_on_startup: bool = Field(default=False, description="Verify model digest on startup")


class LLMConfig(BaseModel):
    """LLM (Large Language Model) configuration."""
    model: str = Field(default="llama3.2", description="Ollama LLM model name")
    version: Optional[str] = Field(default=None, description="Model version for reproducibility (e.g., 'latest')")
    digest: Optional[str] = Field(default=None, description="Model SHA256 digest for exact version pinning")
    seed: int = Field(default=42, description="Random seed for deterministic output")
    temperature: float = Field(default=0.0, description="Temperature for response generation (0.0 for deterministic)")
    top_k: int = Field(default=1, description="Top-k sampling for deterministic output (1 = greedy)")
    repeat_penalty: float = Field(default=1.1, description="Repeat penalty for generation")
    verify_on_startup: bool = Field(default=False, description="Verify model digest on startup")


class LoggingConfig(BaseModel):
    """Logging configuration."""
    level: str = Field(default="INFO", description="Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)")
    format: str = Field(
        default="%(asctime)s - %(levelname)s - %(message)s",
        description="Log message format"
    )

    @field_validator('level')
    @classmethod
    def validate_level(cls, v: str) -> str:
        """Validate log level is one of the standard Python levels."""
        v_upper = v.upper()
        if v_upper not in VALID_LOG_LEVELS:
            raise ValueError(f"Invalid log level '{v}'. Must be one of: {VALID_LOG_LEVELS}")
        return v_upper


class GitHubConfig(BaseModel):
    """GitHub API integration configuration."""
    token: SecretStr = Field(default=SecretStr(""), description="GitHub personal access token")
    user_agent: str = Field(default="ESS-Dev-Context-Tracker/1.0", description="User-Agent for GitHub API requests")
    api_base_url: str = Field(default="https://api.github.com", description="GitHub API base URL")
    rate_limit_buffer: int = Field(default=10, description="Buffer requests before hitting rate limit")


class ProjectConfig(BaseModel):
    """Project-specific configuration."""
    name: Optional[str] = Field(default=None, description="Project name for multitenancy")
    root_dir: Optional[str] = Field(default=None, description="Project root directory")
    target_dirs: list[str] = Field(
        default=["services", "models", "scripts", "docs", "core", "api", "lib", "src"],
        description="Directories to scan for indexing"
    )


class VeracityConfig(BaseModel):
    """Root configuration schema for Veracity Engine."""
    neo4j: Neo4jConfig = Field(default_factory=Neo4jConfig)
    embedding: EmbeddingConfig = Field(default_factory=EmbeddingConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    github: GitHubConfig = Field(default_factory=GitHubConfig)
    project: ProjectConfig = Field(default_factory=ProjectConfig)

    model_config = {"extra": "ignore"}


class YamlConfigSettingsSource(PydanticBaseSettingsSource):
    """Custom settings source that reads from a YAML file."""

    def __init__(
        self,
        settings_cls: Type[BaseSettings],
        config_file: Optional[str] = None
    ):
        super().__init__(settings_cls)
        self.config_file = config_file
        self._yaml_data: Dict[str, Any] = {}
        self._load_yaml()

    def _load_yaml(self) -> None:
        """Load YAML configuration file if it exists."""
        if not self.config_file:
            return

        config_path = Path(self.config_file)
        if not config_path.exists():
            logger.debug(f"Config file not found: {self.config_file}")
            return

        try:
            with open(config_path, 'r') as f:
                data = yaml.safe_load(f)
                if data:
                    self._yaml_data = data
                    logger.debug(f"Loaded config from: {self.config_file}")
        except Exception as e:
            logger.warning(f"Failed to load config file {self.config_file}: {e}")

    def get_field_value(
        self, field: Any, field_name: str
    ) -> Tuple[Any, str, bool]:
        """Get field value from YAML data."""
        # For nested models, return the whole section
        if field_name in self._yaml_data:
            return self._yaml_data[field_name], field_name, False
        return None, field_name, False

    def __call__(self) -> Dict[str, Any]:
        """Return all YAML data."""
        return self._yaml_data


class LegacyEnvSettingsSource(PydanticBaseSettingsSource):
    """Custom settings source for legacy environment variables (NEO4J_*, EMBED_MODEL, etc.)."""

    def get_field_value(
        self, field: Any, field_name: str
    ) -> Tuple[Any, str, bool]:
        """Get field value from legacy environment variables."""
        return None, field_name, False

    def __call__(self) -> Dict[str, Any]:
        """Return legacy environment variable mappings."""
        result: Dict[str, Any] = {}

        # Legacy Neo4j environment variables
        if neo4j_uri := os.getenv("NEO4J_URI"):
            result.setdefault("neo4j", {})["uri"] = neo4j_uri
        if neo4j_user := os.getenv("NEO4J_USER"):
            result.setdefault("neo4j", {})["user"] = neo4j_user
        if neo4j_password := os.getenv("NEO4J_PASSWORD"):
            result.setdefault("neo4j", {})["password"] = neo4j_password

        # Legacy embedding model
        if embed_model := os.getenv("EMBED_MODEL"):
            result.setdefault("embedding", {})["model"] = embed_model

        # Legacy LLM model
        if llm_model := os.getenv("LLM_MODEL"):
            result.setdefault("llm", {})["model"] = llm_model
        if llm_seed := os.getenv("LLM_SEED"):
            result.setdefault("llm", {})["seed"] = int(llm_seed)

        return result


class ConfigSettings(BaseSettings):
    """
    Pydantic Settings class for Veracity Engine configuration.

    Implements hierarchical configuration with sources in order of precedence:
    1. init_settings (CLI arguments)
    2. env_settings (VERACITY_* environment variables)
    3. legacy_env_settings (NEO4J_*, EMBED_MODEL, etc.)
    4. yaml_settings (config file)
    5. defaults (from model definitions)
    """
    neo4j: Neo4jConfig = Field(default_factory=Neo4jConfig)
    embedding: EmbeddingConfig = Field(default_factory=EmbeddingConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    project: ProjectConfig = Field(default_factory=ProjectConfig)

    model_config = SettingsConfigDict(
        env_prefix="VERACITY_",
        env_nested_delimiter="__",
        extra="ignore",
        case_sensitive=False,
    )

    # Class variable to store YAML config file path
    _config_file: Optional[str] = None

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        """
        Customize settings sources for hierarchical configuration.

        Order (highest to lowest priority):
        1. init_settings - CLI arguments passed to constructor
        2. env_settings - VERACITY_* environment variables
        3. legacy_env - Legacy NEO4J_*, EMBED_MODEL variables
        4. yaml_settings - Configuration file
        """
        yaml_source = YamlConfigSettingsSource(settings_cls, cls._config_file)
        legacy_env_source = LegacyEnvSettingsSource(settings_cls)

        return (
            init_settings,       # Highest priority: CLI args
            env_settings,        # VERACITY_* env vars
            legacy_env_source,   # Legacy env vars (NEO4J_*, etc.)
            yaml_source,         # Config file
            # Defaults are handled by model Field definitions
        )


class ConfigLoader:
    """
    Configuration loader with singleton pattern.

    Usage:
        # Load with defaults
        config = ConfigLoader.load()

        # Load with config file
        config = ConfigLoader.load(config_file="config.yaml")

        # Load with CLI overrides
        config = ConfigLoader.load(neo4j_uri="bolt://custom:7687")

        # Get singleton instance
        config = ConfigLoader.get()

        # Reload configuration
        ConfigLoader.reload()
    """
    _instance: Optional[VeracityConfig] = None
    _config_file: Optional[str] = None
    _cli_overrides: Dict[str, Any] = {}

    @classmethod
    def load(
        cls,
        config_file: Optional[str] = None,
        **cli_overrides: Any
    ) -> VeracityConfig:
        """
        Load configuration with hierarchical resolution.

        Args:
            config_file: Path to YAML configuration file
            **cli_overrides: CLI argument overrides (neo4j_uri, neo4j_user, etc.)

        Returns:
            VeracityConfig instance
        """
        # Store for singleton pattern
        cls._config_file = config_file
        cls._cli_overrides = cli_overrides

        # Set config file for settings source
        ConfigSettings._config_file = config_file

        # Build init kwargs from CLI overrides
        init_kwargs = cls._build_init_kwargs(cli_overrides)

        # Create settings instance
        settings = ConfigSettings(**init_kwargs)

        # Convert to VeracityConfig
        config = VeracityConfig(
            neo4j=settings.neo4j,
            embedding=settings.embedding,
            llm=settings.llm,
            logging=settings.logging,
            project=settings.project
        )

        # Cache as singleton
        cls._instance = config

        logger.debug(f"Configuration loaded (file={config_file})")
        return config

    @classmethod
    def _build_init_kwargs(cls, cli_overrides: Dict[str, Any]) -> Dict[str, Any]:
        """Build initialization kwargs from CLI overrides."""
        result: Dict[str, Any] = {}

        # Map flat CLI args to nested structure
        # Format: section_field -> section.field
        mappings = {
            "neo4j_uri": ("neo4j", "uri"),
            "neo4j_user": ("neo4j", "user"),
            "neo4j_password": ("neo4j", "password"),
            "embedding_model": ("embedding", "model"),
            "llm_model": ("llm", "model"),
            "llm_seed": ("llm", "seed"),
            "logging_level": ("logging", "level"),
        }

        for key, value in cli_overrides.items():
            if value is None:
                continue

            if key in mappings:
                section, field = mappings[key]
                if section not in result:
                    result[section] = {}
                result[section][field] = value

        return result

    @classmethod
    def get(cls) -> VeracityConfig:
        """
        Get singleton configuration instance.

        Loads with defaults if not already loaded.

        Returns:
            VeracityConfig instance
        """
        if cls._instance is None:
            return cls.load(cls._config_file, **cls._cli_overrides)
        return cls._instance

    @classmethod
    def reload(cls) -> VeracityConfig:
        """
        Reload configuration, refreshing from all sources.

        Returns:
            New VeracityConfig instance
        """
        cls._instance = None
        return cls.load(cls._config_file, **cls._cli_overrides)


# Convenience function for getting config
def get_config() -> VeracityConfig:
    """Get the singleton configuration instance."""
    return ConfigLoader.get()


# =============================================================================
# Security Functions (STORY-003)
# =============================================================================

def validate_secrets(config: VeracityConfig, strict: bool = False) -> list[str]:
    """
    Validate secrets in configuration for security issues.

    Args:
        config: The configuration to validate
        strict: If True, raise ConfigSecurityError for any issue. If False, just warn.

    Returns:
        List of warning messages for any issues found.

    Raises:
        ConfigSecurityError: If strict mode and critical security issue found.
    """
    issues: list[str] = []

    # Get the actual password value
    password = config.neo4j.password.get_secret_value()

    # Check for default insecure passwords
    if password.lower() in DEFAULT_INSECURE_PASSWORDS:
        msg = (
            f"Neo4j password is set to a known insecure default ('{password}'). "
            "This is not suitable for production. Set a secure password via "
            "NEO4J_PASSWORD environment variable or config file."
        )
        issues.append(msg)
        logger.warning(msg)

    # Check minimum password length
    if len(password) < MINIMUM_PASSWORD_LENGTH:
        msg = (
            f"Neo4j password is too short ({len(password)} chars). "
            f"Minimum recommended length is {MINIMUM_PASSWORD_LENGTH} characters."
        )
        issues.append(msg)
        if strict:
            raise ConfigSecurityError(msg)
        logger.warning(msg)

    if not issues:
        logger.debug("Secret validation passed - no security issues detected")

    return issues


def check_env_file_permissions(env_path: str) -> bool:
    """
    Check if .env file has secure permissions.

    On Unix systems, .env files should only be readable by the owner (mode 600).
    Files that are world or group readable will trigger a warning.

    Args:
        env_path: Path to the .env file

    Returns:
        True if permissions are secure, False otherwise.

    Raises:
        UserWarning: If file permissions are too open.
    """
    path = Path(env_path)
    if not path.exists():
        return True  # Non-existent file is not a security issue

    # Get file mode
    file_stat = path.stat()
    mode = file_stat.st_mode

    # Check if group or others have read permission
    group_readable = bool(mode & stat.S_IRGRP)
    others_readable = bool(mode & stat.S_IROTH)

    if group_readable or others_readable:
        msg = (
            f"Environment file '{env_path}' has insecure permissions (mode {oct(mode & 0o777)}). "
            "It should only be readable by the owner (mode 600). "
            "Run: chmod 600 " + str(env_path)
        )
        warnings.warn(msg, UserWarning)
        logger.warning(msg)
        return False

    logger.debug(f"Environment file permissions OK: {env_path}")
    return True


def redact_config(config: VeracityConfig) -> Dict[str, Any]:
    """
    Get a redacted version of config suitable for logging.

    All SecretStr values are replaced with '****REDACTED****'.

    Args:
        config: The configuration to redact

    Returns:
        Dictionary with secrets redacted
    """
    data = config.model_dump()

    # Redact Neo4j password
    if "neo4j" in data and "password" in data["neo4j"]:
        data["neo4j"]["password"] = "****REDACTED****"

    return data


def log_config_summary(config: VeracityConfig) -> None:
    """
    Log a summary of the configuration (with secrets redacted).

    Args:
        config: The configuration to log
    """
    logger.info("Configuration loaded:")
    logger.info(f"  Neo4j: {config.neo4j.uri} (user: {config.neo4j.user})")
    logger.info(f"  Embedding: {config.embedding.model}")
    logger.info(f"  LLM: {config.llm.model} (seed: {config.llm.seed}, temp: {config.llm.temperature})")
    logger.info(f"  Logging: {config.logging.level}")
