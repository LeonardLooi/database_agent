from __future__ import annotations

import os
import re

import httpx
import structlog

logger = structlog.get_logger()

_ENV_VAR_RE = re.compile(r"\$\{([A-Z_][A-Z0-9_]*)\}")

_DEFAULT_TIMEOUT = 30.0


def _resolve_env_vars(headers: dict) -> dict:
    """Replace ${VAR_NAME} references in header values with env var values."""
    return {
        k: _ENV_VAR_RE.sub(lambda m: os.environ.get(m.group(1), m.group(0)), str(v))
        for k, v in headers.items()
    }


class RestConnector:
    """Async HTTP connector for REST API intents.

    POSTs the user prompt as {"prompt": "<text>"} to the configured URL.
    Not a subclass of BaseConnector — REST responses are not DataFrames.
    """

    def __init__(
        self,
        url: str,
        method: str = "POST",
        headers: dict | None = None,
    ) -> None:
        self._url = url
        self._method = method.upper()
        self._headers = _resolve_env_vars(headers or {})

    async def call(self, prompt: str) -> dict:
        """Send the prompt to the REST endpoint and return the parsed response.

        Returns:
            {"data": <parsed JSON or raw text>, "status": <HTTP status code>}

        Raises:
            httpx.HTTPStatusError: on 4xx/5xx responses
            httpx.RequestError: on connection/timeout failures
        """
        body = {"prompt": prompt}
        async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT) as client:
            if self._method in ("POST", "PUT", "PATCH"):
                response = await client.request(
                    self._method,
                    self._url,
                    json=body,
                    headers=self._headers,
                )
            else:
                response = await client.request(
                    self._method,
                    self._url,
                    params={"prompt": prompt},
                    headers=self._headers,
                )
            response.raise_for_status()
            logger.info("rest_connector_done", url=self._url, status=response.status_code)
            try:
                return {"data": response.json(), "status": response.status_code}
            except Exception:
                return {"data": response.text, "status": response.status_code}
