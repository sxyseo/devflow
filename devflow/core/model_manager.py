"""
Model Manager - Manages AI model providers and interactions.

Provides abstraction layer for multiple AI providers (Anthropic, OpenAI, local models).
"""

import os
import time
import threading
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field
from enum import Enum
import json
from pathlib import Path


class ModelProviderType(Enum):
    """Available model provider types."""
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    LOCAL = "local"


@dataclass
class ModelConfig:
    """Configuration for a specific model."""
    model_id: str
    name: str
    provider: str
    type: str = "chat"
    max_tokens: int = 8192
    input_cost_per_1k: float = 0.0
    output_cost_per_1k: float = 0.0
    capabilities: List[str] = field(default_factory=list)
    priority: int = 1
    available: bool = True


@dataclass
class ProviderConfig:
    """Configuration for a model provider."""
    provider_type: ModelProviderType
    name: str
    enabled: bool = True
    api_key_env: Optional[str] = None
    base_url: str = ""
    models: Dict[str, ModelConfig] = field(default_factory=dict)


@dataclass
class ModelResponse:
    """Response from a model provider."""
    content: str
    model_id: str
    provider: str
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: float = 0.0
    success: bool = True
    error: Optional[str] = None


@dataclass
class ModelRequest:
    """Request to a model provider."""
    prompt: str
    system_prompt: Optional[str] = None
    max_tokens: Optional[int] = None
    temperature: float = 0.7
    stream: bool = False


class ModelProvider:
    """
    Abstract base class for model providers.

    All model providers must implement these methods for consistent interaction.
    """

    def __init__(self, config: ProviderConfig):
        """
        Initialize the model provider.

        Args:
            config: Provider configuration
        """
        self.config = config
        self.api_key = self._load_api_key()
        self.models = config.models
        self.lock = threading.Lock()

    def _load_api_key(self) -> Optional[str]:
        """
        Load API key from environment variable.

        Returns:
            API key if available, None otherwise
        """
        if self.config.api_key_env:
            return os.getenv(self.config.api_key_env)
        return None

    def validate_config(self) -> bool:
        """
        Validate provider configuration.

        Returns:
            True if configuration is valid
        """
        if not self.config.enabled:
            return False

        # For local providers, API key is not required
        if self.config.provider_type == ModelProviderType.LOCAL:
            return True

        # For cloud providers, API key is required
        return self.api_key is not None

    def get_model(self, model_id: str) -> Optional[ModelConfig]:
        """
        Get model configuration.

        Args:
            model_id: Model identifier

        Returns:
            ModelConfig if found, None otherwise
        """
        return self.models.get(model_id)

    def get_available_models(self) -> List[ModelConfig]:
        """
        Get list of available models.

        Returns:
            List of available ModelConfig objects
        """
        return [
            model for model in self.models.values()
            if model.available
        ]

    def get_models_by_capability(self, capability: str) -> List[ModelConfig]:
        """
        Get models that support a specific capability.

        Args:
            capability: Capability to filter by

        Returns:
            List of ModelConfig objects with the capability
        """
        return [
            model for model in self.models.values()
            if model.available and capability in model.capabilities
        ]

    async def generate(self, request: ModelRequest, model_id: str) -> ModelResponse:
        """
        Generate a response from the model.

        Args:
            request: Model request
            model_id: Model to use

        Returns:
            ModelResponse

        Raises:
            NotImplementedError: This method must be implemented by subclasses
        """
        raise NotImplementedError("Subclasses must implement generate()")

    def estimate_cost(self, input_tokens: int, output_tokens: int, model_id: str) -> float:
        """
        Estimate cost for a request.

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            model_id: Model identifier

        Returns:
            Estimated cost in USD
        """
        model = self.get_model(model_id)
        if not model:
            return 0.0

        input_cost = (input_tokens / 1000) * model.input_cost_per_1k
        output_cost = (output_tokens / 1000) * model.output_cost_per_1k

        return input_cost + output_cost


