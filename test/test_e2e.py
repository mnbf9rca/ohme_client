import os
import sys
import pytest

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))
from ohme.firebase import get_firebase_token  # noqa: E402


def test_get_firebase_token():
    # Ensure the function does not raise an exception and returns the correct data
    try:
        token = get_firebase_token()

        # Check the response has the following 3 fields only: idToken, expiresIn, refreshToken
        assert set(token.keys()) == {"idToken", "expiresIn", "refreshToken"}

        # Check idToken and refreshToken are strings longer than 1 char
        assert isinstance(token["idToken"], str) and len(token["idToken"]) > 1
        assert isinstance(token["refreshToken"], str) and len(token["refreshToken"]) > 1

        # Check expiresIn is a string parseable to an int
        assert isinstance(token["expiresIn"], str)
        int(token["expiresIn"])

    except Exception as e:
        pytest.fail(f"get_firebase_token() raised an exception: {e}")
