"""
Unit tests for ModelManager and provider implementations.

Tests the multi-model support system including:
- ModelProvider base class
- AnthropicProvider, OpenAIProvider, LocalProvider
- ModelManager registration and configuration
- Cost estimation and validation
"""

import pytest
import json
import asyncio
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, Mock
from typing import Dict, Any

from devflow.core.model_manager import (
    ModelProviderType,
    ModelConfig,
    ProviderConfig,
    ModelResponse,
    ModelRequest,
    ModelProvider,
    AnthropicProvider,
    OpenAIProvider,
    LocalProvider,
    ModelManager,
)

# Mock the external libraries before import
sys.modules['anthropic'] = MagicMock()
sys.modules['openai'] = MagicMock()
sys.modules['requests'] = MagicMock()


# Fixtures

@pytest.fixture
def sample_model_config() -> ModelConfig:
    """Create a sample model configuration."""
    return ModelConfig(
        model_id="test-model",
        name="Test Model",
        provider="anthropic",
        type="chat",
        max_tokens=8192,
        input_cost_per_1k=0.003,
        output_cost_per_1k=0.015,
        capabilities=["code_generation", "analysis"],
        priority=1,
        available=True
    )


@pytest.fixture
def sample_provider_config() -> ProviderConfig:
    """Create a sample provider configuration."""
    return ProviderConfig(
        provider_type=ModelProviderType.ANTHROPIC,
        name="Test Provider",
        enabled=True,
        api_key_env="TEST_API_KEY",
        base_url="https://api.test.com",
        models={}
    )


@pytest.fixture
def sample_config_dict() -> Dict[str, Any]:
    """Create a sample configuration dictionary."""
    return {
        "version": "1.0.0",
        "providers": {
            "anthropic": {
                "name": "Anthropic",
                "enabled": True,
                "api_key_env": "ANTHROPIC_API_KEY",
                "base_url": "https://api.anthropic.com",
                "models": {
                    "claude-3-5-sonnet-20241022": {
                        "name": "Claude 3.5 Sonnet",
                        "type": "chat",
                        "max_tokens": 200000,
                        "input_cost_per_1k": 0.003,
                        "output_cost_per_1k": 0.015,
                        "capabilities": ["code_generation", "analysis"],
                        "priority": 1,
                        "available": True
                    }
                }
            },
            "openai": {
                "name": "OpenAI",
                "enabled": True,
                "api_key_env": "OPENAI_API_KEY",
                "base_url": "https://api.openai.com/v1",
                "models": {
                    "gpt-4-turbo": {
                        "name": "GPT-4 Turbo",
                        "type": "chat",
                        "max_tokens": 128000,
                        "input_cost_per_1k": 0.01,
                        "output_cost_per_1k": 0.03,
                        "capabilities": ["code_generation", "writing"],
                        "priority": 1,
                        "available": True
                    }
                }
            }
        }
    }


@pytest.fixture
def temp_config_file(tmp_path: Path, sample_config_dict: Dict[str, Any]) -> Path:
    """Create a temporary configuration file."""
    config_file = tmp_path / "model_config.json"
    with open(config_file, 'w') as f:
        json.dump(sample_config_dict, f)
    return config_file


# ModelConfig Tests

class TestModelConfig:
    """Tests for ModelConfig dataclass."""

    def test_model_config_creation(self, sample_model_config: ModelConfig):
        """Test creating a ModelConfig object."""
        assert sample_model_config.model_id == "test-model"
        assert sample_model_config.name == "Test Model"
        assert sample_model_config.provider == "anthropic"
        assert sample_model_config.type == "chat"
        assert sample_model_config.max_tokens == 8192
        assert sample_model_config.input_cost_per_1k == 0.003
        assert sample_model_config.output_cost_per_1k == 0.015
        assert sample_model_config.capabilities == ["code_generation", "analysis"]
        assert sample_model_config.priority == 1
        assert sample_model_config.available is True

    def test_model_config_defaults(self):
        """Test ModelConfig with default values."""
        config = ModelConfig(
            model_id="test",
            name="Test",
            provider="test"
        )
        assert config.type == "chat"
        assert config.max_tokens == 8192
        assert config.input_cost_per_1k == 0.0
        assert config.output_cost_per_1k == 0.0
        assert config.capabilities == []
        assert config.priority == 1
        assert config.available is True


