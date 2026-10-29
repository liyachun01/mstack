"""Synthetic CodeGraph verification fixture; not application code."""


def fixture_normalize_payload(value):
    return value.strip().lower()


def fixture_read_payload(value):
    return fixture_normalize_payload(value)


def fixture_handle_request(value):
    return fixture_read_payload(value)
