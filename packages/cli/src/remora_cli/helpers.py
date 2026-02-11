from functools import wraps

import anyio


def make_async(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        from functools import partial

        return anyio.run(partial(func, *args, **kwargs))

    return wrapper
