from typing import Any
import logging
import os
import jsonschema
import json


def validate_against_schema(
    array_schema: dict[str, Any], object_to_validate: dict[str, Any]
) -> bool:
    """
    Validates the input object against the provided JSON schema.

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

    try:
        jsonschema.validate(object_to_validate, array_schema)
    except Exception as e:
        logging.error(f"Schema validation failed: {e}")
        raise e
    return object_to_validate


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
        this_dir = os.path.dirname(os.path.abspath(__file__))
        schema_file = os.path.join(this_dir, "ohme_minimum_schema.json")
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
