from __future__ import annotations

import json
import urllib.request
from collections.abc import Callable


Transport = Callable[[str, dict[str, str], dict[str, object], int], dict[str, object]]


def _default_transport(url: str, headers: dict[str, str], payload: dict[str, object], timeout: int) -> dict[str, object]:
    request = urllib.request.Request(
        url=url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


class MiniMaxProvider:
    def __init__(self, api_key: str, api_url: str = "https://api.minimaxi.com/v1/text/chatcompletion_v2", timeout: int = 30, transport: Transport | None = None) -> None:
        self.api_key = api_key
        self.api_url = api_url
        self.timeout = timeout
        self.transport = transport or _default_transport

    def complete(self, system_prompt: str, user_prompt: str, model: str | None = None) -> str:
        payload = {
            "model": model or "MiniMax-M2.5",
            "messages": [
                {"role": "system", "name": "System", "content": system_prompt},
                {"role": "user", "name": "User", "content": user_prompt},
            ],
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        response = self.transport(self.api_url, headers, payload, self.timeout)
        try:
            return str(response["choices"][0]["message"]["content"]).strip()
        except Exception as exc:  # pragma: no cover
            raise ValueError(f"Invalid MiniMax response: {response}") from exc
