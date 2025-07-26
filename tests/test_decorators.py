"""Test decorators for NCBI service availability and offline testing.

This module provides pytest decorators for handling NCBI service availability,
allowing tests to be automatically skipped when NCBI services are offline
or when using alternative sources.
"""

import pytest

from artl_mcp.utils.config_manager import (
    is_ncbi_available,
    should_use_alternative_sources,
)


def skip_if_ncbi_offline(func=None, *, reason="NCBI services are offline"):
    """Skip test if NCBI services are not available.

    This decorator checks NCBI service availability in real-time and skips
    the test if services are not responding. Useful for tests that require
    live NCBI API access.

    Args:
        func: Test function to decorate (when used without arguments)
        reason: Custom reason message for skip (default: "NCBI services are offline")

    Returns:
        Decorated test function that will be skipped if NCBI is offline

    Examples:
        @skip_if_ncbi_offline
        def test_pubmed_search():
            # Test code that requires NCBI access
            pass

        @skip_if_ncbi_offline(reason="PubMed API required for this test")
        def test_specific_pubmed_feature():
            # Test code here
            pass
    """

    def decorator(test_func):
        return pytest.mark.skipif(not is_ncbi_available(), reason=reason)(test_func)

    if func is None:
        # Called with arguments: @skip_if_ncbi_offline(reason="...")
        return decorator
    else:
        # Called without arguments: @skip_if_ncbi_offline
        return decorator(func)


def skip_if_using_alternatives(
    func=None, *, reason="Using alternative sources instead of NCBI"
):
    """Skip test if configured to use alternative sources.

    This decorator checks the configuration to see if alternative sources
    (Europe PMC, etc.) should be used instead of NCBI services. Useful for
    tests that specifically test NCBI functionality and should be skipped
    when alternative sources are preferred.

    Args:
        func: Test function to decorate (when used without arguments)
        reason: Custom reason message for skip

    Returns:
        Decorated test function that will be skipped if using alternatives

    Examples:
        @skip_if_using_alternatives
        def test_pubmed_specific_feature():
            # Test code that specifically tests PubMed functionality
            pass

        @skip_if_using_alternatives(reason="This test requires direct NCBI access")
        def test_ncbi_api_endpoint():
            # Test code here
            pass
    """

    def decorator(test_func):
        return pytest.mark.skipif(should_use_alternative_sources(), reason=reason)(
            test_func
        )

    if func is None:
        # Called with arguments: @skip_if_using_alternatives(reason="...")
        return decorator
    else:
        # Called without arguments: @skip_if_using_alternatives
        return decorator(func)


def requires_ncbi_access(func=None, *, strict=False, reason=None):
    """Mark test as requiring NCBI access with automatic skipping.

    This is a comprehensive decorator that combines both offline checking
    and alternative source configuration. It will skip the test if:
    - NCBI services are offline (when strict=True)
    - Alternative sources are configured to be used instead of NCBI

    Args:
        func: Test function to decorate (when used without arguments)
        strict: If True, also skip when NCBI services are offline (default: False)
        reason: Custom reason message for skip

    Returns:
        Decorated test function with NCBI access requirements

    Examples:
        @requires_ncbi_access
        def test_pubmed_functionality():
            # Will be skipped if USE_ALTERNATIVE_SOURCES=true
            pass

        @requires_ncbi_access(strict=True)
        def test_pubmed_strict():
            # Will be skipped if NCBI is offline OR alternatives are configured
            pass

        @requires_ncbi_access(strict=True, reason="Critical NCBI test")
        def test_critical_ncbi_feature():
            # Test code here
            pass
    """

    def decorator(test_func):
        # Build skip condition that evaluates at runtime
        def should_skip():
            skip_conditions = []

            # Always skip if alternatives are configured
            if should_use_alternative_sources():
                skip_conditions.append("configured to use alternative sources")

            # Skip if NCBI is offline (when strict mode)
            if strict and not is_ncbi_available():
                skip_conditions.append("NCBI services are offline")

            return len(skip_conditions) > 0, skip_conditions

        # Create the skip condition function for pytest
        def skip_condition():
            should_skip_result, reasons = should_skip()
            return should_skip_result

        # Determine final reason - build at decoration time but use callable
        final_reason = (
            reason or "Test requires NCBI access but conditions prevent execution"
        )

        return pytest.mark.skipif(skip_condition, reason=final_reason)(test_func)

    if func is None:
        # Called with arguments: @requires_ncbi_access(strict=True, reason="...")
        return decorator
    else:
        # Called without arguments: @requires_ncbi_access
        return decorator(func)


# Convenience markers for common patterns
ncbi_required = pytest.mark.skipif(
    lambda: should_use_alternative_sources(),
    reason="Test requires NCBI access but alternative sources are configured",
)

ncbi_online_required = pytest.mark.skipif(
    lambda: not is_ncbi_available(), reason="Test requires NCBI services to be online"
)

# Combined marker for tests that need both NCBI access and online services
ncbi_full_access = pytest.mark.skipif(
    lambda: should_use_alternative_sources() or not is_ncbi_available(),
    reason="Test requires full NCBI access (online and not using alternatives)",
)


# Parametrized markers for different service levels
def parametrize_ncbi_availability():
    """Parametrize tests to run with different NCBI availability scenarios.

    This can be used to test behavior under different conditions:
    - NCBI available, not using alternatives
    - NCBI available, using alternatives
    - NCBI offline, using alternatives

    Returns:
        pytest.mark.parametrize decorator

    Example:
        @parametrize_ncbi_availability()
        def test_search_behavior(ncbi_available, using_alternatives):
            # Test will run multiple times with different configurations
            pass
    """
    scenarios = [
        (True, False, "ncbi_available_direct"),
        (True, True, "ncbi_available_alternatives"),
        (False, True, "ncbi_offline_alternatives"),
    ]

    return pytest.mark.parametrize(
        "ncbi_available,using_alternatives,scenario_name",
        scenarios,
        ids=[scenario[2] for scenario in scenarios],
    )
