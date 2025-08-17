# tests/conftest.py

import sys
import os
import pytest
import importlib

# Use in-memory DB for testing
os.environ["TESTING"] = "1"

# Add project root to sys.path so imports work in console and PyCharm
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

@pytest.fixture(scope="session")
def app_module():
    """
    import the flask app webhook_receiver.py once per test session.
    """
    # import after TESTING=1 so it picks SQLite memory DB
    app_module = importlib.import_module("webhook_receiver")
    return app_module

@pytest.fixture(scope="session")
def app(app_module):
    """
    return the flask app instance from your module.
    """
    return app_module.app

@pytest.fixture(scope="session")
def db(app_module):
    """
    return the SQLAlchemy db object imported in your module.
    """
    return app_module.db


@pytest.fixture(scope="function", autouse=True)
def _db_setup(app,db):
    """
    create all tables before each test and drop after.
    """
    with app.app_context():
        db.create_all()
        yield
        db.drop_all()

@pytest.fixture()
def client(app):
    """
    Flask test client for making requests to route.
    """
    return app.test_client()

