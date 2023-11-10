import pytest
from unittest import mock
import json
from jsonschema.exceptions import ValidationError
import logging

import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))
from ohme import api  # noqa: E402


class TestCreateHeaders:
    @pytest.mark.parametrize(
        "firebase_token, expected_auth_header",
        [
            ("test_token_1", "Firebase test_token_1"),
        ],
    )
    def test_create_headers(self, firebase_token, expected_auth_header):
        # Call the function with the test parameters
        headers = api.create_headers(firebase_token)

        # Assertions to ensure the headers are correctly set
        assert headers["Connection"] == "keep-alive"
        assert headers["Accept"] == "*/*"
        assert headers["User-Agent"] == "OhmE/543 CFNetwork/1474 Darwin/23.0.0"
        assert headers["Accept-Language"] == "en-GB,en;q=0.9"
        assert headers["Accept-Encoding"] == "gzip, deflate, br"
        assert headers["Authorization"] == expected_auth_header

    @pytest.mark.parametrize("firebase_token", [None, 123, True, [], {}, ""])
    def test_create_headers_with_invalid_token_type(self, firebase_token):
        # Assertion to ensure TypeError is raised when token is not a string
        with pytest.raises(TypeError):
            api.create_headers(firebase_token)


class TestGetOhmeUrl:
    @pytest.mark.parametrize(
        "base_url, expected_url",
        [
            ("http://example.com", "http://example.com/v1/chargeSessions"),
            ("http://", "http:///v1/chargeSessions"),
        ],
    )
    def test_get_ohme_url_valid(self, base_url, expected_url):
        with mock.patch.dict(os.environ, {"ohme_api_base": base_url}):
            assert api.get_ohme_url() == expected_url

    @pytest.mark.parametrize(
        "env_vars, expected_exception, expected_message",
        [
            ({"ohme_api_base": ""}, ValueError, "ohme_api_base is empty"),
            ({}, KeyError, "ohme_api_base not set in environment"),
        ],
    )
    def test_get_ohme_url_invalid(self, env_vars, expected_exception, expected_message):
        with mock.patch.dict(os.environ, env_vars, clear=True):
            with pytest.raises(expected_exception, match=expected_message):
                api.get_ohme_url()


class TestGetChargingSessions:
    @pytest.fixture
    def mock_send_request(self):
        with mock.patch("ohme.api.send_request") as mock_request:
            yield mock_request

    @pytest.fixture
    def mock_create_headers(self):
        with mock.patch("ohme.api.create_headers") as mock_headers:
            mock_headers.return_value = {"Authorization": "Firebase sample_token"}
            yield mock_headers

    @pytest.fixture
    def mock_get_ohme_url(self):
        with mock.patch("ohme.api.get_ohme_url") as mock_url:
            mock_url.return_value = "http://ohme-url"
            yield mock_url

    @pytest.fixture
    def mock_extract_json_from_response(self):
        with mock.patch("ohme.api.extract_json_from_response") as mock_validate:
            # Return input as is
            mock_validate.side_effect = lambda response: response["json"]
            yield mock_validate

    @pytest.mark.parametrize(
        "response_json, expected_output",
        [
            ({"json": [{"mode": "DISCONNECTED"}]}, [{"mode": "DISCONNECTED"}]),
            ({"json": [{"mode": "CALCULATING"}]}, [{"mode": "CALCULATING"}]),
        ],
    )
    def test_get_charging_sessions_successful(
        self,
        mock_send_request,
        mock_create_headers,
        mock_get_ohme_url,
        mock_extract_json_from_response,
        response_json,
        expected_output,
    ):
        # Mock successful response
        mock_send_request.return_value = response_json

        request_token = "sample_token"

        # Call the function
        result = api.get_charging_sessions(request_token)

        # Assert the result
        assert result == expected_output

        # Assert mocks were called with correct arguments
        mock_send_request.assert_called_once_with(
            "GET",
            mock_get_ohme_url.return_value,
            mock_create_headers.return_value,
        )
        mock_create_headers.assert_called_once_with(request_token)
        mock_get_ohme_url.assert_called_once()
        mock_extract_json_from_response.assert_called_once_with(response_json)

    def test_get_charging_sessions_exception_handling(
        self, mock_get_ohme_url, mock_create_headers, mock_send_request, caplog
    ):
        # Mocking the functions to raise an Exception
        mock_send_request.side_effect = Exception("Request error")

        caplog.at_level(
            logging.ERROR,
        )
        # Assert that the function raises the same Exception and logs the error
        with pytest.raises(Exception, match="Request error"):
            api.get_charging_sessions("sample_token")

        assert "Failed to fetch or validate charging sessions" in caplog.text
