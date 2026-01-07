"""
Unit tests for Model Version Control (STORY-002).

Tests model versioning, digest verification, and determinism features.
"""
import pytest
from unittest.mock import patch, MagicMock


class TestModelInfo:
    """Tests for ModelInfo dataclass."""

    def test_model_info_creation(self):
        """Should create ModelInfo with all fields."""
        from core.models import ModelInfo

        info = ModelInfo(
            name="nomic-embed-text:latest",
            digest="0a109f422b47abc123",
            size=274000000,
            modified_at="2025-12-27T00:00:00Z",
            details={"architecture": "nomic-bert"}
        )
        assert info.name == "nomic-embed-text:latest"
        assert info.digest == "0a109f422b47abc123"
        assert info.size == 274000000

    def test_short_digest(self):
        """Should return first 12 chars of digest."""
        from core.models import ModelInfo

        info = ModelInfo(
            name="test-model",
            digest="0a109f422b47abc123def456",
            size=0,
            modified_at="",
            details={}
        )
        assert info.short_digest == "0a109f422b47"

    def test_short_digest_empty(self):
        """Should handle empty digest."""
        from core.models import ModelInfo

        info = ModelInfo(
            name="test-model",
            digest="",
            size=0,
            modified_at="",
            details={}
        )
        assert info.short_digest == ""


class TestGetModelInfo:
    """Tests for get_model_info function."""

    def test_get_model_info_found(self):
        """Should return ModelInfo when model exists."""
        from core.models import get_model_info

        mock_models = {
            'models': [
                {
                    'name': 'nomic-embed-text:latest',
                    'digest': '0a109f422b47',
                    'size': 274000000,
                    'modified_at': '2025-12-27T00:00:00Z',
                    'details': {}
                }
            ]
        }

        with patch('core.models.ollama.list', return_value=mock_models):
            info = get_model_info('nomic-embed-text')
            assert info is not None
            assert info.name == 'nomic-embed-text:latest'
            assert info.digest == '0a109f422b47'

    def test_get_model_info_not_found(self):
        """Should raise ModelNotFoundError when model doesn't exist."""
        from core.models import get_model_info, ModelNotFoundError

        mock_models = {'models': []}

        with patch('core.models.ollama.list', return_value=mock_models):
            with pytest.raises(ModelNotFoundError):
                get_model_info('nonexistent-model')

    def test_get_model_info_with_tag(self):
        """Should match model with tag."""
        from core.models import get_model_info

        mock_models = {
            'models': [
                {
                    'name': 'llama3.2:latest',
                    'digest': 'a80c4f17acd5',
                    'size': 2000000000,
                    'modified_at': '2025-12-27T00:00:00Z',
                    'details': {}
                }
            ]
        }

        with patch('core.models.ollama.list', return_value=mock_models):
            info = get_model_info('llama3.2')
            assert info is not None
            assert info.name == 'llama3.2:latest'


class TestVerifyModelDigest:
    """Tests for verify_model_digest function."""

    def test_verify_digest_match(self):
        """Should return True when digest matches."""
        from core.models import verify_model_digest, ModelInfo

        mock_info = ModelInfo(
            name='test-model',
            digest='0a109f422b47abc123',
            size=0,
            modified_at='',
            details={}
        )

        with patch('core.models.get_model_info', return_value=mock_info):
            result = verify_model_digest('test-model', '0a109f422b47')
            assert result is True

    def test_verify_digest_mismatch(self):
        """Should return False when digest doesn't match."""
        from core.models import verify_model_digest, ModelInfo

        mock_info = ModelInfo(
            name='test-model',
            digest='0a109f422b47abc123',
            size=0,
            modified_at='',
            details={}
        )

        with patch('core.models.get_model_info', return_value=mock_info):
            result = verify_model_digest('test-model', 'wrong_digest')
            assert result is False

    def test_verify_digest_with_sha256_prefix(self):
        """Should handle sha256: prefix in expected digest."""
        from core.models import verify_model_digest, ModelInfo

        mock_info = ModelInfo(
            name='test-model',
            digest='0a109f422b47abc123',
            size=0,
            modified_at='',
            details={}
        )

        with patch('core.models.get_model_info', return_value=mock_info):
            result = verify_model_digest('test-model', 'sha256:0a109f422b47')
            assert result is True

    def test_verify_digest_model_not_found(self):
        """Should raise error when model not found."""
        from core.models import verify_model_digest, ModelNotFoundError

        with patch('core.models.get_model_info', return_value=None):
            with pytest.raises(ModelNotFoundError):
                verify_model_digest('nonexistent', 'digest')


class TestVerifyModelsOnStartup:
    """Tests for verify_models_on_startup function."""

    def test_verify_models_success(self):
        """Should return True for all models when verification passes."""
        from core.models import verify_models_on_startup, ModelInfo
        from core.config import ConfigLoader

        # Create config with models
        config = ConfigLoader.load()

        mock_embed_info = ModelInfo(
            name='nomic-embed-text:latest',
            digest='0a109f422b47',
            size=274000000,
            modified_at='',
            details={}
        )
        mock_llm_info = ModelInfo(
            name='llama3.2:latest',
            digest='a80c4f17acd5',
            size=2000000000,
            modified_at='',
            details={}
        )

        def mock_get_model_info(name):
            if 'embed' in name.lower() or 'nomic' in name.lower():
                return mock_embed_info
            return mock_llm_info

        with patch('core.models.get_model_info', side_effect=mock_get_model_info):
            results = verify_models_on_startup(config)
            assert results.get('nomic-embed-text', False) is True
            assert results.get('llama3.2', False) is True


class TestGetAllModelDigests:
    """Tests for get_all_model_digests function."""

    def test_get_all_digests(self):
        """Should return all model digests."""
        from core.models import get_all_model_digests

        mock_models = {
            'models': [
                {'name': 'model1', 'digest': 'digest1'},
                {'name': 'model2', 'digest': 'digest2'},
            ]
        }

        with patch('core.models.ollama.list', return_value=mock_models):
            digests = get_all_model_digests()
            assert digests == {'model1': 'digest1', 'model2': 'digest2'}

    def test_get_all_digests_error(self):
        """Should return empty dict on error."""
        from core.models import get_all_model_digests

        with patch('core.models.ollama.list', side_effect=Exception("Connection error")):
            digests = get_all_model_digests()
            assert digests == {}


class TestConfigWithModelVersions:
    """Tests for config schema with model version fields."""

    def test_config_accepts_model_digest(self, tmp_path):
        """Config should accept model with digest."""
        from core.config import ConfigLoader

        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
embedding:
  model: "nomic-embed-text"
  version: "latest"
  digest: "0a109f422b47"
  verify_on_startup: true

llm:
  model: "llama3.2"
  version: "latest"
  digest: "a80c4f17acd5"
  verify_on_startup: false
""")
        config = ConfigLoader.load(config_file=str(config_file))
        assert config.embedding.digest == "0a109f422b47"
        assert config.embedding.verify_on_startup is True
        assert config.llm.digest == "a80c4f17acd5"
        assert config.llm.verify_on_startup is False

    def test_config_dimensions_field(self):
        """Config should have dimensions field for embeddings."""
        from core.config import ConfigLoader

        config = ConfigLoader.load()
        assert config.embedding.dimensions == 768

    def test_config_top_k_field(self):
        """Config should have top_k field for LLM."""
        from core.config import ConfigLoader

        config = ConfigLoader.load()
        assert config.llm.top_k == 1  # Default for deterministic output
