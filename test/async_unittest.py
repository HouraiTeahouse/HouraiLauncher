import asyncio
from inspect import iscoroutinefunction
from unittest import case, loader, mock, result, runner, signals, suite, util
from unittest import *  # import everything that IS defined in __all__


def async_mock(func):
    '''
    Returns an asynchronous function coroutine. The provided "func"
    argument is the function to be called when the coroutine is run.
    All args and kwargs are passed to func when it is called.
    '''
    async def mock_coroutine(*args, **kwargs):
        return func(*args, **kwargs)

    mock_coroutine.mock = func
    return mock_coroutine


def async_magic_mock(*args, **kwargs):
    '''
    Returns an asynchronous function coroutine. The returned coroutine
    contains a "mock" attribute, which is the MagicMock object to be called
    when the coroutine is run. All args and kwargs are passed to the mock.
    '''
    return async_mock(mock.MagicMock(*args, **kwargs))


def async_patch(target, new=mock.DEFAULT, *args, **kwargs):
    '''
    Patches 'target' object with 'new' coroutine. If new is not a coroutine,
    async_mock will be called with 'new' as the argument to replace 'new'.
    If 'new' is not provided(or mock.DEFAULT), async_magic_mock will be called
    and 'new' will be replaced with it.
    '''
    if new is mock.DEFAULT:
        new = async_magic_mock()
    elif not iscoroutinefunction(new):
        new = async_mock(new)
    return mock.patch(target, new, *args, **kwargs)


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

    def run_async(self, coroutine, *args, **kwargs):
        return self.loop.run_until_complete(coroutine(*args, **kwargs))
