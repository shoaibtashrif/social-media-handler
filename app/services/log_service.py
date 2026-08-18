import logging
import asyncio
from typing import AsyncGenerator

class SSELogHandler(logging.Handler):
    """
    Custom logging handler that puts formatted log strings into an asyncio queue.
    """
    def __init__(self):
        super().__init__()
        self.queues = []

    def emit(self, record):
        try:
            msg = self.format(record)
            # Push to all connected client queues
            for q in self.queues:
                try:
                    q.put_nowait(msg)
                except asyncio.QueueFull:
                    pass
        except Exception:
            self.handleError(record)

    def subscribe(self) -> asyncio.Queue:
        q = asyncio.Queue(maxsize=200)
        self.queues.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue):
        if q in self.queues:
            self.queues.remove(q)


sse_handler = SSELogHandler()
formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s', datefmt='%H:%M:%S')
sse_handler.setFormatter(formatter)
sse_handler.setLevel(logging.INFO)

async def log_streamer() -> AsyncGenerator[str, None]:
    """
    Yields Server-Sent Events for each new log message.
    """
    q = sse_handler.subscribe()
    try:
        while True:
            # Wait for a new log message
            msg = await q.get()
            # SSE format: data: <message>\n\n
            yield f"data: {msg}\n\n"
    except asyncio.CancelledError:
        pass
    finally:
        sse_handler.unsubscribe(q)
