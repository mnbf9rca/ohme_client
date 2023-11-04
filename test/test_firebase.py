import os
import sys
import pytest
import httpx
from unittest.mock import patch, Mock

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))
from ohme import firebase  # noqa: E402


class TestFirebaseHeaders:
    def test_get_firebase_auth_headers(self):
        # Call the function
        headers = firebase.get_firebase_auth_headers()

        # Define expected headers
        expected_headers = {
            "Content-Type": "application/json",
            "Accept": "*/*",
            "X-Firebase-Locale": "en",
            "X-Ios-Bundle-Identifier": "io.ohme.ios.OhmE",
            "Connection": "keep-alive",
            "X-Client-Version": "iOS/FirebaseSDK/8.2.0/FirebaseUI-iOS",
            "User-Agent": "FirebaseAuth.iOS/8.2.0 io.ohme.ios.OhmE/1.28.1 iPhone/17.0.3 hw/iPhone15_2",
            "Accept-Language": "en",
            "Accept-Encoding": "gzip, deflate, br",
        }

        # Validate
        assert headers == expected_headers


class TestFirebaseAuthBody:
    def test_get_firebase_auth_body(self):
        # Mock environment variables
        with patch.dict(
            os.environ, {"ohme_username": "test_user", "ohme_password": "test_pass"}
        ):
            # Call the function
            body = firebase.get_firebase_auth_body()

        # Define expected body
        expected_body = {
            "email": "test_user",
            "password": "test_pass",
            "returnSecureToken": True,
        }

        # Validate
        assert body == expected_body

    def test_get_firebase_auth_body_missing_envvars(self):
        # Ensure environment variables are not set
        if "ohme_username" in os.environ:
            del os.environ["ohme_username"]
        if "ohme_password" in os.environ:
            del os.environ["ohme_password"]

        # Validate that a KeyError is raised
        with pytest.raises(KeyError):
            firebase.get_firebase_auth_body()


class TestFirebaseSdkKey:
    def test_get_firebase_sdk_key_success(self):
        # Mock environment variable
        with patch.dict(os.environ, {"firebase_sdk_key": "test_key"}):
            # Call the function
            sdk_key = firebase.get_firebase_sdk_key()

        # Validate
        assert sdk_key == "test_key"

    def test_get_firebase_sdk_key_failure(self):
        # Ensure environment variable is not set
        if "firebase_sdk_key" in os.environ:
            del os.environ["firebase_sdk_key"]

        # Validate that a KeyError is raised
        with pytest.raises(KeyError):
            firebase.get_firebase_sdk_key()


class TestGetFirebaseToken:
    # Test for successful token retrieval
    @patch("ohme.firebase.get_firebase_auth_headers")
    @patch("ohme.firebase.get_firebase_auth_body")
    @patch("ohme.firebase.get_firebase_sdk_key")
    @patch("ohme.firebase.send_request")
    def test_get_firebase_token_success(
        self,
        mock_send_request,
        mock_get_firebase_sdk_key,
        mock_get_firebase_auth_body,
        mock_get_firebase_auth_headers,
    ):
        # Mock successful response, headers, body, and sdk key
        mock_send_request.return_value = {
            "status_code": 200,
            "raw_data": b'{"idToken": "test_idToken", "expiresIn": "3600", "refreshToken": "test_refreshToken"}',
            "json": {
                "idToken": "test_idToken",
                "expiresIn": "3600",
                "refreshToken": "test_refreshToken",
            },
            "headers": {"Content-Type": "application/json"},
        }
        mock_get_firebase_auth_headers.return_value = {"Authorization": "Bearer token"}
        mock_get_firebase_sdk_key.return_value = "test_sdk_key"

        mock_get_firebase_auth_body.return_value = {
            "email": "test_user",
            "password": "test_pass",
            "returnSecureToken": True,
        }

        result = firebase.get_firebase_token()

        # Validate
        assert result["idToken"] == mock_send_request.return_value["json"]["idToken"]
        assert (
            result["expiresIn"] == mock_send_request.return_value["json"]["expiresIn"]
        )
        assert (
            result["refreshToken"]
            == mock_send_request.return_value["json"]["refreshToken"]
        )

        mock_send_request.assert_called_once_with(
            "POST",
            "https://www.googleapis.com/identitytoolkit/v3/relyingparty/verifyPassword",
            headers=mock_get_firebase_auth_headers.return_value,
            json=mock_get_firebase_auth_body.return_value,
            params={"key": mock_get_firebase_sdk_key.return_value},
        )

    @pytest.mark.parametrize("missing_key", ["idToken", "expiresIn", "refreshToken"])
    @patch("ohme.firebase.get_firebase_auth_headers")
    @patch("ohme.firebase.get_firebase_auth_body")
    @patch("ohme.firebase.get_firebase_sdk_key")
    @patch("ohme.firebase.send_request")
    def test_get_firebase_token_missing_keys(
        self,
        mock_send_request,
        mock_get_firebase_sdk_key,
        mock_get_firebase_auth_body,
        mock_get_firebase_auth_headers,
        missing_key,
    ):
        # Remove a key from the response json
        response_json = {
            "idToken": "test_idToken",
            "expiresIn": "3600",
            "refreshToken": "test_refreshToken",
        }
        del response_json[missing_key]

        mock_send_request.return_value = {
            "status_code": 200,
            "raw_data": b'{"status": "OK"}',
            "json": response_json,
            "headers": {"Content-Type": "application/json"},
        }

        with pytest.raises(Exception, match="Error getting firebase token"):
            firebase.get_firebase_token()

    # Test for null json in response
    @patch("ohme.firebase.get_firebase_auth_headers")
    @patch("ohme.firebase.get_firebase_auth_body")
    @patch("ohme.firebase.get_firebase_sdk_key")
    @patch("ohme.firebase.send_request")
    def test_get_firebase_token_null_json(
        self,
        mock_send_request,
        mock_get_firebase_sdk_key,
        mock_get_firebase_auth_body,
        mock_get_firebase_auth_headers,
    ):
        mock_send_request.return_value = {
            "status_code": 200,
            "raw_data": b"Invalid JSON",
            "json": None,
            "headers": {"Content-Type": "application/json"},
        }

        with pytest.raises(
            Exception, match="Error getting firebase token: Invalid JSON"
        ):
            firebase.get_firebase_token()

    # Test for HTTP error
    @patch("ohme.firebase.get_firebase_auth_headers")
    @patch("ohme.firebase.get_firebase_auth_body")
    @patch("ohme.firebase.get_firebase_sdk_key")
    @patch("ohme.firebase.send_request")
    def test_get_firebase_token_http_error(
        self,
        mock_send_request,
        mock_get_firebase_sdk_key,
        mock_get_firebase_auth_body,
        mock_get_firebase_auth_headers,
    ):
        mock_send_request.side_effect = httpx.HTTPError("Generated HTTP error")

        with pytest.raises(Exception, match="Generated HTTP error"):
            firebase.get_firebase_token()

    # Test for unexpected error
    @patch("ohme.firebase.get_firebase_auth_headers")
    @patch("ohme.firebase.get_firebase_auth_body")
    @patch("ohme.firebase.get_firebase_sdk_key")
    @patch("ohme.firebase.send_request")
    def test_get_firebase_token_unexpected_error(
        self,
        mock_send_request,
        mock_get_firebase_sdk_key,
        mock_get_firebase_auth_body,
        mock_get_firebase_auth_headers,
    ):
        mock_send_request.side_effect = Exception("Generated Unexpected error")

        with pytest.raises(Exception, match="Generated Unexpected error"):
            firebase.get_firebase_token()
