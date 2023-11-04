import pytest
import httpx
from ohme.make_requests import post_dict, SendRequestError
from unittest.mock import MagicMock, patch


class TestPostDict:
    @pytest.fixture(autouse=True)
    def setup_method(self, monkeypatch):
        # Mock the httpx.Request constructor
        self.mock_request = MagicMock()
        monkeypatch.setattr("httpx.Request", lambda *args, **kwargs: self.mock_request)

    def test_successful_post(self, monkeypatch):
        # Mock the httpx.Client.send method to return a successful response
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None  # No exception is raised
        monkeypatch.setattr("httpx.Client.send", lambda self, request: mock_response)

        response = post_dict(
            "https://example.com", {"Header": "Value"}, {"Param": "Value"}
        )

        # Assert the response is the mocked response
        assert response == mock_response

    def test_http_error(self, monkeypatch):
        # Mock the httpx.Client.send method to raise an httpx.HTTPError
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPError("HTTP Error")
        monkeypatch.setattr("httpx.Client.send", lambda self, request: mock_response)

        with pytest.raises(SendRequestError) as exc_info:
            post_dict("https://example.com", {"Header": "Value"}, {"Param": "Value"})
        assert (
            str(exc_info.value)
            == "HTTP error occurred while sending request to https://example.com"
        )

    def test_other_error(self, monkeypatch):
        # Mock the httpx.Client.send method to raise a generic exception
        monkeypatch.setattr(
            "httpx.Client.send", lambda self, request: 1 / 0
        )  # This will raise a ZeroDivisionError

        with pytest.raises(ZeroDivisionError):
            post_dict("https://example.com", {"Header": "Value"}, {"Param": "Value"})

    @patch.object(httpx, "Request")
    @patch.object(httpx.Client, "send")
    def test_request_parameters(self, mock_send, mock_request):
        # Mock the response
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_send.return_value = mock_response

        # Mock the request
        mock_request_instance = MagicMock()
        mock_request.return_value = mock_request_instance

        # Call the function
        post_dict("https://example.com", {"Header": "Value"}, {"Param": "Value"})

        # Check the parameters passed to httpx.Request constructor
        mock_request.assert_called_once_with(
            "POST",
            url="https://example.com",
            headers={"Header": "Value"},
            data={"Param": "Value"},
        )

        # Check that the mocked request object was passed to the send() method
        mock_send.assert_called_once_with(mock_request_instance)
