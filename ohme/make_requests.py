import httpx
import logging
from typing import TypedDict, Optional, Dict, Union

logger = logging.getLogger(__name__)


class SendRequestError(Exception):
    """Exception raised for errors in the send_request function."""

    pass


def send_request(
    method: str,
    url: str,
    headers: dict[str, str] = None,
    params: dict[str, str] = None,
    **kwargs,
) -> dict:
    """
    Send an HTTP request and return the response data as a dictionary.

    This function constructs and sends an HTTP request using the given parameters.
    It returns a dictionary containing the status code, raw data, parsed JSON data (if applicable),
    and headers from the response.

    :param method: The HTTP method (e.g., "GET", "POST").
    :type method: str
    :param url: The URL to which the request is sent.
    :type url: str
    :param headers: The headers to include in the request, defaults to None.
    :type headers: dict[str, str], optional
    :param params: The query parameters to include in the request, defaults to None.
    :type params: dict[str, str], optional
    :param kwargs: Additional arguments to pass to the httpx.Request constructor.
    :return: A dictionary containing the status code, raw data, parsed JSON data (if applicable),
             and headers from the response.
    :rtype: dict
    :raises SendRequestError: If an HTTP error occurs while sending the request.
    :raises Exception: If a generic exception occurs while sending the request.
    """
    try:
        request = httpx.Request(
            method, url=url, params=params, headers=headers, **kwargs
        )

        with httpx.Client(timeout=10.0) as client:
            response = client.send(request)
            response.raise_for_status()

            # Attempt to parse JSON
            try:
                json_data = response.json()
            except ValueError:
                json_data = None

            # Construct the response dictionary
            response_data = {
                "status_code": response.status_code,
                "raw_data": response.content,
                "json": json_data,
                "headers": dict(response.headers),
            }

            return response_data

    except httpx.HTTPError as e:
        logger.exception(e)
        raise SendRequestError(
            f"HTTP error occurred while sending request to {url}: {str(e)}"
        ) from e
    except Exception as e:
        logger.exception(e)
        raise e