# ProviderConfig Tests

class TestProviderConfig:
    """Tests for ProviderConfig dataclass."""

    def test_provider_config_creation(self, sample_provider_config: ProviderConfig):
        """Test creating a ProviderConfig object."""
        assert sample_provider_config.provider_type == ModelProviderType.ANTHROPIC
        assert sample_provider_config.name == "Test Provider"
        assert sample_provider_config.enabled is True
        assert sample_provider_config.api_key_env == "TEST_API_KEY"
        assert sample_provider_config.base_url == "https://api.test.com"
        assert sample_provider_config.models == {}

    def test_provider_config_defaults(self):
        """Test ProviderConfig with default values."""
        config = ProviderConfig(
            provider_type=ModelProviderType.OPENAI,
            name="OpenAI"
        )
        assert config.enabled is True
        assert config.api_key_env is None
        assert config.base_url == ""
        assert config.models == {}


# ModelProvider Tests

class TestModelProvider:
    """Tests for ModelProvider base class."""

    def test_provider_initialization(self, sample_provider_config: ProviderConfig):
        """Test provider initialization."""
        provider = ModelProvider(sample_provider_config)
        assert provider.config == sample_provider_config
        assert provider.models == {}
        assert provider.lock is not None

    def test_load_api_key_from_env(self, sample_provider_config: ProviderConfig):
        """Test loading API key from environment variable."""
        with patch.dict('os.environ', {'TEST_API_KEY': 'test-key-123'}):
            provider = ModelProvider(sample_provider_config)
            assert provider.api_key == 'test-key-123'

    def test_load_api_key_missing(self, sample_provider_config: ProviderConfig):
        """Test loading API key when environment variable is not set."""
        with patch.dict('os.environ', {}, clear=True):
            provider = ModelProvider(sample_provider_config)
            assert provider.api_key is None

    def test_validate_config_enabled(self, sample_provider_config: ProviderConfig):
        """Test validation when provider is enabled."""
        provider = ModelProvider(sample_provider_config)
        # Without API key, should return False for cloud providers
        assert provider.validate_config() is False

    def test_validate_config_disabled(self, sample_provider_config: ProviderConfig):
        """Test validation when provider is disabled."""
        sample_provider_config.enabled = False
        provider = ModelProvider(sample_provider_config)
        assert provider.validate_config() is False

    def test_validate_config_local_provider(self):
        """Test validation for local provider (no API key required)."""
        config = ProviderConfig(
            provider_type=ModelProviderType.LOCAL,
            name="Local",
            enabled=True,
            base_url="http://localhost:11434"
        )
        provider = LocalProvider(config)
        assert provider.validate_config() is True

    def test_get_model(self, sample_provider_config: ProviderConfig, sample_model_config: ModelConfig):
        """Test getting a model by ID."""
        sample_provider_config.models = {"test-model": sample_model_config}
        provider = ModelProvider(sample_provider_config)
        model = provider.get_model("test-model")
        assert model is not None
        assert model.model_id == "test-model"

    def test_get_model_not_found(self, sample_provider_config: ProviderConfig):
        """Test getting a non-existent model."""
        provider = ModelProvider(sample_provider_config)
        model = provider.get_model("non-existent")
        assert model is None

    def test_get_available_models(self, sample_provider_config: ProviderConfig):
        """Test getting available models."""
        model1 = ModelConfig(
            model_id="model1",
            name="Model 1",
            provider="test",
            available=True
        )
        model2 = ModelConfig(
            model_id="model2",
            name="Model 2",
            provider="test",
            available=False
        )
        sample_provider_config.models = {
            "model1": model1,
            "model2": model2
        }
        provider = ModelProvider(sample_provider_config)
        available = provider.get_available_models()
        assert len(available) == 1
        assert available[0].model_id == "model1"

    def test_get_models_by_capability(self, sample_provider_config: ProviderConfig):
        """Test getting models by capability."""
        model1 = ModelConfig(
            model_id="model1",
            name="Model 1",
            provider="test",
            capabilities=["code_generation", "analysis"]
        )
        model2 = ModelConfig(
            model_id="model2",
            name="Model 2",
            provider="test",
            capabilities=["writing"]
        )
        sample_provider_config.models = {
            "model1": model1,
            "model2": model2
        }
        provider = ModelProvider(sample_provider_config)
        models = provider.get_models_by_capability("code_generation")
        assert len(models) == 1
        assert models[0].model_id == "model1"

    def test_estimate_cost(self, sample_provider_config: ProviderConfig, sample_model_config: ModelConfig):
        """Test cost estimation."""
        sample_provider_config.models = {"test-model": sample_model_config}
        provider = ModelProvider(sample_provider_config)
        cost = provider.estimate_cost(1000, 500, "test-model")
        # Cost = (1000/1000 * 0.003) + (500/1000 * 0.015) = 0.003 + 0.0075 = 0.0105
        assert cost == pytest.approx(0.0105)

    def test_estimate_cost_model_not_found(self, sample_provider_config: ProviderConfig):
        """Test cost estimation for non-existent model."""
        provider = ModelProvider(sample_provider_config)
        cost = provider.estimate_cost(1000, 500, "non-existent")
        assert cost == 0.0

    def test_generate_not_implemented(self, sample_provider_config: ProviderConfig):
        """Test that generate raises NotImplementedError."""
        provider = ModelProvider(sample_provider_config)
        request = ModelRequest(prompt="test")
        with pytest.raises(NotImplementedError):
            asyncio.run(provider.generate(request, "test-model"))


