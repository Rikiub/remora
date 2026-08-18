from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator, AsyncIterable
from contextlib import asynccontextmanager
from typing import Generic, TypeVar

import anyio
from anyio import AsyncContextManagerMixin
from anyio.streams.memory import MemoryObjectSendStream

_DEFAULT_BUFFER_SIZE = 25
_T = TypeVar("_T")


class AsyncEventStreamer(AsyncContextManagerMixin, ABC, Generic[_T]):
    """
    Base class that safely manages AnyIO background tasks, event streams,
    and cancellation propagation natively using AnyIO's Context Manager Mixin.
    """

    def __init__(self, buffer_size: int | None = None):
        self._buffer_size = _DEFAULT_BUFFER_SIZE if buffer_size is None else buffer_size
        self._send_stream: MemoryObjectSendStream[_T] | None = None

    @asynccontextmanager
    async def __asynccontextmanager__(self) -> AsyncGenerator[AsyncIterable[_T], None]:
        """AnyIO's internal mixin hook. This runs the background process and yields the receive stream safely."""
        if self._send_stream:
            raise RuntimeError(f"{self.__class__.__name__} can only be started once.")

        send_stream, receive_stream = anyio.create_memory_object_stream[_T](
            self._buffer_size
        )
        self._send_stream = send_stream

        try:
            async with receive_stream, anyio.create_task_group() as tg:
                tg.start_soon(self._producer_wrapper)
                yield receive_stream
        except BaseExceptionGroup as eg:
            # Unwrap exception group if is only one
            if len(eg.exceptions) == 1:
                raise eg.exceptions[0] from None

            # Else return the whole exception group
            raise

    async def _producer_wrapper(self) -> None:
        if not self._send_stream:
            return

        async with self._send_stream:
            try:
                await self._run_pipeline()
            finally:
                with anyio.CancelScope(shield=True):
                    await self._on_exit()

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
        """Safely pushes an event to the stream without blocking."""
        if not self._send_stream:
            return
        try:
            self._send_stream.send_nowait(event)
        except (anyio.ClosedResourceError, anyio.WouldBlock):
            pass

    async def _on_exit(self) -> None:
        """Subclasses CAN override this to handle cleanup tasks."""
