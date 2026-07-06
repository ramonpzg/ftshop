"""fal.ai queue API client. No business logic here.

Auth is the FAL_KEY environment variable, sent as `Authorization: Key`.
Requests go through the queue endpoints (submit, poll, fetch) and the
status/response URLs returned by the submit call are used verbatim, as
the fal docs recommend for nested model ids.
"""

import os
import time

import httpx


def _queue_base() -> str:
    # Overridable for tests and proxies.
    return os.environ.get("FAL_QUEUE_BASE", "https://queue.fal.run").rstrip("/")


class FalNotConfiguredError(RuntimeError):
    pass


class FalRequestError(RuntimeError):
    pass


def is_fal_configured() -> bool:
    return bool(os.environ.get("FAL_KEY"))


def _headers() -> dict[str, str]:
    key = os.environ.get("FAL_KEY", "")
    if not key:
        raise FalNotConfiguredError("FAL_KEY is not set")
    return {"Authorization": f"Key {key}"}


def run_model(model_id: str, payload: dict, *, timeout: float = 600.0) -> dict:
    """Submit, poll until COMPLETED, return the result JSON."""
    headers = _headers()
    with httpx.Client(timeout=60.0) as client:
        submit = client.post(f"{_queue_base()}/{model_id}", headers=headers, json=payload)
        if submit.status_code not in (200, 201, 202):
            raise FalRequestError(f"fal submit failed {submit.status_code}: {submit.text[:300]}")
        submitted = submit.json()
        status_url = submitted.get("status_url")
        response_url = submitted.get("response_url")
        if not status_url or not response_url:
            raise FalRequestError(f"fal submit response missing queue urls: {str(submitted)[:200]}")

        deadline = time.monotonic() + timeout
        while True:
            status = client.get(status_url, headers=headers)
            if status.status_code != 200:
                raise FalRequestError(
                    f"fal status failed {status.status_code}: {status.text[:300]}"
                )
            state = status.json().get("status")
            if state == "COMPLETED":
                break
            if state not in ("IN_QUEUE", "IN_PROGRESS"):
                raise FalRequestError(f"fal job ended in state {state}")
            if time.monotonic() > deadline:
                raise FalRequestError(f"fal job timed out after {timeout:.0f}s")
            time.sleep(1.0)

        result = client.get(response_url, headers=headers)
        if result.status_code != 200:
            raise FalRequestError(f"fal result failed {result.status_code}: {result.text[:300]}")
        return result.json()


def download_file(url: str, *, timeout: float = 120.0) -> bytes:
    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        response = client.get(url)
        if response.status_code != 200:
            raise FalRequestError(f"download failed {response.status_code} for {url}")
        return response.content