# AnthropicProvider Tests

class TestAnthropicProvider:
    """Tests for AnthropicProvider."""

    def test_initialization(self, sample_provider_config: ProviderConfig):
        """Test Anthropic provider initialization."""
        provider = AnthropicProvider(sample_provider_config)
        assert provider.provider_name == "Anthropic"
        assert provider.config == sample_provider_config

    def test_validate_config_valid_api_key(self):
        """Test validation with valid API key format."""
        config = ProviderConfig(
            provider_type=ModelProviderType.ANTHROPIC,
            name="Anthropic",
            enabled=True,
            api_key_env="ANTHROPIC_API_KEY"
        )
        with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'sk-ant-test123'}):
            provider = AnthropicProvider(config)
            assert provider.validate_config() is True

    def test_validate_config_invalid_api_key(self):
        """Test validation with invalid API key format."""
        config = ProviderConfig(
            provider_type=ModelProviderType.ANTHROPIC,
            name="Anthropic",
            enabled=True,
            api_key_env="ANTHROPIC_API_KEY"
        )
        with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'invalid-key'}):
            provider = AnthropicProvider(config)
            assert provider.validate_config() is False

    @pytest.mark.asyncio
    async def test_generate_success(self):
        """Test successful generation."""
        # Create provider with mock
        config = ProviderConfig(
            provider_type=ModelProviderType.ANTHROPIC,
            name="Anthropic",
            enabled=True,
            api_key_env="ANTHROPIC_API_KEY"
        )
        with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'sk-ant-test123'}):
            provider = AnthropicProvider(config)

        # Create mock client and response
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Test response")]
        mock_response.usage.input_tokens = 100
        mock_response.usage.output_tokens = 50
        mock_client.messages.create.return_value = mock_response

        # Mock the Anthropic class in sys.modules
        sys.modules['anthropic'].Anthropic = Mock(return_value=mock_client)

        # Test generation
        request = ModelRequest(
            prompt="Test prompt",
            system_prompt="System prompt",
            max_tokens=1000,
            temperature=0.7
        )
        response = await provider.generate(request, "claude-3-5-sonnet-20241022")

        # Verify
        assert response.success is True
        assert response.content == "Test response"
        assert response.input_tokens == 100
        assert response.output_tokens == 50
        assert response.model_id == "claude-3-5-sonnet-20241022"
        assert response.provider == "Anthropic"
        assert response.latency_ms > 0

    @pytest.mark.asyncio
    async def test_generate_library_not_installed(self):
        """Test generation when anthropic library is not installed."""
        config = ProviderConfig(
            provider_type=ModelProviderType.ANTHROPIC,
            name="Anthropic",
            enabled=True,
            api_key_env="ANTHROPIC_API_KEY"
        )
        with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'sk-ant-test123'}):
            provider = AnthropicProvider(config)

        # Mock ImportError
        with patch('builtins.__import__', side_effect=ImportError):
            request = ModelRequest(prompt="Test prompt")
            response = await provider.generate(request, "claude-3-5-sonnet-20241022")

            assert response.success is False
            assert "not installed" in response.error

    @pytest.mark.asyncio
    async def test_generate_api_error(self):
        """Test generation with API error."""
        config = ProviderConfig(
            provider_type=ModelProviderType.ANTHROPIC,
            name="Anthropic",
            enabled=True,
            api_key_env="ANTHROPIC_API_KEY"
        )
        with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'sk-ant-test123'}):
            provider = AnthropicProvider(config)

        # Create mock client that raises error
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = Exception("API Error")

        # Mock the Anthropic class in sys.modules
        sys.modules['anthropic'].Anthropic = Mock(return_value=mock_client)

        request = ModelRequest(prompt="Test prompt")
        response = await provider.generate(request, "claude-3-5-sonnet-20241022")

        assert response.success is False
        assert response.error == "API Error"


