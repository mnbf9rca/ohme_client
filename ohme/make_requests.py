import httpx
import logging

logger = logging.getLogger(__name__)


class SendRequestError(Exception):
    """Exception raised for errors in the send_request function."""

    pass


def post_dict(
    url: str, headers: dict[str, str], body: dict[str, str]
) -> httpx.Response:
    try:
        request = httpx.Request("POST", url=url, headers=headers, data=body)

        with httpx.Client(timeout=10.0) as client:
            response = client.send(request)
            response.raise_for_status()
            return response
    except httpx.HTTPError as e:
        logger.exception(e)
        raise SendRequestError(
            f"HTTP error occurred while sending request to {url}"
        ) from e
    except Exception as e:
        logger.exception(e)
        raise e
