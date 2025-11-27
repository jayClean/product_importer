"""Helper functions for chunking iterables."""
from collections.abc import Iterable


def chunked(iterable: Iterable, size: int):
    """Yield successive chunks to optimize DB writes and Celery progress."""
    raise NotImplementedError
