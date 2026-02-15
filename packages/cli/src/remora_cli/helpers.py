from functools import partial, wraps


def make_async(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        import anyio

        return anyio.run(partial(func, *args, **kwargs))

    return wrapper
