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


class TestGetOhmeMinimumSchema:
    @pytest.fixture
    def mock_schema_file_content(self):
        return {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": {"field1": {"type": "string"}, "field2": {"type": "number"}},
        }

    def test_get_ohme_minimum_schema_success(self, mock_schema_file_content):
        # Mock the loading of the JSON file
        with mock.patch(
            "ohme.api.load_file_as_json", return_value=mock_schema_file_content
        ) as mock_load_file_as_json:
            result = api.get_ohme_minimum_schema()

        assert mock_load_file_as_json.call_count == 1
        expected_result = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "array",
            "items": mock_schema_file_content,
        }

        assert result == expected_result

    def test_get_ohme_minimum_schema_file_not_found(self):
        # Mock the loading of the JSON file to raise FileNotFoundError
        with mock.patch("ohme.api.load_file_as_json", side_effect=FileNotFoundError()):
            with pytest.raises(FileNotFoundError):
                api.get_ohme_minimum_schema()

    def test_get_ohme_minimum_schema_json_load_error(self):
        # Mock the loading of the JSON file to raise json.JSONDecodeError
        with mock.patch(
            "ohme.api.load_file_as_json",
            side_effect=json.JSONDecodeError("msg", "doc", 0),
        ):
            with pytest.raises(json.JSONDecodeError):
                api.get_ohme_minimum_schema()


class TestLoadFileAsJson:
    def test_load_file_as_json_success(self):
        # Test with valid JSON
        file_content = '{"key": "value"}'
        expected_output = {"key": "value"}

        # Mocking the open function to return the file_content
        mock_open = mock.mock_open(read_data=file_content)
        with mock.patch("builtins.open", mock_open):
            assert api.load_file_as_json("dummy_path") == expected_output

    def test_load_file_as_json_invalid_json(self):
        # Test with invalid JSON
        file_content = '{"key": "value",}'

        # Mocking the open function to return the file_content
        mock_open = mock.mock_open(read_data=file_content)
        with mock.patch("builtins.open", mock_open):
            with pytest.raises(json.JSONDecodeError):
                api.load_file_as_json("dummy_path")

    def test_load_file_as_json_file_not_found(self):
        # Test when file is not found
        with pytest.raises(FileNotFoundError):
            api.load_file_as_json("non_existent_path")


class TestIsChargingSessionActive:
    def test_is_charging_session_active_all_disconnected(self, caplog):
        charge_sessions = [
            {"mode": "DISCONNECTED"},
            {"mode": "DISCONNECTED"},
            {"mode": "DISCONNECTED"},
        ]
        assert api.is_charging_session_active(charge_sessions) is False
        assert "Unknown mode" not in caplog.text

    def test_is_charging_session_active_some_connected(self, caplog):
        charge_sessions = [
            {"mode": "DISCONNECTED"},
            {"mode": "RETRIEVING_SOC"},
            {"mode": "DISCONNECTED"},
        ]
        assert api.is_charging_session_active(charge_sessions) is True
        assert "Unknown mode" not in caplog.text

    def test_is_charging_session_active_unknown_mode(self, caplog):
        charge_sessions = [
            {"mode": "DISCONNECTED"},
            {"mode": "UNKNOWN_MODE"},
            {"mode": "DISCONNECTED"},
        ]
        assert api.is_charging_session_active(charge_sessions) is True
        assert "Unknown mode UNKNOWN_MODE found in chargeStatus" in caplog.text

    def test_is_charging_session_active_empty_list(self, caplog):
        charge_sessions = []
        assert api.is_charging_session_active(charge_sessions) is False
        assert "Unknown mode" not in caplog.text


class TestValidateChargeSessionResponse:
    # Sample schema and response
    valid_schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "array",
        "items": {
            "type": "object",
            "properties": {"mode": {"type": "string"}},
            "required": ["mode"],
        },
    }

    valid_response = {"json": [{"mode": "DISCONNECTED"}, {"mode": "RETRIEVING_SOC"}]}
    invalid_response_no_json = {
        "data": [{"mode": "DISCONNECTED"}, {"mode": "RETRIEVING_SOC"}]
    }
    invalid_response_invalid_data = {
        "json": [{"mode": "DISCONNECTED"}, {"unknown": "RETRIEVING_SOC"}]
    }

    def test_validate_against_schema_success(self):
        # Test that the function returns the charge sessions when the response is valid
        result = api.validate_against_schema(self.valid_schema, self.valid_response)
        assert result == self.valid_response["json"]

    @pytest.mark.parametrize(
        "response, error_message",
        [
            (
                invalid_response_no_json,
                "No json field in response to array_schema request",
            ),
            (invalid_response_invalid_data, "'mode' is a required property"),
        ],
    )
    def test_validate_against_schema_errors(self, response, error_message):
        # Test that the function raises specific exceptions with the correct error messages
        with pytest.raises(Exception, match=error_message):
            api.validate_against_schema(self.valid_schema, response)

    def test_validate_against_schema_logs_error_on_validation_error(self, caplog):
        # Test that the function logs an error message when schema validation fails
        with pytest.raises(ValidationError, match="'mode' is a required property"):
            api.validate_against_schema(
                self.valid_schema, self.invalid_response_invalid_data
            )
        assert "Schema validation failed" in caplog.text


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
    def mock_validate_against_schema(self):
        with mock.patch("ohme.api.validate_against_schema") as mock_validate:
            # Return input as is
            mock_validate.side_effect = lambda schema, response: response["json"]
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
        mock_validate_against_schema,
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
        mock_validate_against_schema.assert_called_once_with(mock.ANY, response_json)

    def test_get_charging_sessions_exception_handling(self, caplog):
        # Mocking the functions to raise an Exception
        with mock.patch(
            "ohme.api.send_request", side_effect=Exception("Request error")
        ), mock.patch("ohme.api.create_headers"), mock.patch(
            "ohme.api.get_ohme_url"
        ), mock.patch(
            "ohme.api.get_ohme_minimum_schema"
        ), caplog.at_level(
            logging.ERROR
        ):
            # Assert that the function raises the same Exception and logs the error
            with pytest.raises(Exception, match="Request error"):
                api.get_charging_sessions("sample_token")

            assert "Failed to fetch or validate charging sessions" in caplog.text
