import pytest
from ohme.firebase import get_firebase_token


def test_get_firebase_token():
    # Ensure the function does not raise an exception and returns a str
    try:
        token = get_firebase_token()
        assert isinstance(token, str)
        assert len(token) > 0
    except Exception as e:
        pytest.fail(f"get_firebase_token() raised an exception: {e}")