class AnthropicProvider(ModelProvider):
    """
    Anthropic Claude model provider.

    Provides access to Claude 3 models (Sonnet, Opus, Haiku).
    """

    def __init__(self, config: ProviderConfig):
        """
        Initialize Anthropic provider.

        Args:
            config: Provider configuration
        """
        super().__init__(config)
        self.provider_name = "Anthropic"

    def validate_config(self) -> bool:
        """
        Validate Anthropic configuration.

        Returns:
            True if configuration is valid
        """
        if not super().validate_config():
            return False

        # Validate API key format (starts with sk-ant-)
        if self.api_key and not self.api_key.startswith("sk-ant-"):
            return False

        return True

    async def generate(self, request: ModelRequest, model_id: str) -> ModelResponse:
        """
        Generate a response using Anthropic's API.

        Args:
            request: Model request
            model_id: Model to use (e.g., claude-3-5-sonnet-20241022)

        Returns:
            ModelResponse
        """
        start_time = time.time()

        try:
            # Import anthropic library
            try:
                from anthropic import Anthropic
            except ImportError:
                return ModelResponse(
                    content="",
                    model_id=model_id,
                    provider=self.provider_name,
                    success=False,
                    error="anthropic library not installed. Install with: pip install anthropic"
                )

            # Create client
            client = Anthropic(api_key=self.api_key)

            # Prepare messages
            messages = [{"role": "user", "content": request.prompt}]

            # Prepare API parameters
            api_params = {
                "model": model_id,
                "messages": messages,
                "max_tokens": request.max_tokens or 4096,
                "temperature": request.temperature,
            }

            # Add system prompt if provided
            if request.system_prompt:
                api_params["system"] = request.system_prompt

            # Make API call
            response = client.messages.create(**api_params)

            # Extract response content
            content = response.content[0].text

            # Get token usage
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens

            # Calculate latency
            latency_ms = (time.time() - start_time) * 1000

            return ModelResponse(
                content=content,
                model_id=model_id,
                provider=self.provider_name,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                latency_ms=latency_ms,
                success=True
            )

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            return ModelResponse(
                content="",
                model_id=model_id,
                provider=self.provider_name,
                latency_ms=latency_ms,
                success=False,
                error=str(e)
            )


class OpenAIProvider(ModelProvider):
    """
    OpenAI model provider.

    Provides access to GPT-4 and GPT-3.5 models.
    """

    def __init__(self, config: ProviderConfig):
        """
        Initialize OpenAI provider.

        Args:
            config: Provider configuration
        """
        super().__init__(config)
        self.provider_name = "OpenAI"

    def validate_config(self) -> bool:
        """
        Validate OpenAI configuration.

        Returns:
            True if configuration is valid
        """
        if not super().validate_config():
            return False

        # Validate API key format (starts with sk-)
        if self.api_key and not self.api_key.startswith("sk-"):
            return False

        return True

    async def generate(self, request: ModelRequest, model_id: str) -> ModelResponse:
        """
        Generate a response using OpenAI's API.

        Args:
            request: Model request
            model_id: Model to use (e.g., gpt-4-turbo)

        Returns:
            ModelResponse
        """
        start_time = time.time()

        try:
            # Import openai library
            try:
                from openai import OpenAI
            except ImportError:
                return ModelResponse(
                    content="",
                    model_id=model_id,
                    provider=self.provider_name,
                    success=False,
                    error="openai library not installed. Install with: pip install openai"
                )

            # Create client
            client = OpenAI(api_key=self.api_key)

            # Prepare messages
            messages = []
            if request.system_prompt:
                messages.append({"role": "system", "content": request.system_prompt})
            messages.append({"role": "user", "content": request.prompt})

            # Prepare API parameters
            api_params = {
                "model": model_id,
                "messages": messages,
                "temperature": request.temperature,
            }

            # Add max_tokens if specified
            if request.max_tokens:
                api_params["max_tokens"] = request.max_tokens

            # Make API call
            response = client.chat.completions.create(**api_params)

            # Extract response content
            content = response.choices[0].message.content

            # Get token usage
            input_tokens = response.usage.prompt_tokens
            output_tokens = response.usage.completion_tokens

            # Calculate latency
            latency_ms = (time.time() - start_time) * 1000

            return ModelResponse(
                content=content,
                model_id=model_id,
                provider=self.provider_name,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                latency_ms=latency_ms,
                success=True
            )

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            return ModelResponse(
                content="",
                model_id=model_id,
                provider=self.provider_name,
                latency_ms=latency_ms,
                success=False,
                error=str(e)
            )


