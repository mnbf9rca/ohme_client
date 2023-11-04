import os
from typing import Any

from urllib.parse import urljoin
from dotenv_vault import load_dotenv

from .make_requests import post_dict

load_dotenv()


def get_firebase_auth_headers() -> dict[str, str]:
    """
    Generate authentication headers required for Firebase API requests.

    The headers are constructed based on environment variables which should have been
    set prior to calling this function. The required environment variables are:
    - ohme_firebase_token
    - ohme_firebase_installation_token
    - ohme_firebase_device_token

    :return: A dictionary containing the authentication headers.
    :rtype: dict[str, str]
    """
    token = os.environ["ohme_firebase_token"]
    installation_token = os.environ["ohme_firebase_installation_token"]
    device_token = os.environ["ohme_firebase_device_token"]
    return {
        "Accept": "*/*",
        "X-firebase-client": "apple-platform/ios apple-sdk/20C52 appstore/true deploy/cocoapods device/iPhone15,2 fire-abt/8.2.0 fire-analytics/8.1.1 fire-auth/8.2.0 fire-dl/8.2.0 fire-fcm/8.2.0 fire-install/8.2.0 fire-ios/8.2.0 fire-rc/8.2.0 firebase-crashlytics/8.2.0 os-version/17.0.3 xcode/14C18",  # noqa: E501
        "Authorization": f"AidLogin {device_token}:{installation_token}",
        "X-firebase-client-log-type": "0",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "en-GB,en;q=0.9",
        "app": "io.ohme.ios.OhmE",
        "Conetent-Type": "application/x-www-form-urlencoded",
        "User-Agent": "Ohme/543 CFNetwork/1474 Darwin/23.0.0",
        "Connection": "keep-alive",
        "info": "",
        "x-goog-firebase-installations-auth": f"{token}",
    }


def get_firebase_auth_body() -> dict[str, str]:
    """
    Generate the request body required for Firebase API requests.

    The body is constructed based on an environment variable which should have been
    set prior to calling this function. The required environment variable is:
    - ohme_firebase_device_token

    :return: A dictionary containing the key-value pairs for the request body.
    :rtype: dict[str, str]
    """
    device_token = os.environ["ohme_firebase_device_token"]
    return {
        "X-osv": "17.0.3",
        "device": device_token,
        "X-scope": "*",
        "plat": "2",
        "app": "io.ohme.ios.OhmE",
        "app_ver": "1.28.1",
        "X-cliv": "fiid-8.2.0",
        "sender": "206163667850",
        "X-subtype": "206163667850",
        "appid": "f1TW3-vVsEbwuIuDui2MoQ",
        "gmp_app_id": "1:206163667850:ios:6f2cd746818dd6de",
    }


def get_firebase_token() -> str:
    """
    Retrieve a Firebase token by sending a HTTP request to the Firebase API.

    This function calls `get_firebase_auth_headers` and `get_firebase_auth_body` to
    obtain the necessary headers and body for the request, then sends a HTTP request
    to the Firebase API to obtain a Firebase token.

    :return: The Firebase token retrieved from the API.
    :rtype: str
    :raises Exception: If there is an error retrieving the token from the API.
    """
    headers = get_firebase_auth_headers()
    body = get_firebase_auth_body()
    request_url = "https://fcmtoken.googleapis.com/register"
    response = post_dict(request_url, headers, body)
    # body looks like token=f1TW3-vVsEbwuIuDui2MoQ:APA91b...
    # or error=Missing+registration+token
    # 1. Remove token=
    # 2. Split on =
    # 3. Return the second element
    if response.text.split("=")[0] == "token":
        return response.text.split("=")[1]
    else:
        raise Exception(f"Error getting firebase token: {response.text}")