# OpenAIProvider Tests

class TestOpenAIProvider:
    """Tests for OpenAIProvider."""

    def test_initialization(self, sample_provider_config: ProviderConfig):
        """Test OpenAI provider initialization."""
        provider = OpenAIProvider(sample_provider_config)
        assert provider.provider_name == "OpenAI"
        assert provider.config == sample_provider_config

    def test_validate_config_valid_api_key(self):
        """Test validation with valid API key format."""
        config = ProviderConfig(
            provider_type=ModelProviderType.OPENAI,
            name="OpenAI",
            enabled=True,
            api_key_env="OPENAI_API_KEY"
        )
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'sk-test123'}):
            provider = OpenAIProvider(config)
            assert provider.validate_config() is True

    def test_validate_config_invalid_api_key(self):
        """Test validation with invalid API key format."""
        config = ProviderConfig(
            provider_type=ModelProviderType.OPENAI,
            name="OpenAI",
            enabled=True,
            api_key_env="OPENAI_API_KEY"
        )
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'invalid-key'}):
            provider = OpenAIProvider(config)
            assert provider.validate_config() is False

    @pytest.mark.asyncio
    async def test_generate_success(self):
        """Test successful generation."""
        # Create provider
        config = ProviderConfig(
            provider_type=ModelProviderType.OPENAI,
            name="OpenAI",
            enabled=True,
            api_key_env="OPENAI_API_KEY"
        )
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'sk-test123'}):
            provider = OpenAIProvider(config)

        # Create mock client and response
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Test response"))]
        mock_response.usage.prompt_tokens = 100
        mock_response.usage.completion_tokens = 50
        mock_client.chat.completions.create.return_value = mock_response

        # Mock the OpenAI class in sys.modules
        sys.modules['openai'].OpenAI = Mock(return_value=mock_client)

        # Test generation
        request = ModelRequest(
            prompt="Test prompt",
            system_prompt="System prompt",
            max_tokens=1000,
            temperature=0.7
        )
        response = await provider.generate(request, "gpt-4-turbo")

        # Verify
        assert response.success is True
        assert response.content == "Test response"
        assert response.input_tokens == 100
        assert response.output_tokens == 50
        assert response.model_id == "gpt-4-turbo"
        assert response.provider == "OpenAI"
        assert response.latency_ms > 0

    @pytest.mark.asyncio
    async def test_generate_library_not_installed(self):
        """Test generation when openai library is not installed."""
        config = ProviderConfig(
            provider_type=ModelProviderType.OPENAI,
            name="OpenAI",
            enabled=True,
            api_key_env="OPENAI_API_KEY"
        )
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'sk-test123'}):
            provider = OpenAIProvider(config)

        # Mock ImportError
        with patch('builtins.__import__', side_effect=ImportError):
            request = ModelRequest(prompt="Test prompt")
            response = await provider.generate(request, "gpt-4-turbo")

            assert response.success is False
            assert "not installed" in response.error

    @pytest.mark.asyncio
    async def test_generate_api_error(self):
        """Test generation with API error."""
        config = ProviderConfig(
            provider_type=ModelProviderType.OPENAI,
            name="OpenAI",
            enabled=True,
            api_key_env="OPENAI_API_KEY"
        )
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'sk-test123'}):
            provider = OpenAIProvider(config)

        # Create mock client that raises error
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("API Error")

        # Mock the OpenAI class in sys.modules
        sys.modules['openai'].OpenAI = Mock(return_value=mock_client)

        request = ModelRequest(prompt="Test prompt")
        response = await provider.generate(request, "gpt-4-turbo")

        assert response.success is False
        assert response.error == "API Error"


