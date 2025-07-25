"""Configuration management for ARTL MCP.

This module provides utilities for managing configuration from MCP clients,
enabling better environment variable access across different client types.
"""

from typing import Any

from .email_manager import EmailManager


class ConfigManager:
    """Manages configuration injection from MCP clients."""

    def __init__(self, client_config: dict[str, Any] | None = None):
        """Initialize configuration manager.

        Args:
            client_config: Configuration dictionary from MCP client
        """
        self.client_config = client_config or {}
        self._email_manager: EmailManager | None = None

    def get_email_manager(self) -> EmailManager:
        """Get EmailManager with client configuration.

        Returns:
            EmailManager instance configured with client config
        """
        if self._email_manager is None:
            self._email_manager = EmailManager(client_config=self.client_config)
        return self._email_manager

    def get_config_value(self, key: str, default: Any = None) -> Any:
        """Get configuration value with fallback to environment.

        Args:
            key: Configuration key to retrieve
            default: Default value if not found

        Returns:
            Configuration value or default
        """
        # Check client config first
        if key in self.client_config:
            return self.client_config[key]

        # Fall back to environment variable
        import os

        return os.getenv(key, default)

    def update_config(self, new_config: dict[str, Any]) -> None:
        """Update client configuration.

        Args:
            new_config: New configuration to merge
        """
        self.client_config.update(new_config)
        # Reset email manager to pick up new config
        self._email_manager = None


# Global configuration manager
# This can be updated by MCP server initialization code
global_config_manager = ConfigManager()


def set_client_config(config: dict[str, Any]) -> None:
    """Set global client configuration.

    Args:
        config: Configuration dictionary from MCP client
    """
    global global_config_manager
    global_config_manager = ConfigManager(config)


def get_email_manager() -> EmailManager:
    """Get configured EmailManager instance.

    Returns:
        EmailManager with current client configuration
    """
    return global_config_manager.get_email_manager()


def get_config_value(key: str, default: Any = None) -> Any:
    """Get configuration value.

    Args:
        key: Configuration key
        default: Default value

    Returns:
        Configuration value or default
    """
    return global_config_manager.get_config_value(key, default)
