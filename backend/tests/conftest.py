import pytest
from fastapi import FastAPI

from app import create_app


@pytest.fixture
def app() -> FastAPI:
    return create_app()