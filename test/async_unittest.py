import asyncio
from unittest import case, loader, mock, result, runner, signals, suite, util
from unittest import *  # import everything that IS defined in __all__


def AsyncMock(mock_func, *args, **kwargs):
    '''
    Returns an asynchronous function coroutine. The provided "mock_func"
    argument is the function to be called when the coroutine is run.
    All args and kwargs are passed to the mock when it is called.
    '''
    async def mock_coroutine(*args, **kwargs):
        return mock_func(*args, **kwargs)

    mock_coroutine.mock = mock_func
    return mock_coroutine


def AsyncMagicMock(*args, **kwargs):
    '''
    Returns an asynchronous function coroutine. The returned coroutine
    contains a "mock" attribute, which is the MagicMock object to be called
    when the coroutine is run. All args and kwargs are passed to the mock.
    '''
    return AsyncMock(mock.MagicMock(*args, **kwargs), *args, **kwargs)


class AsyncTestCase(TestCase):
    _loop = None

    @property
    def loop(self):
        if self._loop is None:
            self._loop = asyncio.get_event_loop()
        return self._loop

    @loop.setter
    def loop(self, new_val):
        self._loop = new_val

    def run_async(self, coroutine):
        return self.loop.run_until_complete(coroutine)