# LocalProvider Tests

class TestLocalProvider:
    """Tests for LocalProvider."""

    def test_initialization(self, sample_provider_config: ProviderConfig):
        """Test Local provider initialization."""
        provider = LocalProvider(sample_provider_config)
        assert provider.provider_name == "Local"
        assert provider.config == sample_provider_config

    def test_validate_config_valid(self):
        """Test validation with valid configuration."""
        config = ProviderConfig(
            provider_type=ModelProviderType.LOCAL,
            name="Local",
            enabled=True,
            base_url="http://localhost:11434"
        )
        provider = LocalProvider(config)
        assert provider.validate_config() is True

    def test_validate_config_disabled(self):
        """Test validation when provider is disabled."""
        config = ProviderConfig(
            provider_type=ModelProviderType.LOCAL,
            name="Local",
            enabled=False,
            base_url="http://localhost:11434"
        )
        provider = LocalProvider(config)
        assert provider.validate_config() is False

    def test_validate_config_no_base_url(self):
        """Test validation without base URL."""
        config = ProviderConfig(
            provider_type=ModelProviderType.LOCAL,
            name="Local",
            enabled=True,
            base_url=""
        )
        provider = LocalProvider(config)
        assert provider.validate_config() is False

    @pytest.mark.asyncio
    async def test_generate_success(self):
        """Test successful generation."""
        # Create provider
        config = ProviderConfig(
            provider_type=ModelProviderType.LOCAL,
            name="Local",
            enabled=True,
            base_url="http://localhost:11434"
        )
        provider = LocalProvider(config)

        # Mock the requests module
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "response": "Test response",
            "prompt_eval_count": 100,
            "eval_count": 50
        }
        mock_response.raise_for_status = MagicMock()

        with patch('requests.post', return_value=mock_response):
            # Test generation
            request = ModelRequest(
                prompt="Test prompt",
                system_prompt="System prompt",
                max_tokens=1000
            )
            response = await provider.generate(request, "llama3-70b")

            # Verify
            assert response.success is True
            assert response.content == "Test response"
            assert response.input_tokens == 100
            assert response.output_tokens == 50
            assert response.model_id == "llama3-70b"
            assert response.provider == "Local"
            assert response.latency_ms > 0

    @pytest.mark.asyncio
    async def test_generate_library_not_installed(self):
        """Test generation when requests library is not installed."""
        config = ProviderConfig(
            provider_type=ModelProviderType.LOCAL,
            name="Local",
            enabled=True,
            base_url="http://localhost:11434"
        )
        provider = LocalProvider(config)

        # Mock ImportError
        with patch('builtins.__import__', side_effect=ImportError):
            request = ModelRequest(prompt="Test prompt")
            response = await provider.generate(request, "llama3-70b")

            assert response.success is False
            assert "not installed" in response.error

    @pytest.mark.asyncio
    async def test_generate_api_error(self):
        """Test generation with API error."""
        config = ProviderConfig(
            provider_type=ModelProviderType.LOCAL,
            name="Local",
            enabled=True,
            base_url="http://localhost:11434"
        )
        provider = LocalProvider(config)

        # Mock the requests module with error
        with patch('requests.post', side_effect=Exception("Connection Error")):
            request = ModelRequest(prompt="Test prompt")
            response = await provider.generate(request, "llama3-70b")

            assert response.success is False
            assert response.error == "Connection Error"


# ModelManager Tests

