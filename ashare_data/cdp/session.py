"""CDP page session helpers."""

from __future__ import annotations

import json
import time
from typing import TYPE_CHECKING, Any

from ashare_data.cdp.errors import CdpEvalError, CdpFetchError, CdpNavigationError

if TYPE_CHECKING:
    from ashare_data.cdp.client import CdpClient


class CdpPageSession:
    """Small reusable page session wrapper."""

    def __init__(self, *, client: "CdpClient", target_id: str, page_url: str, timeout: float) -> None:
        self.client = client
        self.target_id = target_id
        self.page_url = page_url
        self.timeout = timeout

    def navigate(self, url: str) -> None:
        """Navigate the current page."""
        expression = f"location.href = {json.dumps(url)}"
        try:
            self.client.run_eval(self.target_id, expression)
        except Exception as exc:
            raise CdpNavigationError(str(exc)) from exc
        self.page_url = url
        time.sleep(1.0)

    def wait_for_network_idle(self, seconds: float = 1.0) -> None:
        """Wait briefly for page work to settle."""
        time.sleep(seconds)

    def evaluate(self, expression: str) -> Any:
        """Evaluate JavaScript and parse JSON-stringified results when possible."""
        try:
            raw = self.client.run_eval(self.target_id, expression)
        except Exception as exc:
            raise CdpEvalError(str(exc)) from exc
        return self._decode_output(raw)

    def fetch_text(self, url: str, headers: dict[str, str] | None = None) -> str:
        """Fetch text inside the page context."""
        expression = self._build_fetch_expression(url=url, headers=headers, parse_json=False)
        result = self.evaluate(expression)
        if not isinstance(result, dict) or result.get("ok") is not True:
            raise CdpFetchError(str(result))
        text = result.get("text")
        if not isinstance(text, str):
            raise CdpFetchError("CDP fetch_text did not return text")
        return text

    def fetch_json(self, url: str, headers: dict[str, str] | None = None) -> dict[str, Any]:
        """Fetch JSON inside the page context."""
        expression = self._build_fetch_expression(url=url, headers=headers, parse_json=True)
        result = self.evaluate(expression)
        if not isinstance(result, dict) or result.get("ok") is not True:
            raise CdpFetchError(str(result))
        payload = result.get("data")
        if not isinstance(payload, dict):
            raise CdpFetchError("CDP fetch_json did not return JSON object")
        return payload

    def close(self) -> None:
        """Close the page target."""
        self.client.close_page(self.target_id)

    def _build_fetch_expression(
        self,
        *,
        url: str,
        headers: dict[str, str] | None,
        parse_json: bool,
    ) -> str:
        success_field = '"data"' if parse_json else '"text"'
        js_headers = json.dumps(headers or {}, ensure_ascii=False)
        if parse_json:
            response_reader = "r.json()"
            payload_expr = f"const payload = await {response_reader};"
        else:
            # Use ArrayBuffer + TextDecoder to respect the actual charset.
            # Falls back to 'gbk' when the server omits a charset declaration
            # (common for Chinese sites like THS that serve GBK HTML without
            # an explicit Content-Type charset).
            payload_expr = (
                "const buf = await r.arrayBuffer();"
                "const ct = r.headers.get('content-type') || '';"
                "const m = ct.match(/charset=([^\\s;]+)/i);"
                "const charset = m ? m[1] : 'gbk';"
                "const payload = new TextDecoder(charset).decode(buf);"
            )
        return (
            "(async () => {"
            f"const r = await fetch({json.dumps(url)}, {{credentials: 'include', headers: {js_headers}}});"
            f"{payload_expr}"
            f"return JSON.stringify({{ok: r.ok, status: r.status, {success_field}: payload}});"
            "})()"
        )

    @staticmethod
    def _decode_output(raw: str) -> Any:
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return raw
