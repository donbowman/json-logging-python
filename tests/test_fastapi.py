"""Test suite for the flask backend"""
import json
import logging
import pathlib
import re

import fastapi
import fastapi.testclient
import pytest
from helpers import constants
from helpers.handler import FormattedMessageCollectorHandler
from helpers.imports import undo_imports_from_package

LOGGER_NAME = "fastapi-test"


@pytest.fixture
def client_and_log_handler():
    import json_logging

    # Init app
    app = fastapi.FastAPI()

    # Init std logging
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.DEBUG)
    handler = FormattedMessageCollectorHandler()
    logger.addHandler(handler)

    # Add json_logging
    json_logging.init_fastapi(enable_json=True)
    json_logging.init_request_instrument(app, exclude_url_patterns=["^/no-request-instrumentation"])

    # Prepare test endpoints
    @app.get("/log/levels/debug")
    async def log_debug():
        logger.debug("debug message")
        return {}

    @app.get("/log/levels/info")
    async def log_info():
        logger.info("info message")
        return {}

    @app.get("/log/levels/error")
    async def log_error():
        logger.error("error message")
        return {}

    @app.get("/log/extra_property")
    async def extra_property():
        logger.info(
            "test log statement with extra props",
            extra={"props": {"extra_property": "extra_value"}, "tags": ["app:name"], "extra_property": "extra_value2"},
        )
        return {}

    @app.get("/log/extra_property_no_props")
    async def extra_property_no_props():
        logger.info(
            "test log statement with extra and no 'props' property",
            extra={"tags": ["app:name"], "extra_property": "extra_value2"},
        )
        return {}

    @app.get("/log/exception")
    async def log_exception():
        try:
            raise RuntimeError()
        except BaseException as e:
            logger.exception("Error occurred", exc_info=e)
        return {}

    @app.get("/get-correlation-id")
    async def get_correlation_id():
        return {'correlation_id': json_logging.get_correlation_id()}

    @app.get('/no-request-instrumentation')
    async def excluded_from_request_instrumentation():
        return {}

    test_client = fastapi.testclient.TestClient(app)
    yield test_client, handler

    # Tear down test environment
    logger.removeHandler(handler)
    undo_imports_from_package("json_logging")  # Necessary because of json-logging's global state


@pytest.mark.parametrize("level", ["debug", "info", "error"])
def test_record_format_per_log_level(client_and_log_handler, level):
    """Test if log messages are formatted correctly for all log levels"""
    api_client, handler = client_and_log_handler

    response = api_client.get("/log/levels/" + level)

    assert response.status_code == 200
    assert len(handler.messages) == 1
    msg = json.loads(handler.messages[0])
    assert set(msg.keys()) == constants.STANDARD_MSG_ATTRIBUTES
    assert msg["module"] == __name__
    assert msg["level"] == level.upper()
    assert msg["logger"] == LOGGER_NAME
    assert msg["type"] == "log"
    assert msg["msg"] == level + " message"
    assert re.match(
        r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(\.\d+.*)?$", msg["written_at"]
    ), "The field 'written_at' does not contain an iso timestamp"


def test_correlation_id_given(client_and_log_handler):
    """Test if a given correlation ID is added to the logs"""
    api_client, handler = client_and_log_handler

    response = api_client.get("/log/levels/debug", headers={"X-Correlation-Id": "abc-def"})

    assert response.status_code == 200
    assert len(handler.messages) == 1
    msg = json.loads(handler.messages[0])
    assert set(msg.keys()) == constants.STANDARD_MSG_ATTRIBUTES
    assert msg["correlation_id"] == "abc-def"


def test_correlation_id_generated(client_and_log_handler):
    """Test if a missing correlation ID is replaced by an autogenerated UUID"""
    api_client, handler = client_and_log_handler

    response = api_client.get("/log/levels/debug")

    assert response.status_code == 200
    assert len(handler.messages) == 1
    msg = json.loads(handler.messages[0])
    assert set(msg.keys()) == constants.STANDARD_MSG_ATTRIBUTES
    assert re.match(
        r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-5][0-9a-f]{3}-[089ab][0-9a-f]{3}-[0-9a-f]{12}$",
        msg["correlation_id"],
    ), "autogenerated UUID doesn't have expected format"


def test_get_correlation_id(client_and_log_handler):
    """Test if json_logging.get_correlation_id() finds a given correlation ID"""
    api_client, handler = client_and_log_handler

    response = api_client.get("/get-correlation-id", headers={"X-Correlation-Id": "abc-def"})

    assert response.status_code == 200
    assert response.json()["correlation_id"] == "abc-def"


def test_extra_property(client_and_log_handler):
    """Test adding an extra property to a log message"""
    api_client, handler = client_and_log_handler

    response = api_client.get("/log/extra_property")

    assert response.status_code == 200
    assert len(handler.messages) == 1
    msg = json.loads(handler.messages[0])
    assert set(msg.keys()) == constants.STANDARD_MSG_ATTRIBUTES.union({"extra_property", "tags"})
    assert msg["extra_property"] == "extra_value"
    assert msg["tags"] == ["app:name"]


def test_extra_property_no_props(client_and_log_handler):
    """Test adding an extra property to a log message"""
    api_client, handler = client_and_log_handler

    response = api_client.get("/log/extra_property_no_props")

    assert response.status_code == 200
    assert len(handler.messages) == 1
    msg = json.loads(handler.messages[0])
    assert set(msg.keys()) == constants.STANDARD_MSG_ATTRIBUTES.union({"extra_property", "tags"})
    assert msg["extra_property"] == "extra_value2"
    assert msg["tags"] == ["app:name"]


def test_exception_logged_with_stack_trace(client_and_log_handler):
    """Test if the details of a stack trace are logged"""
    api_client, handler = client_and_log_handler

    response = api_client.get("/log/exception")

    assert response.status_code == 200
    assert len(handler.messages) == 1
    msg = json.loads(handler.messages[0])
    assert set(msg.keys()) == constants.STANDARD_MSG_ATTRIBUTES.union({"exc_info", "filename"})
    assert msg["filename"] == pathlib.Path(__file__).name, "File name for exception not logged"
    assert "Traceback (most recent call last):" in msg["exc_info"], "Not a stack trace"
    assert "RuntimeError" in msg["exc_info"], "Exception type not logged"
    assert len(msg["exc_info"].split("\n")) > 2, "Stacktrace doesn't have multiple lines"


def test_request_instrumentation(client_and_log_handler):
    """Test if a request log is written"""
    api_client, _ = client_and_log_handler
    request_logger = logging.getLogger("fastapi-request-logger")
    handler = FormattedMessageCollectorHandler()
    request_logger.addHandler(handler)

    response = api_client.get("/log/levels/debug")

    assert response.status_code == 200
    assert len(handler.messages) == 1


def test_excluded_from_request_instrumentation(client_and_log_handler):
    """Test if endpoints can be excluded from the request log"""
    api_client, _ = client_and_log_handler
    request_logger = logging.getLogger("fastapi-request-logger")
    handler = FormattedMessageCollectorHandler()
    request_logger.addHandler(handler)

    response = api_client.get("/no-request-instrumentation")

    assert response.status_code == 200
    assert len(handler.messages) == 0