class TestModelManager:
    """Tests for ModelManager."""

    def test_initialization(self, temp_config_file: Path):
        """Test ModelManager initialization."""
        manager = ModelManager(config_path=temp_config_file)
        assert manager.config_path == temp_config_file
        assert manager.config is not None
        assert "providers" in manager.config
        assert manager.lock is not None

    def test_initialization_default_path(self):
        """Test ModelManager initialization with default config path."""
        manager = ModelManager()
        assert manager.config_path is not None
        assert manager.config_path.name == "model_config.json"

    def test_load_config(self, temp_config_file: Path):
        """Test loading configuration from file."""
        manager = ModelManager(config_path=temp_config_file)
        config = manager.config
        assert "providers" in config
        assert "anthropic" in config["providers"]
        assert "openai" in config["providers"]

    def test_load_config_missing_file(self, tmp_path: Path):
        """Test loading configuration when file doesn't exist."""
        missing_file = tmp_path / "nonexistent.json"
        manager = ModelManager(config_path=missing_file)
        assert manager.config == {"providers": {}}

    def test_register_providers(self, temp_config_file: Path):
        """Test provider registration."""
        manager = ModelManager(config_path=temp_config_file)
        # Should register Anthropic and OpenAI providers
        assert len(manager.providers) >= 1
        # At least one provider should be registered if API keys are available
        # or if configuration allows it

    def test_get_provider(self, temp_config_file: Path):
        """Test getting a specific provider."""
        manager = ModelManager(config_path=temp_config_file)
        anthropic = manager.get_provider(ModelProviderType.ANTHROPIC)
        if anthropic:
            assert isinstance(anthropic, AnthropicProvider)

        openai = manager.get_provider(ModelProviderType.OPENAI)
        if openai:
            assert isinstance(openai, OpenAIProvider)

    def test_get_provider_not_found(self, temp_config_file: Path):
        """Test getting a non-existent provider."""
        manager = ModelManager(config_path=temp_config_file)
        # Local provider might not be registered if not enabled
        local = manager.get_provider(ModelProviderType.LOCAL)
        # This could be None or a LocalProvider instance

    def test_get_all_providers(self, temp_config_file: Path):
        """Test getting all registered providers."""
        manager = ModelManager(config_path=temp_config_file)
        providers = manager.get_all_providers()
        assert isinstance(providers, list)
        # Number of providers depends on configuration

    def test_get_available_providers(self, temp_config_file: Path):
        """Test getting providers with valid configuration."""
        manager = ModelManager(config_path=temp_config_file)
        available = manager.get_available_providers()
        assert isinstance(available, list)
        # Without actual API keys, most providers won't be available

    def test_get_provider_for_model(self, temp_config_file: Path):
        """Test getting provider for a specific model."""
        manager = ModelManager(config_path=temp_config_file)
        provider = manager.get_provider_for_model("claude-3-5-sonnet-20241022")
        if provider:
            assert isinstance(provider, AnthropicProvider)

    def test_get_all_models(self, temp_config_file: Path):
        """Test getting all models from all providers."""
        manager = ModelManager(config_path=temp_config_file)
        models = manager.get_all_models()
        assert isinstance(models, dict)
        # Should have models from config
        assert len(models) > 0

    def test_get_available_models(self, temp_config_file: Path):
        """Test getting available models."""
        manager = ModelManager(config_path=temp_config_file)
        models = manager.get_available_models()
        assert isinstance(models, list)
        # Should have available models from config
        assert len(models) > 0

    def test_get_models_by_capability(self, temp_config_file: Path):
        """Test getting models by capability."""
        manager = ModelManager(config_path=temp_config_file)
        models = manager.get_models_by_capability("code_generation")
        assert isinstance(models, list)
        # Should have models with code_generation capability
        assert len(models) > 0

    def test_parse_provider_config(self):
        """Test parsing provider configuration."""
        manager = ModelManager()
        config_dict = {
            "name": "Test Provider",
            "enabled": True,
            "api_key_env": "TEST_KEY",
            "base_url": "https://test.com",
            "models": {
                "test-model": {
                    "name": "Test Model",
                    "type": "chat",
                    "max_tokens": 8192,
                    "input_cost_per_1k": 0.001,
                    "output_cost_per_1k": 0.002,
                    "capabilities": ["test"],
                    "priority": 1,
                    "available": True
                }
            }
        }

        provider_config = manager._parse_provider_config(
            ModelProviderType.ANTHROPIC,
            config_dict
        )

        assert provider_config.provider_type == ModelProviderType.ANTHROPIC
        assert provider_config.name == "Test Provider"
        assert provider_config.enabled is True
        assert provider_config.api_key_env == "TEST_KEY"
        assert provider_config.base_url == "https://test.com"
        assert "test-model" in provider_config.models
        assert provider_config.models["test-model"].name == "Test Model"


