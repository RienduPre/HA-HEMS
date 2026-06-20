"""Pytest configuration for HA-HEMS tests."""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch


@pytest.fixture
def hass():
    """Mock Home Assistant instance."""
    hass = MagicMock()
    hass.services.async_call = AsyncMock()
    hass.states.get = MagicMock(return_value=None)
    return hass


@pytest.fixture
def hass_registry():
    """Mock entity registry."""
    registry = MagicMock()
    registry.entities = {}
    return registry
