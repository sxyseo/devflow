"""
Integration Plugin - Base class for integration plugins.

Integration plugins enable DevFlow to connect with external tools, services,
and platforms such as CI/CD systems, code repositories, project management tools, etc.
"""

from abc import abstractmethod
from typing import Dict, List, Optional, Any
from enum import Enum

from devflow.plugins.base import Plugin, PluginMetadata


class IntegrationStatus(Enum):
    """Status of an integration connection."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


class IntegrationPlugin(Plugin):
    """
    Base class for integration plugins.

    Integration plugins enable DevFlow to connect with external tools, services,
    and platforms such as CI/CD systems, code repositories, project management tools,
    notification systems, and other third-party services.

    Provides:
    - Integration connection management
    - Authentication handling
    - Configuration validation
    - Health check functionality
    - Webhook handling capabilities
    """

    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the integration plugin.

        Args:
            config: Optional plugin configuration dictionary containing:
                    - api_key: API key or token for authentication
                    - api_url: Base URL for the integration API
                    - webhook_url: Optional webhook URL for callbacks
                    - timeout: Request timeout in seconds (default: 30)
        """
        super().__init__(config)
        self._status = IntegrationStatus.DISCONNECTED
        self._connection = None

    @abstractmethod
    def get_integration_name(self) -> str:
        """
        Get the name of this integration.

        Returns:
            Integration name (e.g., "github", "jenkins", "slack")
        """
        pass

    @abstractmethod
    def get_integration_type(self) -> str:
        """
        Get the type of this integration.

        Returns:
            Integration type (e.g., "vcs", "cicd", "notification", "project-management")
        """
        pass

    def validate_config(self) -> bool:
        """
        Validate the integration configuration.

        Checks that all required configuration fields are present and valid.

        Returns:
            True if configuration is valid, False otherwise
        """
        required_fields = self.get_required_config_fields()
        for field in required_fields:
            if field not in self.config:
                return False
            if not self.config[field]:
                return False
        return True

    def get_required_config_fields(self) -> List[str]:
        """
        Get the list of required configuration fields.

        Returns:
            List of required configuration field names
        """
        return ['api_url', 'api_key']

    def get_optional_config_fields(self) -> List[str]:
        """
        Get the list of optional configuration fields.

        Returns:
            List of optional configuration field names
        """
        return ['webhook_url', 'timeout', 'verify_ssl', 'proxy']

    def connect(self) -> bool:
        """
        Establish connection to the integration service.

        Validates credentials and establishes a connection to the external service.
        Override this method to implement custom connection logic.

        Returns:
            True if connection successful, False otherwise
        """
        if not self.validate_config():
            self._status = IntegrationStatus.ERROR
            return False

        self._status = IntegrationStatus.CONNECTING

        try:
            # Test the connection
            if self.test_connection():
                self._status = IntegrationStatus.CONNECTED
                return True
            else:
                self._status = IntegrationStatus.ERROR
                return False
        except Exception:
            self._status = IntegrationStatus.ERROR
            return False

    def disconnect(self) -> None:
        """
        Disconnect from the integration service.

        Override this method to implement custom disconnection logic
        (e.g., closing connections, cleaning up resources).
        """
        self._status = IntegrationStatus.DISCONNECTED
        self._connection = None

    def test_connection(self) -> bool:
        """
        Test the connection to the integration service.

        Override this method to implement a simple health check
        or ping operation to verify the connection is working.

        Returns:
            True if connection is working, False otherwise
        """
        # Default implementation attempts to connect
        # Subclasses should override with actual test logic
        return True

    def get_status(self) -> IntegrationStatus:
        """
        Get the current connection status.

        Returns:
            Current integration status
        """
        return self._status

    def is_connected(self) -> bool:
        """
        Check if the integration is connected.

        Returns:
            True if connected, False otherwise
        """
        return self._status == IntegrationStatus.CONNECTED

    def get_connection(self):
        """
        Get the connection object for the integration.

        Returns:
            Connection object or None if not connected
        """
        return self._connection

    def handle_webhook(self, payload: Dict[str, Any], headers: Dict[str, str]) -> Dict[str, Any]:
        """
        Handle an incoming webhook from the integration service.

        Override this method to process webhook events from the external service.

        Args:
            payload: Webhook payload data
            headers: HTTP headers from the webhook request

        Returns:
            Response dictionary with at least:
            - success: Boolean indicating if handling was successful
            - message: Optional message describing the result
        """
        return {
            'success': False,
            'message': 'Webhook handling not implemented'
        }

    def get_supported_webhook_events(self) -> List[str]:
        """
        Get the list of supported webhook event types.

        Returns:
            List of webhook event types this integration can handle
        """
        return []

    def send_notification(self, message: str, level: str = "info") -> bool:
        """
        Send a notification through the integration.

        Override this method to implement notification functionality
        (e.g., send a Slack message, create a Jira ticket, etc.)

        Args:
            message: The notification message
            level: Notification level (info, warning, error, success)

        Returns:
            True if notification sent successfully, False otherwise
        """
        return False

    def get_api_client(self):
        """
        Get or create an API client for the integration.

        Override this method to provide a configured API client
        for making requests to the external service.

        Returns:
            API client instance or None
        """
        return None

    def get_health_check(self) -> Dict[str, Any]:
        """
        Get health check information for the integration.

        Returns a dictionary with health status and diagnostic information.

        Returns:
            Dictionary with at least:
            - status: Health status (healthy, degraded, unhealthy)
            - message: Status message
            - details: Optional dictionary with additional details
        """
        if self.is_connected():
            return {
                'status': 'healthy',
                'message': f'{self.get_integration_name()} integration is connected',
                'details': {
                    'integration_name': self.get_integration_name(),
                    'integration_type': self.get_integration_type(),
                }
            }
        else:
            return {
                'status': 'unhealthy',
                'message': f'{self.get_integration_name()} integration is not connected',
                'details': {
                    'integration_name': self.get_integration_name(),
                    'integration_type': self.get_integration_type(),
                    'connection_status': self._status.value
                }
            }

    def register_integration(self, integration_manager) -> None:
        """
        Register the integration with the integration manager.

        Args:
            integration_manager: The integration manager to register with
        """
        integration_name = self.get_integration_name()
        integration_type = self.get_integration_type()

        # Register the integration
        if hasattr(integration_manager, 'register_integration'):
            integration_manager.register_integration(
                integration_name,
                integration_type,
                self
            )
