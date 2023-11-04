import os
import sys
import httpx
from typing import Dict

from urllib.parse import urljoin
from dotenv_vault import load_dotenv

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))
from ohme.make_requests import send_request  # noqa: E402


load_dotenv()


def get_firebase_auth_headers() -> dict[str, str]:
    """
    Generate authentication headers required for Firebase API requests.

    :return: A dictionary containing the authentication headers.
    :rtype: dict[str, str]
    """
    return {
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


def get_firebase_auth_body() -> dict[str, str]:
    """
    Generate the request body required for Firebase API requests.

    The body is constructed based on the following environment variables which
    should have been     set prior to calling this function. The required environment
    variable is:
    - ohme_username
    - ohme_password

    :return: A dictionary containing the key-value pairs for the request body.
    :rtype: dict[str, str]
    """
    username = os.environ["ohme_username"]
    password = os.environ["ohme_password"]
    return {"email": username, "password": password, "returnSecureToken": True}


def get_firebase_sdk_key() -> str:
    return os.environ["firebase_sdk_key"]


def get_firebase_token() -> Dict[str, str]:
    """
    Retrieve a Firebase token by sending a HTTP request to the Firebase API.

    :return: A dictionary containing the Firebase token, expiration time, and refresh token.
    :rtype: Dict[str, str]
    :raises Exception: If there is an error retrieving the token from the API.
    """
    headers = get_firebase_auth_headers()
    body = get_firebase_auth_body()

    base_url = "https://www.googleapis.com"
    url_path = "/identitytoolkit/v3/relyingparty/verifyPassword"
    request_url = urljoin(base_url, url_path)
    params = {"key": get_firebase_sdk_key()}

    try:
        response = send_request(
            "POST", request_url, headers=headers, json=body, params=params
        )

        if response.get("json") is None:
            raise Exception(f"Error getting firebase token: Invalid JSON: {response}")
        response_data = response.get("json")

        # Validate the response
        # body looks like this.
        # {
        # "kind": "identitytoolkit#VerifyPasswordResponse",
        # "localId": "5w...A3",
        # "email": "r...@...m",
        # "displayName": "R...k",
        # "idToken": "eyJhbG...JWT...6486MLUsfPAw",
        # "registered": true,
        # "refreshToken": "AMf-vBwc-A4...2NrIg",
        # "expiresIn": "3600"
        # }
        if (
            not response_data.get("idToken")
            or not response_data.get("expiresIn")
            or not response_data.get("refreshToken")
        ):
            raise Exception(f"Error getting firebase token: {response}")

        return {
            "idToken": response_data["idToken"],
            "expiresIn": response_data["expiresIn"],
            "refreshToken": response_data["refreshToken"],
        }

    except httpx.HTTPError as e:
        raise Exception(f"HTTP error occurred while sending request: {str(e)}") from e
    except Exception as e:
        raise Exception(f"An unexpected error occurred: {str(e)}") from e
