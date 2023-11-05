from dotenv import load_dotenv
import os
import sys
import json
from typing import Any, Dict, List
from urllib.parse import urljoin
from jsonschema import validate
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
        array_of_ohme_charge_sessions = get_ohme_minimum_schema()
        headers = create_headers(firebase_token)
        url = get_ohme_url()

        # Send the request and validate the response
        response = send_request("GET", url, headers)
        charge_sessions = validate_against_schema(
            array_of_ohme_charge_sessions, response
        )

        return charge_sessions

    except Exception as e:
        logging.error("Failed to fetch or validate charging sessions", exc_info=True)
        raise e


def validate_against_schema(array_schema, response):
    """
    Validates the charge session response against the provided JSON schema.

    The function checks if the response contains valid data by validating it
    against the provided JSON schema. If the validation is successful, the resulting objects
    are returned. If the response does not contain the expected JSON data or if the data
    does not conform to the schema, an exception is raised.

    Parameters:
    - array_schema (dict): The JSON schema used for validation.
    - response (dict): The response containing the data to be validated.

    Returns:
    - list[dict[str, Any]]: The validated data.

    Raises:
    - Exception: If the response does not contain the expected JSON data.
    - ValidationError: If the data does not conform to the schema.

    Example:
    >>> validate_against_schema(array_schema, response)
    [{'mode': 'DISCONNECTED'}, {'mode': 'RETRIEVING_SOC'}]
    """
    if "json" not in response:
        raise Exception("No json field in response to array_schema request", response)
    response_object = response["json"]
    try:
        validate(response_object, array_schema)
    except Exception as e:
        logging.error(f"Schema validation failed: {e}")
        raise e
    return response_object


def get_ohme_minimum_schema():
    """
    Load and return the minimum schema required for Ohme data. This is an array of
    objects, where each object is a charge session.

    This function reads a JSON schema file, constructs an array schema using the loaded schema,
    and returns the resulting schema.

    Returns:
    - dict: The minimum schema required for Ohme data in the form of a Python dictionary.

    Raises:
    - Exception: If there is an error loading the schema file or constructing the array schema.

    Example:
    >>> get_ohme_minimum_schema()
    {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "array",
        "items": {...}  # Loaded object schema
    }
    """
    try:
        schema_file = os.path.join(SCRIPT_DIR, "ohme_minimum_schema.json")
        object_schema = load_file_as_json(schema_file)
        array_schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "array",
            "items": object_schema,
        }
    except Exception as e:
        logging.error("Error loading ohme_minimum_schema.json")
        raise e
    return array_schema


def load_file_as_json(schema_path):
    """
    Load a JSON file and return the data as a Python dictionary.

    Parameters:
    - file_path (str): The path to the JSON file to be read.

    Returns:
    - dict: The JSON data parsed into a Python dictionary.

    Raises:
    - FileNotFoundError: If the specified file does not exist.
    - json.JSONDecodeError: If the file content is not valid JSON.
    - Exception: For other errors encountered while reading the file.

    Example:
    >>> load_file_as_json("sample.json")
    {'key': 'value'}
    """
    try:
        with open(schema_path, "r") as f:
            return json.loads(f.read())
    except FileNotFoundError as e:
        logging.error(f"ohme_minimum_schema not found at {schema_path}")
        raise e
    except Exception as e:
        logging.error(f"Error reading ohme_minimum_schema  at {schema_path}")
        raise e


def is_charging_session_active(charge_sessions: list[dict[str:Any]]) -> bool:
    """
    Determine if any charging session is currently active.

    This function checks the 'mode' attribute of each session object in the input list.
    A session is considered active if its 'mode' is anything other than 'DISCONNECTED'.
    The function logs an error message if it encounters an unknown mode. Modes known so far
    are: DISCONNECTED, RETRIEVING_SOC, CALCULATING, SMART_CHARGE.

    Parameters:
    - charge_sessions (list[dict[str, Any]]): A list of dictionaries representing charging sessions,
      where each dictionary contains a 'mode' key indicating the status of the session.

    Returns:
    - bool: True if any session is active, False otherwise.

    Example:
    >>> is_charging_session_active([{"mode": "DISCONNECTED"}, {"mode": "RETRIEVING_SOC"}])
    True
    """
    known_modes = ["DISCONNECTED", "RETRIEVING_SOC", "CALCULATING", "SMART_CHARGE"]

    for obj in charge_sessions:
        mode = obj.get("mode")
        if mode not in known_modes:
            logging.error(
                f"Unknown mode {mode} found in chargeStatus: {obj}",
            )
    return any(obj.get("mode") != "DISCONNECTED" for obj in charge_sessions)


# allow debugging of this file
if __name__ == "__main__":  # pragma: no cover
    firebase_token = get_firebase_token().get("idToken")
    print(get_charging_sessions(firebase_token))
