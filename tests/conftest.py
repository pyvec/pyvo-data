import copy

import pytest

from loader import load_data


@pytest.fixture(scope='session')
def loaded_data():
    """The whole data set, loaded once per test session. Do not mutate."""
    return load_data()


@pytest.fixture
def data(loaded_data):
    """A private deep copy of the data set that a test may break at will"""
    return copy.deepcopy(loaded_data)
