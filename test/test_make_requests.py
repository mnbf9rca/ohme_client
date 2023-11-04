import os
import sys
import pytest
import httpx
from unittest.mock import patch, Mock

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))
from ohme import make_requests


class TestSendRequest:
    # Parameterized test for successful requests
    @pytest.mark.parametrize(
        "method, params, data, json_body, response_content, response_headers, expected_json",
        [
            ("GET", None, None, None, b"OK", {"Content-Type": "text/plain"}, None),
            (
                "POST",
                {"key1": "value1"},
                None,
                None,
                b"OK",
                {"Content-Type": "text/plain"},
                None,
            ),
            (
                "POST",
                None,
                {"key2": "value2"},
                None,
                b'{"status": "OK"}',
                {"Content-Type": "application/json"},
                {"status": "OK"},
            ),
            (
                "POST",
                None,
                {"key2": "value2"},
                None,
                b'{"status": "OK"}',
                {"Content-Type": "text/plain"},  # missing JSON content type is ignored
                {"status": "OK"},
            ),
            (
                "GET",
                None,
                None,
                None,
                b"not json",
                {"Content-Type": "application/json"},
                None,
            ),
        ],
    )
    def test_send_request_success(
        self,
        method,
        params,
        data,
        json_body,
        response_content,
        response_headers,
        expected_json,
    ):
        # Create Response instance
        mock_response = httpx.Response(
            200, content=response_content, headers=response_headers
        )
        mock_response.raise_for_status = Mock(return_value=None)

        # Mock Client and Request
        with patch("httpx.Client.send", return_value=mock_response) as mock_send:
            with patch("httpx.Request", return_value="mock_request") as mock_request:
                response = make_requests.send_request(
                    method,
                    url="http://test.com",
                    headers={"Authorization": "Bearer token"},
                    params=params,
                    data=data,
                    json=json_body,
                )

        # Validate
        mock_request.assert_called_once_with(
            method,
            url="http://test.com",
            params=params,
            headers={"Authorization": "Bearer token"},
            data=data,
            json=json_body,
        )
        mock_send.assert_called_once_with("mock_request")
        assert response["status_code"] == 200
        assert response["raw_data"] == response_content
        assert response["json"] == expected_json
        assert all(
            response["headers"].get(key.lower()) == value.lower()
            for key, value in response_headers.items()
        )

    # Test for HTTPError
    def test_send_request_http_error(self):
        mock_response = Mock(spec=httpx.Response)
        mock_response.raise_for_status.side_effect = httpx.HTTPError(
            "Testing that we catch Error"
        )

        with patch("httpx.Client.send", return_value=mock_response):
            with pytest.raises(make_requests.SendRequestError) as e:
                make_requests.send_request("GET", url="http://test.com")
            assert "Testing that we catch Error" in str(e.value)

    # Test for generic Exception
    def test_send_request_generic_error(self):
        with patch(
            "httpx.Client.send",
            side_effect=Exception("Testing that we catch Error again"),
        ):
            with pytest.raises(Exception) as e:
                make_requests.send_request("GET", url="http://test.com")
            assert "Testing that we catch Error again" in str(e.value)
