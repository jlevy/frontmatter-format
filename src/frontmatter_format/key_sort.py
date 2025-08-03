from collections.abc import Callable
from typing import Any, TypeVar

T = TypeVar("T")

KeySort = Callable[[T], Any]


def custom_key_sort(priority_keys: list[T]) -> KeySort[T]:
    """
    Custom sort function that prioritizes the specific keys in a certain order, followed
    by all the other keys in natural order.
    """

    def sort_func(key: T) -> tuple[float, T]:
        try:
            i = priority_keys.index(key)
            return (float(i), key)
        except ValueError:
            return (float("inf"), key)

    return sort_func
