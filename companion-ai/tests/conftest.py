from __future__ import annotations

import asyncio
import inspect


def pytest_configure(config):
    # Custom marker used by test_tool_collection to mark coroutines that
    # should be run via asyncio.run (we don't depend on pytest-asyncio).
    config.addinivalue_line(
        "markers",
        "asyncio_compatible: coroutine test that the conftest will drive with asyncio.run",
    )


def pytest_pyfunc_call(pyfuncitem):
    test_func = pyfuncitem.obj
    if not inspect.iscoroutinefunction(test_func):
        return None

    kwargs = {
        name: pyfuncitem.funcargs[name]
        for name in pyfuncitem._fixtureinfo.argnames
    }
    asyncio.run(test_func(**kwargs))
    return True
