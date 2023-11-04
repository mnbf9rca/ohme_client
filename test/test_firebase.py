import os
import pytest
from unittest.mock import Mock

from ohme.firebase import (
    get_firebase_auth_headers,
    get_firebase_auth_body,
    get_firebase_token,
)


class TestGetFirebaseAuthHeaders:
    @pytest.fixture(autouse=True)
    def setup_method(self, monkeypatch):
        # Mock environment variables
        monkeypatch.setenv("ohme_firebase_token", "test_token")
        monkeypatch.setenv(
            "ohme_firebase_installation_token", "test_installation_token"
        )
        monkeypatch.setenv("ohme_firebase_device_token", "test_device_token")

    def test_get_firebase_auth_headers(self):
        headers = get_firebase_auth_headers()

        assert headers["Accept"] == "*/*"
        assert (
            headers["Authorization"]
            == "AidLogin test_device_token:test_installation_token"
        )
        assert headers["x-goog-firebase-installations-auth"] == "test_token"
        # skipping the other headers for brevity

    def test_missing_environment_variable(self, monkeypatch):
        monkeypatch.delenv("ohme_firebase_token", raising=False)

        with pytest.raises(KeyError):
            get_firebase_auth_headers()


class TestGetFirebaseAuthBody:
    @pytest.fixture(autouse=True)
    def setup_method(self, monkeypatch):
        # Mock environment variable
        monkeypatch.setenv("ohme_firebase_device_token", "test_device_token")

    def test_device_token_mapping(self):
        body = get_firebase_auth_body()
        assert body["device"] == "test_device_token"

    def test_missing_environment_variable(self, monkeypatch):
        monkeypatch.delenv("ohme_firebase_device_token", raising=False)

        with pytest.raises(KeyError):
            get_firebase_auth_body()


class TestGetFirebaseToken:
    @pytest.fixture(autouse=True)
    def setup_method(self, monkeypatch):
        # Mock get_firebase_auth_headers and get_firebase_auth_body
        self.mock_get_firebase_auth_headers = Mock(return_value={"mocked": "headers"})
        self.mock_get_firebase_auth_body = Mock(return_value={"mocked": "body"})
        monkeypatch.setattr(
            "ohme.firebase.get_firebase_auth_headers",
            self.mock_get_firebase_auth_headers,
        )
        monkeypatch.setattr(
            "ohme.firebase.get_firebase_auth_body", self.mock_get_firebase_auth_body
        )

    def test_successful_token_retrieval(self, monkeypatch):
        # Mock send_request for a successful response
        mock_send_request = Mock()
        mock_send_request.return_value.text = "token=sample_token"
        monkeypatch.setattr("ohme.firebase.send_request", mock_send_request)

        token = get_firebase_token()
        assert token == "sample_token"

        # Check that the mocked functions were called with the correct parameters
        self.mock_get_firebase_auth_headers.assert_called()
        self.mock_get_firebase_auth_body.assert_called()
        mock_send_request.assert_called_with(
            "https://fcmtoken.googleapis.com/register",
            {"mocked": "headers"},
            {"mocked": "body"},
        )

    def test_error_response(self, monkeypatch):
        # Mock send_request for an error response
        mock_error_response = Mock()
        mock_error_response.return_value.text = "error=Missing+registration+token"
        monkeypatch.setattr("ohme.firebase.send_request", mock_error_response)

        with pytest.raises(Exception) as exc_info:
            get_firebase_token()
        assert (
            str(exc_info.value)
            == "Error getting firebase token: error=Missing+registration+token"
        )

        # Check that the mocked functions were called with the correct parameters
        self.mock_get_firebase_auth_headers.assert_called()
        self.mock_get_firebase_auth_body.assert_called()
        mock_error_response.assert_called_with(
            "https://fcmtoken.googleapis.com/register",
            {"mocked": "headers"},
            {"mocked": "body"},
        )
