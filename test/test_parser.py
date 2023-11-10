import pytest
import json
from unittest import mock

from jsonschema.exceptions import ValidationError


from ohme import parser


class TestLoadFileAsJson:
    def test_load_file_as_json_success(self):
        # Test with valid JSON
        file_content = '{"key": "value"}'
        expected_output = {"key": "value"}

        # Mocking the open function to return the file_content
        mock_open = mock.mock_open(read_data=file_content)
        with mock.patch("builtins.open", mock_open):
            assert parser.load_file_as_json("dummy_path") == expected_output

    def test_load_file_as_json_invalid_json(self):
        # Test with invalid JSON
        file_content = '{"key": "value",}'

        # Mocking the open function to return the file_content
        mock_open = mock.mock_open(read_data=file_content)
        with mock.patch("builtins.open", mock_open):
            with pytest.raises(json.JSONDecodeError):
                parser.load_file_as_json("dummy_path")

    def test_load_file_as_json_file_not_found(self):
        # Test when file is not found
        with pytest.raises(FileNotFoundError):
            parser.load_file_as_json("non_existent_path")


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
            "ohme.parser.load_file_as_json", return_value=mock_schema_file_content
        ) as mock_load_file_as_json:
            result = parser.get_ohme_minimum_schema()

        assert mock_load_file_as_json.call_count == 1
        expected_result = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "array",
            "items": mock_schema_file_content,
        }

        assert result == expected_result

    def test_get_ohme_minimum_schema_file_not_found(self):
        # Mock the loading of the JSON file to raise FileNotFoundError
        with mock.patch(
            "ohme.parser.load_file_as_json", side_effect=FileNotFoundError()
        ):
            with pytest.raises(FileNotFoundError):
                parser.get_ohme_minimum_schema()

    def test_get_ohme_minimum_schema_json_load_error(self):
        # Mock the loading of the JSON file to raise json.JSONDecodeError
        with mock.patch(
            "ohme.parser.load_file_as_json",
            side_effect=json.JSONDecodeError("msg", "doc", 0),
        ):
            with pytest.raises(json.JSONDecodeError):
                parser.get_ohme_minimum_schema()


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

    valid_response = [{"mode": "DISCONNECTED"}, {"mode": "RETRIEVING_SOC"}]
    invalid_response_no_mode = [
        {"not_mode": "DISCONNECTED"},
        {"also_not_mode": "RETRIEVING_SOC"},
    ]

    invalid_response_one_mode = [
        {"mode": "DISCONNECTED"},
        {"not_mode": "RETRIEVING_SOC"},
    ]

    invalid_response_invalid_data = [
        {"mode": 123},
    ]

    def test_validate_against_schema_success(self):
        # Test that the function returns the charge sessions when the response is valid
        result = parser.validate_against_schema(self.valid_schema, self.valid_response)
        assert result == self.valid_response

    @pytest.mark.parametrize(
        "response, error_message",
        [
            (
                invalid_response_no_mode,
                "'mode' is a required property",
            ),
            (invalid_response_invalid_data, "123 is not of type 'string'"),
            (
                invalid_response_one_mode,
                "'mode' is a required property",
            ),
        ],
    )
    def test_validate_against_schema_errors(self, response, error_message, caplog):
        # Test that the function raises specific exceptions with the correct error messages
        with pytest.raises(Exception, match=error_message):
            parser.validate_against_schema(self.valid_schema, response)
        assert "Schema validation failed" in caplog.text


class TestIsChargingSessionActive:
    def test_is_charging_session_active_all_disconnected(self, caplog):
        charge_sessions = [
            {"mode": "DISCONNECTED"},
            {"mode": "DISCONNECTED"},
            {"mode": "DISCONNECTED"},
        ]
        assert parser.is_charging_session_active(charge_sessions) is False
        assert "Unknown mode" not in caplog.text

    def test_is_charging_session_active_some_connected(self, caplog):
        charge_sessions = [
            {"mode": "DISCONNECTED"},
            {"mode": "RETRIEVING_SOC"},
            {"mode": "DISCONNECTED"},
        ]
        assert parser.is_charging_session_active(charge_sessions) is True
        assert "Unknown mode" not in caplog.text

    def test_is_charging_session_active_unknown_mode(self, caplog):
        charge_sessions = [
            {"mode": "DISCONNECTED"},
            {"mode": "UNKNOWN_MODE"},
            {"mode": "DISCONNECTED"},
        ]
        assert parser.is_charging_session_active(charge_sessions) is True
        assert "Unknown mode UNKNOWN_MODE found in chargeStatus" in caplog.text

    def test_is_charging_session_active_empty_list(self, caplog):
        charge_sessions = []
        assert parser.is_charging_session_active(charge_sessions) is False
        assert "Unknown mode" not in caplog.text
