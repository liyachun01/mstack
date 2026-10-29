"""Synthetic public fixture; no application data or credentials."""


def fixture_normalize_payload(payload: str) -> str:
    return payload.strip().lower()


def fixture_read_payload(payload: str) -> dict:
    return {"value": fixture_normalize_payload(payload)}


def fixture_handle_request(payload: str) -> dict:
    return fixture_read_payload(payload)