class LocalProvider(ModelProvider):
    """
    Local model provider.

    Provides access to locally hosted models (e.g., via Ollama).
    """

    def __init__(self, config: ProviderConfig):
        """
        Initialize local provider.

        Args:
            config: Provider configuration
        """
        super().__init__(config)
        self.provider_name = "Local"

    def validate_config(self) -> bool:
        """
        Validate local provider configuration.

        Returns:
            True if configuration is valid
        """
        if not self.config.enabled:
            return False

        # Local providers don't require API keys
        # Just check that base URL is configured
        return bool(self.config.base_url)

    async def generate(self, request: ModelRequest, model_id: str) -> ModelResponse:
        """
        Generate a response using a local model.

        Args:
            request: Model request
            model_id: Model to use (e.g., llama3-70b)

        Returns:
            ModelResponse
        """
        start_time = time.time()

        try:
            # Import requests library
            try:
                import requests
            except ImportError:
                return ModelResponse(
                    content="",
                    model_id=model_id,
                    provider=self.provider_name,
                    success=False,
                    error="requests library not installed. Install with: pip install requests"
                )

            # Prepare API endpoint
            url = f"{self.config.base_url}/api/generate"

            # Prepare request payload
            payload = {
                "model": model_id,
                "prompt": request.prompt,
                "stream": False,
            }

            # Add optional parameters
            if request.system_prompt:
                payload["system"] = request.system_prompt

            if request.max_tokens:
                payload["num_predict"] = request.max_tokens

            # Make API call
            response = requests.post(url, json=payload, timeout=120)
            response.raise_for_status()

            # Extract response
            data = response.json()
            content = data.get("response", "")

            # Token usage may not be available for local models
            input_tokens = data.get("prompt_eval_count", 0)
            output_tokens = data.get("eval_count", 0)

            # Calculate latency
            latency_ms = (time.time() - start_time) * 1000

            return ModelResponse(
                content=content,
                model_id=model_id,
                provider=self.provider_name,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                latency_ms=latency_ms,
                success=True
            )

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            return ModelResponse(
                content="",
                model_id=model_id,
                provider=self.provider_name,
                latency_ms=latency_ms,
                success=False,
                error=str(e)
            )


