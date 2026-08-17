from abc import ABC, abstractmethod
from collections.abc import AsyncIterable, AsyncIterator
from contextlib import asynccontextmanager
from typing import Generic, TypeVar

import anyio
from anyio.streams.memory import MemoryObjectSendStream

_T = TypeVar("_T")


class AsyncEventStreamer(ABC, Generic[_T]):
    """
    Base class that safely manages AnyIO background tasks, event streams,
    and cancellation propagation.
    """

    def __init__(self, buffer_size: int | None = None):
        self._buffer_size = buffer_size or 30
        self._send_stream: MemoryObjectSendStream[_T] | None = None

    @asynccontextmanager
    async def start(self) -> AsyncIterator[AsyncIterable[_T]]:
        """Entry point to start the background process and yield events."""
        if self._send_stream:
            raise RuntimeError(f"{self.__class__.__name__} can only be started once.")

        send_stream, receive_stream = anyio.create_memory_object_stream[_T](
            self._buffer_size
        )
        self._send_stream = send_stream

        async def _producer_wrapper():
            async with send_stream:
                try:
                    await self._run_pipeline()
                except anyio.get_cancelled_exc_class():
                    with anyio.CancelScope(shield=True):
                        await self._on_cancelled()
                    raise
                finally:
                    with anyio.CancelScope(shield=True):
                        await self._on_finally()

        async with receive_stream, anyio.create_task_group() as tg:
            tg.start_soon(_producer_wrapper)

            try:
                yield receive_stream
            finally:
                tg.cancel_scope.cancel()

    @abstractmethod
    async def _run_pipeline(self) -> None:
        """Subclasses MUST implement their main logic here."""
        raise NotImplementedError

    async def _emit(self, event: _T) -> None:
        """Safely pushes an event to the stream."""
        if not self._send_stream:
            return
        try:
            await self._send_stream.send(event)
        except anyio.ClosedResourceError:
            pass  # Stream closed early, safe to ignore

    def _emit_nowait(self, event: _T) -> None:
        """Safely pushes an event to the stream."""
        if not self._send_stream:
            return
        self._send_stream.send_nowait(event)

    async def _on_finally(self) -> None:
        """Subclasses CAN override this to handle cleanup tasks."""

    async def _on_cancelled(self) -> None:
        """Subclasses CAN override this to emit specific cancellation events."""
