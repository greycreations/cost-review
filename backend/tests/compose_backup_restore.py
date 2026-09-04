from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from http.cookiejar import CookieJar
from urllib.error import HTTPError, URLError
from urllib.request import HTTPCookieProcessor, Request, build_opener

BASE_URL = os.environ.get("COST_REVIEW_BASE_URL", "http://localhost:8080")
API_URL = f"{BASE_URL}/api/test/v1"
PASSWORD = "backup restore integration password"
ISOLATION_PASSWORD = "integration test password"
DOCKER = os.environ.get("DOCKER_COMMAND", "docker")
COMPOSE_PROJECT_NAME = os.environ.get("COMPOSE_PROJECT_NAME", "cost-review")


def call(opener, path: str, method: str = "GET", payload=None, csrf: str | None = None):
    headers = {}
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode()
    if csrf:
        headers["X-CSRF-Token"] = csrf
    request = Request(f"{API_URL}{path}", data=data, headers=headers, method=method)
    with opener.open(request) as response:
        body = response.read()
        return response.status, json.loads(body) if body else None


def client():
    jar = CookieJar()
    return build_opener(HTTPCookieProcessor(jar)), jar


def csrf_from(jar: CookieJar) -> str:
    for cookie in jar:
        if cookie.name == "cost_review_test_csrf":
            return cookie.value
    raise AssertionError("missing Test CSRF cookie")


def compose(*arguments: str) -> None:
    subprocess.run(
        [DOCKER, "compose", "-p", COMPOSE_PROJECT_NAME, *arguments],
        check=True,
        timeout=3600,
    )


def container_python(code: str) -> None:
    compose("run", "--rm", "--no-deps", "api-test", "python", "-c", code)


def wait_until_ready() -> None:
    for _ in range(60):
        try:
            opener, _ = client()
            call(opener, "/health")
            return
        except (HTTPError, URLError):
            time.sleep(1)
    raise AssertionError("Test API did not become ready after restore")


def setup_payload() -> dict[str, object]:
    return {
        "username": "restore-owner",
        "password": PASSWORD,
        "settings": {
            "language": "en",
            "region": "SE",
            "base_currency": "SEK",
            "timezone": "Europe/Stockholm",
            "date_format": "YYYY-MM-DD",
            "number_format": "space-comma",
            "week_start": "monday",
        },
    }


def main() -> int:
    opener, jar = client()
    _, status = call(opener, "/setup/status")
    if status["setup_required"]:
        username = "restore-owner"
        password = PASSWORD
        call(opener, "/setup", "POST", setup_payload())
    else:
        username = "test-owner"
        password = ISOLATION_PASSWORD
        call(
            opener,
            "/auth/login",
            "POST",
            {"username": username, "password": password},
        )
    csrf = csrf_from(jar)

    account_payload = {
        "account_type": "current",
        "opening_balance": "100.00",
        "opening_balance_date": "2026-09-01",
        "currency": "SEK",
    }
    call(
        opener,
        "/accounts",
        "POST",
        {**account_payload, "name": "Present in encrypted backup"},
        csrf,
    )
    container_python(
        "from pathlib import Path; "
        "p=Path('/app/storage/attachments/restore-proof.txt'); "
        "p.write_text('before backup', encoding='utf-8')"
    )
    _, backup = call(opener, "/backups", "POST", csrf=csrf)
    call(opener, f"/backups/{backup['filename']}/validate", "POST", csrf=csrf)

    call(
        opener,
        "/accounts",
        "POST",
        {**account_payload, "name": "Created after backup"},
        csrf,
    )
    container_python(
        "from pathlib import Path; "
        "p=Path('/app/storage/attachments/restore-proof.txt'); "
        "p.write_text('after backup', encoding='utf-8'); "
        "Path('/app/storage/attachments/late-file.txt').write_text('late', encoding='utf-8')"
    )

    compose("stop", "api-test", "backup-test")
    compose(
        "run",
        "--rm",
        "--no-deps",
        "api-test",
        "python",
        "-m",
        "app.backup_cli",
        "restore",
        backup["filename"],
        "--confirmation",
        "RESTORE DEMO/TEST",
    )
    compose("up", "--detach", "--wait", "api-test")
    wait_until_ready()

    try:
        call(opener, "/auth/session")
    except HTTPError as error:
        assert error.code == 401
    else:
        raise AssertionError("a restored session remained valid")

    restored, restored_jar = client()
    call(
        restored,
        "/auth/login",
        "POST",
        {"username": username, "password": password},
    )
    _, accounts = call(restored, "/accounts")
    names = {item["name"] for item in accounts["items"]}
    assert "Present in encrypted backup" in names
    assert "Created after backup" not in names
    assert csrf_from(restored_jar)
    container_python(
        "from pathlib import Path; "
        "p=Path('/app/storage/attachments/restore-proof.txt'); "
        "assert p.read_text(encoding='utf-8') == 'before backup'; "
        "assert not Path('/app/storage/attachments/late-file.txt').exists()"
    )
    print("Encrypted database, attachment, and session restore verified.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
