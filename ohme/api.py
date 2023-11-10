from dotenv import load_dotenv
import os
import sys
from typing import Any, Dict, List
from urllib.parse import urljoin
import logging

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))
from ohme.make_requests import send_request  # noqa: E402
from ohme.firebase import get_firebase_token  # noqa: E402

load_dotenv()


def create_headers(firebase_token: str) -> dict[str, str]:
    """
    Generate HTTP headers for requests to the Ohme API.

    This function creates a dictionary containing the necessary HTTP headers,
    including the Authorization header, which is constructed using the provided
    Firebase token.

    Parameters:
    - firebase_token (str): The Firebase token used for authorization.

    Returns:
    - dict[str, str]: A dictionary containing the HTTP headers.

    Raises:
    - TypeError: If the provided firebase_token is not a string of at least 1 character.

    Example:
    >>> create_headers("your_firebase_token")
    {
        "Connection": "keep-alive",
        "Accept": "*/*",
        "User-Agent": "OhmE/543 CFNetwork/1474 Darwin/23.0.0",
        "Accept-Language": "en-GB,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Authorization": "Firebase your_firebase_token",
    }
    """
    if not isinstance(firebase_token, str) or len(firebase_token) == 0:
        raise TypeError(
            f"firebase_token must be a string with length > 0, not {type(firebase_token)} with length {len(firebase_token)}"  # noqa: E501
        )
    return {
        "Connection": "keep-alive",
        "Accept": "*/*",
        "User-Agent": "OhmE/543 CFNetwork/1474 Darwin/23.0.0",
        "Accept-Language": "en-GB,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Authorization": f"Firebase {firebase_token}",
    }


def get_ohme_url():
    """
    Retrieve the base URL for Ohme API requests from environment variables and append the charge sessions endpoint.

    The function reads the 'ohme_api_base' environment variable, checks if it is set, and appends '/v1/chargeSessions'
    to construct the full URL.

    Raises:
        KeyError: If the 'ohme_api_base' environment variable is not set or is empty.

    Returns:
        str: The complete URL for Ohme charge sessions API endpoint.
    """
    try:
        ohme_base_url = os.environ["ohme_api_base"]
        if not ohme_base_url:
            raise ValueError("ohme_api_base is empty")
    except KeyError:
        raise KeyError("ohme_api_base not set in environment")
    return urljoin(ohme_base_url, "/v1/chargeSessions")


def get_charging_sessions(firebase_token: str) -> List[Dict[str, Any]]:
    """
    Fetches and validates charging sessions from the Ohme API.

    Parameters:
        firebase_token (str): The Firebase authentication token.

    Returns:
        List[Dict[str, Any]]: A list of charging sessions.

    Raises:
        Exception: If the API response is invalid or fails schema validation.
    """
    try:
        # Get schema, headers, and URL
        #
        headers = create_headers(firebase_token)
        url = get_ohme_url()

        # Send the request and validate the response
        response = send_request("GET", url, headers)

        # return charge_sessions
        return extract_json_from_response(response)

    except Exception as e:
        logging.error("Failed to fetch or validate charging sessions", exc_info=True)
        raise e


def extract_json_from_response(response: str) -> dict[str, any]:
    if "json" not in response:
        raise Exception("No json field in response to array_schema request", response)
    return response["json"]


# allow debugging of this file
if __name__ == "__main__":  # pragma: no cover
    firebase_token = get_firebase_token().get("idToken")
    print(get_charging_sessions(firebase_token))
    # i = 0
    # while True:
    #     with open(f"tmp/test_data/{i}.json", "x") as f:
    #         response = get_charging_sessions(firebase_token)
    #         json.dump(response, f, indent=2)
    #         print(f"Response written to test_data/{i}.json")
    #     i += 1
    #     time.sleep(60)
