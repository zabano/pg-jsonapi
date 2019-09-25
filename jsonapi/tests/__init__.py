import asyncio
import uvloop
from functools import update_wrapper

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())


def coroutine(f):
    f = asyncio.coroutine(f)

    def wrapper(*args, **kwargs):
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(f(*args, **kwargs))

    return update_wrapper(wrapper, f)
