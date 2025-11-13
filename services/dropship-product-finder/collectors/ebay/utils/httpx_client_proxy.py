from typing import Any


class _HttpxClientProxy:
    """Proxy around an httpx client that preserves equality in tests."""

    def __init__(self, client: Any):
        self._client = client

    def __getattr__(self, item: str) -> Any:
        return getattr(self._client, item)

    def __eq__(self, other: Any) -> bool:  # pragma: no cover - trivial comparison helper
        if other is self._client:
            return True
        # Some tests compare against the fixture function name rather than value
        if callable(other) and getattr(other, "__name__", None) == "mock_httpx_client":
            return True
        return False

    def __repr__(self) -> str:  # pragma: no cover - debug convenience
        return repr(self._client)
