"""Cloudflare Browser Rendering helpers for JS/bot-protected pages."""

from __future__ import annotations

import logging
import random
import time
from typing import Any

import httpx

from mrf.core.config import settings
from mrf.scrapers.base import ScraperError

log = logging.getLogger("mrf.scrapers.cf_browser")

CF_API_BASE = "https://api.cloudflare.com/client/v4"
_CF_MIN_DELAY_SECONDS = 2.0
_CF_MAX_DELAY_SECONDS = 5.0


class CloudflareBrowserUnavailable(ScraperError):
    """Raised when Cloudflare Browser Rendering is not configured."""


def _is_configured() -> bool:
    return bool(settings.cf_account_id and settings.cf_api_token)


def _headers() -> dict[str, str]:
    if not _is_configured():
        raise CloudflareBrowserUnavailable(
            "Cloudflare Browser Rendering is not configured. "
            "Set CF_ACCOUNT_ID and CF_API_TOKEN."
        )
    return {
        "Authorization": f"Bearer {settings.cf_api_token}",
        "Content-Type": "application/json",
    }


def _content_url() -> str:
    return f"{CF_API_BASE}/accounts/{settings.cf_account_id}/browser-rendering/content"


def _extract_html(payload: Any) -> str | None:
    if isinstance(payload, str):
        return payload
    if isinstance(payload, dict):
        for key in ("html", "content", "body", "text", "result"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value
            nested = _extract_html(value)
            if nested:
                return nested
    if isinstance(payload, list):
        for item in payload:
            nested = _extract_html(item)
            if nested:
                return nested
    return None


def cf_fetch_html(url: str, *, timeout: float = 90.0, retries: int = 3) -> str | None:
    """Fetch rendered HTML through Cloudflare Browser Rendering /content.

    Returns None when Cloudflare credentials are not configured.
    Raises ScraperError on repeated API failures.
    """
    if not _is_configured():
        log.info("[cf-browser] CF credentials missing; falling back for %s", url)
        return None

    last_error: Exception | None = None
    with httpx.Client(timeout=httpx.Timeout(timeout, connect=15.0), follow_redirects=True) as client:
        for attempt in range(1, retries + 1):
            try:
                time.sleep(random.uniform(_CF_MIN_DELAY_SECONDS, _CF_MAX_DELAY_SECONDS))
                resp = client.post(
                    _content_url(),
                    headers=_headers(),
                    json={"url": url},
                )
                resp.raise_for_status()

                content_type = resp.headers.get("content-type", "").lower()
                if "text/html" in content_type:
                    html = resp.text
                else:
                    payload = resp.json()
                    if payload.get("success") is False:
                        errors = payload.get("errors") or []
                        raise ScraperError(f"Cloudflare content fetch failed for {url}: {errors}")
                    html = _extract_html(payload.get("result", payload))

                if html and html.strip():
                    return html
                raise ScraperError(f"Cloudflare returned empty HTML for {url}")
            except (httpx.HTTPError, ValueError, ScraperError) as exc:
                last_error = exc
                if attempt >= retries:
                    break
                backoff = min(20.0, attempt * 3.0)
                log.warning(
                    "[cf-browser] Fetch failed for %s (attempt %s/%s): %s — retrying in %.1fs",
                    url,
                    attempt,
                    retries,
                    exc,
                    backoff,
                )
                time.sleep(backoff)

    raise ScraperError(f"Cloudflare fetch failed for {url}: {last_error}")
