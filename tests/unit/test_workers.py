import asyncio
import threading

from picopike.workers import CPU_WORKERS, cpu_pool, run_cpu


def test_run_cpu_runs_off_the_event_loop_thread() -> None:
    async def scenario() -> tuple[int, int]:
        return threading.get_ident(), await run_cpu(threading.get_ident)

    loop_thread, worker_thread = asyncio.run(scenario())
    assert loop_thread != worker_thread


def test_run_cpu_passes_arguments_through() -> None:
    assert asyncio.run(run_cpu(divmod, 17, 5)) == (3, 2)


def test_the_pool_is_shared_and_bounded() -> None:
    assert cpu_pool() is cpu_pool()
    assert cpu_pool()._max_workers == CPU_WORKERS
