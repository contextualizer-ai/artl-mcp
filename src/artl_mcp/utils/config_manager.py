"""Configuration management for ARTL MCP.

This module provides utilities for managing configuration from MCP clients,
enabling better environment variable access across different client types.
"""

import logging
from typing import Any

import requests

from .email_manager import EmailManager

logger = logging.getLogger(__name__)


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


# Service availability testing functions
def test_ncbi_service_availability(timeout: int = 10) -> dict[str, bool]:
    """Test availability of key NCBI/NLM services.

    Tests multiple NCBI endpoints to determine service availability.
    Used for automatic fallback to alternative sources.

    Args:
        timeout: Request timeout in seconds

    Returns:
        Dictionary with service availability status:
        {
            "pubmed": True/False,
            "pmc": True/False,
            "eutils": True/False,
            "overall": True/False  # True if any service is available
        }
    """
    services = {
        "pubmed": "https://pubmed.ncbi.nlm.nih.gov/",
        "eutils": "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/einfo.fcgi",
        "pmc": "https://www.ncbi.nlm.nih.gov/pmc/",
    }

    results = {}

    for service_name, url in services.items():
        try:
            response = requests.head(url, timeout=timeout)
            # Consider 2xx and 3xx as available (redirects are common)
            results[service_name] = 200 <= response.status_code < 400
            logger.debug(f"NCBI {service_name} status: {response.status_code}")
        except (requests.exceptions.RequestException, Exception) as e:
            results[service_name] = False
            logger.debug(f"NCBI {service_name} unavailable: {e}")

    # Overall availability if any service responds
    results["overall"] = any(results.values())

    return results


def should_use_alternative_sources() -> bool:
    """Determine if alternative sources should be used instead of NCBI.

    Checks both explicit configuration and automatic service detection.
    This function respects DOE funding requirements to prioritize US resources
    when available.

    Returns:
        True if alternative sources (Europe PMC, etc.) should be used
        False if NCBI services should be attempted first

    Usage:
        Use this in tools that need to choose between NCBI and alternative APIs
    """
    # Check explicit configuration first
    use_alternatives = get_config_value("USE_ALTERNATIVE_SOURCES", "false")
    if use_alternatives.lower() == "true":
        logger.info("Using alternative sources due to USE_ALTERNATIVE_SOURCES=true")
        return True

    # Check legacy environment variable for backward compatibility
    pubmed_offline = get_config_value("PUBMED_OFFLINE", "false")
    if pubmed_offline.lower() == "true":
        logger.info("Using alternative sources due to PUBMED_OFFLINE=true (deprecated)")
        return True

    # Auto-detect service availability
    try:
        availability = test_ncbi_service_availability(timeout=5)
        if not availability["overall"]:
            logger.info("NCBI services appear unavailable, using alternative sources")
            return True
        else:
            logger.info("NCBI services available, prioritizing US resources")
            return False
    except Exception as e:
        logger.warning(
            f"Could not test NCBI availability: {e}, using alternative sources"
        )
        return True


def is_ncbi_available() -> bool:
    """Quick check if NCBI services are available.

    Returns:
        True if NCBI services are responding, False otherwise

    Note:
        This is a lightweight check for test decorators and quick decisions.
        For comprehensive service selection, use should_use_alternative_sources().
    """
    try:
        availability = test_ncbi_service_availability(timeout=3)
        return availability["overall"]
    except Exception:
        return False