class ModelManager:
    """
    Manages multiple model providers.

    Responsibilities:
    - Provider registration and configuration
    - Model routing to appropriate providers
    - Provider health checks
    - Cost estimation across providers
    """

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize the model manager.

        Args:
            config_path: Optional path to model configuration file
        """
        self.providers: Dict[ModelProviderType, ModelProvider] = {}
        self.config_path = config_path or self._get_default_config_path()
        self.config = self._load_config()
        self.lock = threading.Lock()

        # Register providers
        self._register_providers()

    def _get_default_config_path(self) -> Path:
        """Get default configuration file path."""
        project_root = Path(__file__).parent.parent.parent
        return project_root / "devflow" / "config" / "model_config.json"

    def _load_config(self) -> Dict[str, Any]:
        """
        Load model configuration from file.

        Returns:
            Configuration dictionary
        """
        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                return json.load(f)
        return {"providers": {}}

    def _register_providers(self):
        """Register model providers from configuration."""
        providers_config = self.config.get("providers", {})

        # Register Anthropic provider
        if "anthropic" in providers_config:
            anthropic_config = self._parse_provider_config(
                ModelProviderType.ANTHROPIC,
                providers_config["anthropic"]
            )
            if anthropic_config.enabled:
                self.providers[ModelProviderType.ANTHROPIC] = AnthropicProvider(anthropic_config)

        # Register OpenAI provider
        if "openai" in providers_config:
            openai_config = self._parse_provider_config(
                ModelProviderType.OPENAI,
                providers_config["openai"]
            )
            if openai_config.enabled:
                self.providers[ModelProviderType.OPENAI] = OpenAIProvider(openai_config)

        # Register Local provider
        if "local" in providers_config:
            local_config = self._parse_provider_config(
                ModelProviderType.LOCAL,
                providers_config["local"]
            )
            if local_config.enabled:
                self.providers[ModelProviderType.LOCAL] = LocalProvider(local_config)

    def _parse_provider_config(self, provider_type: ModelProviderType,
                               config_dict: Dict[str, Any]) -> ProviderConfig:
        """
        Parse provider configuration from dictionary.

        Args:
            provider_type: Type of provider
            config_dict: Configuration dictionary

        Returns:
            ProviderConfig object
        """
        models = {}
        for model_id, model_dict in config_dict.get("models", {}).items():
            models[model_id] = ModelConfig(
                model_id=model_id,
                name=model_dict.get("name", model_id),
                provider=provider_type.value,
                type=model_dict.get("type", "chat"),
                max_tokens=model_dict.get("max_tokens", 8192),
                input_cost_per_1k=model_dict.get("input_cost_per_1k", 0.0),
                output_cost_per_1k=model_dict.get("output_cost_per_1k", 0.0),
                capabilities=model_dict.get("capabilities", []),
                priority=model_dict.get("priority", 1),
                available=model_dict.get("available", True)
            )

        return ProviderConfig(
            provider_type=provider_type,
            name=config_dict.get("name", provider_type.value),
            enabled=config_dict.get("enabled", True),
            api_key_env=config_dict.get("api_key_env"),
            base_url=config_dict.get("base_url", ""),
            models=models
        )

    def get_provider(self, provider_type: ModelProviderType) -> Optional[ModelProvider]:
        """
        Get a specific provider.

        Args:
            provider_type: Type of provider

        Returns:
            ModelProvider if found and registered
        """
        return self.providers.get(provider_type)

    def get_all_providers(self) -> List[ModelProvider]:
        """
        Get all registered providers.

        Returns:
            List of ModelProvider objects
        """
        return list(self.providers.values())

    def get_available_providers(self) -> List[ModelProvider]:
        """
        Get providers with valid configuration.

        Returns:
            List of available ModelProvider objects
        """
        return [
            provider for provider in self.providers.values()
            if provider.validate_config()
        ]

    def get_provider_for_model(self, model_id: str) -> Optional[ModelProvider]:
        """
        Get the provider that handles a specific model.

        Args:
            model_id: Model identifier (e.g., claude-3-5-sonnet-20241022)

        Returns:
            ModelProvider if found
        """
        for provider in self.providers.values():
            if provider.get_model(model_id):
                return provider
        return None

    def get_all_models(self) -> Dict[str, ModelConfig]:
        """
        Get all models from all providers.

        Returns:
            Dictionary mapping model_id to ModelConfig
        """
        all_models = {}
        for provider in self.providers.values():
            all_models.update(provider.models)
        return all_models

    def get_available_models(self) -> List[ModelConfig]:
        """
        Get all available models from all providers.

        Returns:
            List of available ModelConfig objects
        """
        available_models = []
        for provider in self.providers.values():
            available_models.extend(provider.get_available_models())
        return available_models

    def get_models_by_capability(self, capability: str) -> List[ModelConfig]:
        """
        Get all models with a specific capability.

        Args:
            capability: Capability to filter by

        Returns:
            List of ModelConfig objects with the capability
        """
        models_with_capability = []
        for provider in self.providers.values():
            models_with_capability.extend(provider.get_models_by_capability(capability))
        return models_with_capability