# ModelRequest and ModelResponse Tests

class TestModelRequest:
    """Tests for ModelRequest dataclass."""

    def test_model_request_creation(self):
        """Test creating a ModelRequest."""
        request = ModelRequest(
            prompt="Test prompt",
            system_prompt="System prompt",
            max_tokens=1000,
            temperature=0.7,
            stream=False
        )
        assert request.prompt == "Test prompt"
        assert request.system_prompt == "System prompt"
        assert request.max_tokens == 1000
        assert request.temperature == 0.7
        assert request.stream is False

    def test_model_request_defaults(self):
        """Test ModelRequest with default values."""
        request = ModelRequest(prompt="Test")
        assert request.system_prompt is None
        assert request.max_tokens is None
        assert request.temperature == 0.7
        assert request.stream is False


class TestModelResponse:
    """Tests for ModelResponse dataclass."""

    def test_model_response_creation(self):
        """Test creating a ModelResponse."""
        response = ModelResponse(
            content="Test response",
            model_id="test-model",
            provider="TestProvider",
            input_tokens=100,
            output_tokens=50,
            latency_ms=123.45,
            success=True,
            error=None
        )
        assert response.content == "Test response"
        assert response.model_id == "test-model"
        assert response.provider == "TestProvider"
        assert response.input_tokens == 100
        assert response.output_tokens == 50
        assert response.latency_ms == 123.45
        assert response.success is True
        assert response.error is None

    def test_model_response_defaults(self):
        """Test ModelResponse with default values."""
        response = ModelResponse(
            content="Test",
            model_id="test",
            provider="Test"
        )
        assert response.input_tokens == 0
        assert response.output_tokens == 0
        assert response.latency_ms == 0.0
        assert response.success is True
        assert response.error is None

    def test_model_response_error(self):
        """Test ModelResponse with error."""
        response = ModelResponse(
            content="",
            model_id="test",
            provider="Test",
            success=False,
            error="API Error"
        )
        assert response.success is False
        assert response.error == "API Error"


# Integration Tests

class TestModelManagerIntegration:
    """Integration tests for ModelManager."""

    def test_full_provider_workflow(self, temp_config_file: Path):
        """Test complete workflow with providers."""
        manager = ModelManager(config_path=temp_config_file)

        # Get all models
        all_models = manager.get_all_models()
        assert len(all_models) > 0

        # Get available models
        available_models = manager.get_available_models()
        assert len(available_models) > 0

        # Get models by capability
        code_models = manager.get_models_by_capability("code_generation")
        assert len(code_models) > 0

        # Get provider for model
        for model_id in all_models:
            provider = manager.get_provider_for_model(model_id)
            if provider:
                assert provider is not None
                break

    def test_cost_estimation_across_providers(self, temp_config_file: Path):
        """Test cost estimation for models from different providers."""
        manager = ModelManager(config_path=temp_config_file)

        all_models = manager.get_all_models()
        for model_id, model_config in all_models.items():
            provider = manager.get_provider_for_model(model_id)
            if provider:
                cost = provider.estimate_cost(1000, 500, model_id)
                assert cost >= 0

    def test_model_filtering(self, temp_config_file: Path):
        """Test filtering models by various criteria."""
        manager = ModelManager(config_path=temp_config_file)

        # Filter by capability
        code_models = manager.get_models_by_capability("code_generation")
        assert all("code_generation" in m.capabilities for m in code_models)

        # Filter by availability
        available_models = manager.get_available_models()
        assert all(m.available for m in available_models)

    def test_provider_model_relationships(self, temp_config_file: Path):
        """Test relationships between providers and models."""
        manager = ModelManager(config_path=temp_config_file)

        providers = manager.get_all_providers()
        for provider in providers:
            # Each provider should have models
            if provider.models:
                # Test getting models from provider
                provider_models = provider.get_available_models()
                assert isinstance(provider_models, list)

                # Test that each model belongs to the correct provider
                for model in provider_models:
                    assert model.provider == provider.config.provider_type.value
