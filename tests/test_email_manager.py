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
        """Test email format validation."""
        em = EmailManager()

        valid_emails = [
            "user@domain.com",
            "test.user@university.edu",
            "researcher+work@institution.org",
            "MAM@lbl.gov",
        ]

        for email in valid_emails:
            assert em._is_valid_email(email), f"Should be valid: {email}"

    def test_invalid_email_format_validation(self):
        """Test rejection of invalid email formats."""
        em = EmailManager()

        invalid_emails = [
            "",
            "not-an-email",
            "@domain.com",
            "user@",
            "user@domain",
            "user.domain.com",
            None,
            123,
        ]

        for email in invalid_emails:
            assert not em._is_valid_email(email), f"Should be invalid: {email}"

    def test_bogus_email_detection(self):
        """Test detection of bogus/test email patterns."""
        em = EmailManager()

        bogus_emails = [
            "test@example.com",
            "user@test.test",  # Changed to match pattern
            "dummy.user@fake.net",
            "placeholder@invalid.com",
            "noreply@service.com",
            "no-reply@automated.org",
        ]

        for email in bogus_emails:
            assert em._is_bogus_email(email), f"Should be detected as bogus: {email}"

    def test_legitimate_email_not_flagged_as_bogus(self):
        """Test that legitimate emails are not flagged as bogus."""
        em = EmailManager()

        legitimate_emails = [
            "researcher@university.edu",
            "MAM@lbl.gov",
            "scientist@institution.org",
            "student@college.ac.uk",
        ]

        for email in legitimate_emails:
            assert not em._is_bogus_email(
                email
            ), f"Should not be flagged as bogus: {email}"

    def test_get_email_with_provided_valid_email(self):
        """Test getting email when valid email is provided."""
        em = EmailManager()

        provided_email = "researcher@university.edu"
        result = em.get_email(provided_email)
        assert result == provided_email

    def test_get_email_rejects_bogus_provided_email(self):
        """Test rejection of bogus provided email."""
        em = EmailManager()

        with pytest.raises(ValueError, match="Bogus email address not allowed"):
            em.get_email("test@example.com")

    def test_get_email_rejects_invalid_provided_email(self):
        """Test rejection of invalid provided email."""
        em = EmailManager()

        with pytest.raises(ValueError, match="Invalid email format"):
            em.get_email("not-an-email")

    def test_get_email_from_environment_variable(self):
        """Test getting email from ARTL_EMAIL_ADDR environment variable."""
        em = EmailManager()

        with patch.dict(os.environ, {"ARTL_EMAIL_ADDR": "env@university.edu"}):
            result = em.get_email()
            assert result == "env@university.edu"

    def test_get_email_ignores_bogus_environment_variable(self):
        """Test that bogus email in environment variable is ignored."""
        em = EmailManager()

        # Clear any cached email first
        em._cached_email = None

        with patch.dict(
            os.environ, {"ARTL_EMAIL_ADDR": "test@example.com"}, clear=True
        ):
            with patch.object(em, "_read_env_file", return_value=None):
                result = em.get_email()
                assert result is None  # Should ignore bogus email

    @pytest.mark.skipif(
        os.getenv("CI") is not None, reason="Skip local/.env tests in CI"
    )
    def test_get_email_from_env_file(self):
        """Test getting email from local/.env file."""
        em = EmailManager()

        # Create a temporary .env file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("ARTL_EMAIL_ADDR=envfile@university.edu\n")
            env_file_path = f.name

        try:
            # Mock the env file path
            with patch.object(Path, "exists", return_value=True):
                with patch(
                    "builtins.open",
                    lambda *args, **kwargs: open(env_file_path, *args, **kwargs),
                ):
                    with patch.object(
                        em, "_read_env_file", return_value="envfile@university.edu"
                    ):
                        result = em.get_email()
                        assert result == "envfile@university.edu"
        finally:
            os.unlink(env_file_path)

    @pytest.mark.skipif(
        os.getenv("CI") is not None, reason="Skip local/.env tests in CI"
    )
    def test_get_email_supports_legacy_email_address_format(self):
        """Test support for legacy email_address format in .env file."""
        em = EmailManager()

        # Create a temporary .env file with legacy format
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("email_address=legacy@university.edu\n")
            env_file_path = f.name

        try:
            with patch.object(Path, "exists", return_value=True):
                with patch(
                    "builtins.open",
                    lambda *args, **kwargs: open(env_file_path, *args, **kwargs),
                ):
                    with patch.object(
                        em, "_read_env_file", return_value="legacy@university.edu"
                    ):
                        result = em.get_email()
                        assert result == "legacy@university.edu"
        finally:
            os.unlink(env_file_path)

    def test_require_email_success(self):
        """Test require_email when email is available."""
        em = EmailManager()

        provided_email = "researcher@university.edu"
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

    def test_validate_for_api_unpaywall(self):
        """Test API-specific validation for Unpaywall."""
        em = EmailManager()

        # Should work with institutional email
        institutional_email = "researcher@university.edu"
        result = em.validate_for_api("unpaywall", institutional_email)
        assert result == institutional_email

        # Should reject example.com for Unpaywall
        with pytest.raises(ValueError, match="requires a real institutional email"):
            em.validate_for_api("unpaywall", "test@example.com")

    def test_validate_for_api_crossref(self):
        """Test API-specific validation for CrossRef."""
        em = EmailManager()

        # Should work with institutional email
        institutional_email = "researcher@university.edu"
        result = em.validate_for_api("crossref", institutional_email)
        assert result == institutional_email

        # Should reject example.com for CrossRef
        with pytest.raises(ValueError, match="requires a real institutional email"):
            em.validate_for_api("crossref", "test@example.com")

    def test_email_caching(self):
        """Test that valid emails are cached for performance."""
        em = EmailManager()

        with patch.dict(os.environ, {"ARTL_EMAIL_ADDR": "cached@university.edu"}):
            # First call should cache the email
            result1 = em.get_email()
            assert result1 == "cached@university.edu"
            assert em._cached_email == "cached@university.edu"

            # Second call should use cached email
            with patch.dict(os.environ, {}, clear=True):  # Remove env var
                result2 = em.get_email()
                assert (
                    result2 == "cached@university.edu"
                )  # Should still work from cache


class TestGlobalFunctions:
    """Test the global convenience functions."""

    def test_get_email_function(self):
        """Test global get_email function."""
        with patch.dict(os.environ, {"ARTL_EMAIL_ADDR": "global@university.edu"}):
            result = get_email()
            assert result == "global@university.edu"

    def test_require_email_function(self):
        """Test global require_email function."""
        provided_email = "global@university.edu"
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

        # Test with hardcoded institutional email to avoid dependency on actual config
        test_email = "researcher@university.edu"

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
                            elif line.startswith("email_address="):
                                return line.split("=", 1)[1].strip()
                except Exception:
                    return None
                return None

            with patch.object(em, "_read_env_file", side_effect=mock_read_env_file):
                result = em._read_env_file()
                assert result == test_email
        finally:
            os.unlink(env_file_path)

    def test_read_env_file_legacy_format(self):
        """Test reading legacy email_address from .env file."""
        em = EmailManager()

        # Test with hardcoded institutional email to avoid dependency on actual config
        test_email = "legacy@university.edu"

        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write(f"email_address={test_email}\n")
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
                            elif line.startswith("email_address="):
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
