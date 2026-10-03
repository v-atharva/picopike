"""A small shared pool for CPU-bound request work.

Heavy inputs queue here instead of each taking its own thread. Threads compete for the
interpreter lock, so many busy ones starve the event loop; one worker keeps the loop's share.
Only concurrency is bounded: the pending queue is not. Admission control, queue limits and
overload responses belong to the serving layer.
"""

from __future__ import annotations

import asyncio
import functools
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor

CPU_WORKERS = 1


@functools.cache
def cpu_pool() -> ThreadPoolExecutor:
    return ThreadPoolExecutor(max_workers=CPU_WORKERS, thread_name_prefix="picopike-cpu")


async def run_cpu[**P, T](func: Callable[P, T], *args: P.args, **kwargs: P.kwargs) -> T:
    """Run ``func`` in the shared pool without blocking the event loop."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(cpu_pool(), functools.partial(func, *args, **kwargs))
