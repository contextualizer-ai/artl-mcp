"""Test email configuration setup for ARTL MCP."""

import os
from pathlib import Path

import pytest

from artl_mcp.utils.email_manager import EmailManager


def test_email_configuration_present():
    """Test that a valid email configuration is present in environment or local/.env."""
    em = EmailManager()

    # Check environment variable first
    env_email = os.getenv("ARTL_EMAIL_ADDR")
    if (
        env_email
        and em._is_valid_email(env_email)
        and not em._is_bogus_email(env_email)
    ):
        # Valid email in environment
        return

    # Check local/.env file
    env_file = Path("local/.env")
    if env_file.exists():
        file_email = em._read_env_file()
        if (
            file_email
            and em._is_valid_email(file_email)
            and not em._is_bogus_email(file_email)
        ):
            # Valid email in file
            return
        else:
            pytest.fail(
                f"local/.env file exists but contains invalid or bogus email: "
                f"{file_email}. Please update ARTL_EMAIL_ADDR in local/.env with a "
                "real email address."
            )
    else:
        pytest.fail(
            "No valid email configuration found. Please either:\n"
            "1. Set ARTL_EMAIL_ADDR environment variable, or\n"
            "2. Create local/.env file with ARTL_EMAIL_ADDR=your@email.com"
        )


@pytest.mark.skipif(os.getenv("CI") is not None, reason="Skip local/.env tests in CI")
def test_local_env_file_exists():
    """Test that local/.env file exists for email configuration."""
    env_file = Path("local/.env")
    assert (
        env_file.exists()
    ), "local/.env file not found. Create it with ARTL_EMAIL_ADDR=your@email.com"


def test_email_in_local_env_is_not_bogus():
    """Test that email in local/.env is not a bogus pattern."""
    env_file = Path("local/.env")
    if not env_file.exists():
        pytest.skip("local/.env file does not exist")

    em = EmailManager()
    file_email = em._read_env_file()

    if not file_email:
        pytest.fail("No ARTL_EMAIL_ADDR found in local/.env file")

    if not em._is_valid_email(file_email):
        pytest.fail(f"Invalid email format in local/.env: {file_email}")

    if em._is_bogus_email(file_email):
        pytest.fail(
            f"Bogus email pattern found in local/.env: {file_email}. "
            "Please update with a real email address."
        )


def test_environment_email_is_not_bogus():
    """Test that ARTL_EMAIL_ADDR environment variable is not bogus."""
    env_email = os.getenv("ARTL_EMAIL_ADDR")
    if not env_email:
        pytest.skip("ARTL_EMAIL_ADDR environment variable not set")

    em = EmailManager()

    if not em._is_valid_email(env_email):
        pytest.fail(f"Invalid email format in environment variable: {env_email}")

    if em._is_bogus_email(env_email):
        pytest.fail(
            f"Bogus email pattern found in environment variable: {env_email}. "
            "Please set ARTL_EMAIL_ADDR to a real email address."
        )


def test_email_manager_can_get_valid_email():
    """Test that EmailManager can successfully get a valid, non-bogus email."""
    em = EmailManager()
    email = em.get_email()

    assert email is not None, (
        "EmailManager could not find a valid email. Please set ARTL_EMAIL_ADDR "
        "environment variable or add to local/.env file."
    )

    assert em._is_valid_email(email), f"EmailManager returned invalid email: {email}"
    assert not em._is_bogus_email(email), f"EmailManager returned bogus email: {email}"
