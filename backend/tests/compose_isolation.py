from __future__ import annotations

import json
import sys
from http.cookiejar import CookieJar
from urllib.error import HTTPError
from urllib.request import HTTPCookieProcessor, Request, build_opener

BASE_URL = "http://localhost:8080"
PASSWORD = "integration test password"


def api_client(environment: str):
    jar = CookieJar()
    return build_opener(HTTPCookieProcessor(jar)), jar, f"{BASE_URL}/api/{environment}/v1"


def call(opener, url: str, method: str = "GET", payload=None, csrf: str | None = None):
    headers = {}
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode()
    if csrf:
        headers["X-CSRF-Token"] = csrf
    request = Request(url, data=data, headers=headers, method=method)
    with opener.open(request) as response:
        body = response.read()
        return response.status, json.loads(body) if body else None


def csrf_from(jar: CookieJar, name: str) -> str:
    for cookie in jar:
        if cookie.name == name:
            return cookie.value
    raise AssertionError(f"missing CSRF cookie {name}")


def setup_payload(username: str):
    return {
        "username": username,
        "password": PASSWORD,
        "settings": {
            "language": "sv",
            "region": "SE",
            "base_currency": "SEK",
            "timezone": "Europe/Stockholm",
            "date_format": "YYYY-MM-DD",
            "number_format": "space-comma",
            "week_start": "monday",
        },
    }


def main() -> int:
    prod, prod_jar, prod_base = api_client("production")
    test, test_jar, test_base = api_client("test")

    _, prod_status = call(prod, f"{prod_base}/setup/status")
    _, test_status = call(test, f"{test_base}/setup/status")
    assert prod_status["data_plane_id"] != test_status["data_plane_id"]

    if prod_status["setup_required"]:
        call(prod, f"{prod_base}/setup", "POST", setup_payload("prod-owner"))
    else:
        call(
            prod,
            f"{prod_base}/auth/login",
            "POST",
            {"username": "prod-owner", "password": PASSWORD},
        )
    if test_status["setup_required"]:
        call(test, f"{test_base}/setup", "POST", setup_payload("test-owner"))
    else:
        call(
            test,
            f"{test_base}/auth/login",
            "POST",
            {"username": "test-owner", "password": PASSWORD},
        )

    prod_csrf = csrf_from(prod_jar, "cost_review_production_csrf")
    test_csrf = csrf_from(test_jar, "cost_review_test_csrf")
    call(prod, f"{prod_base}/settings", "PATCH", {"language": "en", "region": "GB"}, prod_csrf)
    _, prod_before = call(prod, f"{prod_base}/auth/session")
    _, prod_environment_before = call(prod, f"{prod_base}/environment")

    _, reset = call(
        test,
        f"{test_base}/test/reset",
        "POST",
        {"confirmation": "DELETE ALL TEST DATA"},
        test_csrf,
    )
    assert reset["reset_generation"] >= 1

    _, prod_after = call(prod, f"{prod_base}/auth/session")
    _, prod_environment_after = call(prod, f"{prod_base}/environment")
    assert prod_after["settings"] == prod_before["settings"]
    assert prod_environment_after == prod_environment_before
    assert prod_environment_after["reset_generation"] == 0

    try:
        call(
            prod,
            f"{prod_base}/test/reset",
            "POST",
            {"confirmation": "DELETE ALL TEST DATA"},
            prod_csrf,
        )
    except HTTPError as error:
        assert error.code == 404
    else:
        raise AssertionError("Production unexpectedly exposed the test reset route")

    print("Production/Test HTTP isolation verified.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
