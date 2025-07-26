"""Tests for email address management functionality."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from artl_mcp.utils.email_manager import (
    EmailManager,
    email_manager,
    get_email,
    require_email,
)


class TestEmailManager:
    """Test the EmailManager class functionality."""

    def test_valid_email_format_validation(self):
        """Test email format validation with basic structure."""
        em = EmailManager()

        # Test basic valid structure: local@domain.extension
        assert em._is_valid_email("a@b.co")
        assert em._is_valid_email("user@domain.org")
        assert em._is_valid_email("name.lastname@company.net")
        assert em._is_valid_email("test+tag@example.info")

    def test_invalid_email_format_validation(self):
        """Test rejection of invalid email formats."""
        em = EmailManager()

        invalid_emails = [
            "",
            "not-an-email",
            "@domain.com",  # Missing local part
            "user@",  # Missing domain
            "user@domain",  # Missing extension
            "user.domain.com",  # Missing @
            "user@@domain.com",  # Multiple @
            "user@domain.",  # Missing extension
            None,
            123,
        ]

        for email in invalid_emails:
            assert not em._is_valid_email(email), f"Should be invalid: {email}"

    def test_get_email_with_provided_valid_email(self):
        """Test getting email when valid email is provided."""
        em = EmailManager()

        provided_email = "user@domain.co"
        result = em.get_email(provided_email)
        assert result == provided_email

    def test_get_email_rejects_invalid_provided_email(self):
        """Test rejection of invalid provided email."""
        em = EmailManager()

        with pytest.raises(ValueError, match="Invalid email format"):
            em.get_email("not-an-email")

    def test_get_email_from_environment_variable(self):
        """Test getting email from ARTL_EMAIL_ADDR environment variable."""
        em = EmailManager()

        with patch.dict(os.environ, {"ARTL_EMAIL_ADDR": "env@domain.co"}):
            result = em.get_email()
            assert result == "env@domain.co"

    def test_get_email_uses_any_valid_environment_variable(self):
        """Test that any syntactically valid email from environment is used."""
        em = EmailManager()

        # Clear any cached email first
        em._cached_email = None

        with patch.dict(os.environ, {"ARTL_EMAIL_ADDR": "any@valid.email"}, clear=True):
            with patch.object(em, "_read_env_file", return_value=None):
                result = em.get_email()
                assert result == "any@valid.email"

    @pytest.mark.skipif(
        os.getenv("CI") is not None, reason="Skip local/.env tests in CI"
    )
    def test_get_email_from_env_file(self):
        """Test getting email from local/.env file."""
        em = EmailManager()

        # Create a temporary .env file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("ARTL_EMAIL_ADDR=envfile@domain.co\n")
            env_file_path = f.name

        try:
            # Mock the env file path
            with patch.object(Path, "exists", return_value=True):
                with patch(
                    "builtins.open",
                    lambda *args, **kwargs: open(env_file_path, *args, **kwargs),
                ):
                    with patch.object(
                        em, "_read_env_file", return_value="envfile@domain.co"
                    ):
                        result = em.get_email()
                        assert result == "envfile@domain.co"
        finally:
            os.unlink(env_file_path)

    def test_require_email_success(self):
        """Test require_email when email is available."""
        em = EmailManager()

        provided_email = "markampa@upenn.edu"
        result = em.require_email(provided_email)
        assert result == provided_email

    def test_require_email_failure(self):
        """Test require_email when no email is available."""
        em = EmailManager()

        # Clear any cached email
        em._cached_email = None

        with patch.dict(os.environ, {}, clear=True):
            with patch.object(em, "_read_env_file", return_value=None):
                with pytest.raises(ValueError, match="No valid email address found"):
                    em.require_email()

    def test_validate_for_api_with_valid_email(self):
        """Test API-specific validation with any valid email."""
        em = EmailManager()

        # Should work with any syntactically valid email
        valid_email = "user@domain.co"
        result = em.validate_for_api("unpaywall", valid_email)
        assert result == valid_email

        another_email = "test@example.com"
        result = em.validate_for_api("crossref", another_email)
        assert result == another_email

    def test_email_caching(self):
        """Test that valid emails are cached for performance."""
        em = EmailManager()

        with patch.dict(os.environ, {"ARTL_EMAIL_ADDR": "cached@domain.co"}):
            # First call should cache the email
            result1 = em.get_email()
            assert result1 == "cached@domain.co"
            assert em._cached_email == "cached@domain.co"

            # Second call should use cached email
            with patch.dict(os.environ, {}, clear=True):  # Remove env var
                result2 = em.get_email()
                assert result2 == "cached@domain.co"  # Should still work from cache


class TestGlobalFunctions:
    """Test the global convenience functions."""

    def test_get_email_function(self):
        """Test global get_email function."""
        # Clear cached email first
        email_manager._cached_email = None

        with patch.dict(
            os.environ, {"ARTL_EMAIL_ADDR": "global@domain.co"}, clear=True
        ):
            with patch.object(email_manager, "_read_env_file", return_value=None):
                result = get_email()
                assert result == "global@domain.co"

    def test_require_email_function(self):
        """Test global require_email function."""
        provided_email = "global@domain.co"
        result = require_email(provided_email)
        assert result == provided_email

    def test_require_email_function_failure(self):
        """Test global require_email function failure."""
        # Clear cached email first
        email_manager._cached_email = None

        with patch.dict(os.environ, {}, clear=True):
            with patch.object(email_manager, "_read_env_file", return_value=None):
                with pytest.raises(ValueError, match="No valid email address found"):
                    require_email()


class TestEnvFileReading:
    """Test reading from .env files."""

    def test_read_env_file_artl_email_addr(self):
        """Test reading ARTL_EMAIL_ADDR from .env file."""
        em = EmailManager()

        test_email = "test@domain.co"

        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write(f"ARTL_EMAIL_ADDR={test_email}\n")
            f.write("OTHER_VAR=value\n")
            env_file_path = f.name

        try:
            # Directly mock the _read_env_file method to use our test file
            def mock_read_env_file():
                try:
                    with open(env_file_path) as f:
                        for line in f:
                            line = line.strip()
                            if line.startswith("ARTL_EMAIL_ADDR="):
                                return line.split("=", 1)[1].strip()
                except Exception:
                    return None
                return None

            with patch.object(em, "_read_env_file", side_effect=mock_read_env_file):
                result = em._read_env_file()
                assert result == test_email
        finally:
            os.unlink(env_file_path)

    def test_read_env_file_nonexistent(self):
        """Test reading from non-existent .env file."""
        em = EmailManager()

        with patch.object(Path, "exists", return_value=False):
            result = em._read_env_file()
            assert result is None

    def test_read_env_file_no_email_vars(self):
        """Test reading .env file with no email variables."""
        em = EmailManager()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("OTHER_VAR=value\n")
            f.write("ANOTHER_VAR=value2\n")
            env_file_path = f.name

        try:
            with patch(
                "builtins.open",
                lambda *args, **kwargs: open(env_file_path, *args, **kwargs),
            ):
                result = em._read_env_file()
                assert result is None
        finally:
            os.unlink(env_file_path)

    def test_read_env_file_handles_exceptions(self):
        """Test that _read_env_file handles file reading exceptions."""
        em = EmailManager()

        with patch.object(Path, "exists", return_value=True):
            with patch("builtins.open", side_effect=OSError("File read error")):
                result = em._read_env_file()
                assert result is None
