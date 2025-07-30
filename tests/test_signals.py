import pytest
import asyncio

from webcam_ip.utils.signals import SignalHandler, GracefulShutdown, ShutdownReason


def test_sync_cleanup_handler_called():
    called = []

    def cleanup1():
        called.append("sync1")

    handler = SignalHandler(timeout=1.0)
    handler.add_cleanup_handler(cleanup1, async_handler=False)

    # Trigger shutdown and run sync cleanup
    handler.trigger_shutdown(ShutdownReason.MANUAL)
    handler.run_sync_cleanup()

    assert called == ["sync1"]


@pytest.mark.asyncio
async def test_async_cleanup_handler_called():
    called = []

    async def cleanup_async():
        await asyncio.sleep(0)
        called.append("async1")

    handler = SignalHandler(timeout=1.0)
    handler.add_cleanup_handler(cleanup_async, async_handler=True)

    handler.trigger_shutdown(ShutdownReason.MANUAL)
    await handler.run_async_cleanup()

    assert called == ["async1"]


@pytest.mark.asyncio
async def test_wait_for_shutdown_returns_context():
    handler = SignalHandler(timeout=1.0)
    reason = ShutdownReason.SIGNAL_SIGINT

    handler.trigger_shutdown(reason, signal_number=2)
    ctx = await handler.wait_for_shutdown()

    assert ctx.reason == reason
    assert ctx.signal_number == 2


def test_remove_sync_cleanup_handler():
    called = []

    def foo():
        called.append("foo")

    handler = SignalHandler(timeout=1.0)
    handler.add_cleanup_handler(foo, async_handler=False)
    handler.remove_cleanup_handler(foo)

    handler.trigger_shutdown(ShutdownReason.MANUAL)
    handler.run_sync_cleanup()

    assert called == []


def test_gracefulshutdown_context_manager_sync():
    called = []

    def cleanup():
        called.append("cleanup")

    with GracefulShutdown(timeout=1.0, setup_signals=False) as gs:
        gs.add_cleanup_handler(cleanup, async_handler=False)

    assert called == ["cleanup"]


@pytest.mark.asyncio
async def test_gracefulshutdown_context_manager_async():
    called = []

    async def cleanup_async():
        await asyncio.sleep(0)
        called.append("cleanup_async")

    gs = GracefulShutdown(timeout=1.0, setup_signals=False)
    async with gs as mgr:
        mgr.add_cleanup_handler(cleanup_async, async_handler=True)

    assert called == ["cleanup_async"]
