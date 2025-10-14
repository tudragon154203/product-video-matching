import asyncio
from typing import Callable, Optional

import httpx


class LoopAwareAsyncClient:
    """
    Manages the lifecycle of an httpx.AsyncClient so it is always bound to a
    valid event loop. If the originating loop is closed or a different loop is
    active, the client is rebuilt on demand.
    """

    def __init__(self, client_factory: Callable[[], httpx.AsyncClient], logger) -> None:
        self._client_factory = client_factory
        self._logger = logger
        self._client: Optional[httpx.AsyncClient] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def _get_current_loop(self) -> Optional[asyncio.AbstractEventLoop]:
        try:
            return asyncio.get_running_loop()
        except RuntimeError:
            return None

    def _release_client(self) -> None:
        """Dispose of the cached client synchronously when possible."""
        if self._client is None:
            return

        client = self._client
        loop = self._loop
        self._client = None
        self._loop = None

        if getattr(client, "is_closed", False):
            return

        if loop and not loop.is_closed():
            try:
                loop.call_soon_threadsafe(lambda: asyncio.create_task(client.aclose()))
                return
            except RuntimeError:
                # Fall through to best effort close when loop scheduling fails.
                pass

        try:
            client.close()
        except RuntimeError:
            self._logger.debug(
                "Loop-aware client could not close cleanly because the loop is inactive.",
                exc_info=True,
            )
        except Exception:
            self._logger.debug(
                "Unexpected error while closing loop-aware AsyncClient.", exc_info=True
            )

    def get_client(self) -> httpx.AsyncClient:
        """Return an AsyncClient bound to the current event loop."""
        current_loop = self._get_current_loop()

        if self._client is not None:
            if getattr(self._client, "is_closed", False):
                self._release_client()
            elif self._loop is not None:
                loop_closed = self._loop.is_closed()
                loop_changed = current_loop is not None and self._loop is not current_loop
                if loop_closed or loop_changed:
                    self._logger.debug(
                        "Recreating loop-aware AsyncClient (loop_closed=%s loop_changed=%s).",
                        loop_closed,
                        loop_changed,
                    )
                    self._release_client()
            elif current_loop is not None:
                # Previously created without loop context; recreate to bind correctly.
                self._release_client()

        if self._client is None:
            self._client = self._client_factory()
            self._loop = current_loop

        return self._client

    async def close(self) -> None:
        """Close the managed AsyncClient on the appropriate loop."""
        if self._client is None:
            return

        client = self._client
        loop = self._loop
        self._client = None
        self._loop = None

        if getattr(client, "is_closed", False):
            return

        current_loop = self._get_current_loop()
        if loop and current_loop is not loop and not loop.is_closed():
            try:
                future = asyncio.run_coroutine_threadsafe(client.aclose(), loop)
                await asyncio.wrap_future(future)
                return
            except Exception:
                self._logger.debug(
                    "Failed to close AsyncClient on originating loop; falling back.",
                    exc_info=True,
                )

        await client.aclose()
