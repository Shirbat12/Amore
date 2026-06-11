"""Shared test fixtures."""
import pytest

from data.samples.generate_samples import generate


@pytest.fixture
def history():
    """A deterministic synthetic history with a recoverable latent preference."""
    return generate(n=30, seed=42)
