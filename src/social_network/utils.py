from itertools import accumulate, repeat, islice
from typing import Callable, Iterable, TypeVar

T = TypeVar("T")


def iterate(f: Callable[[T], T], x: Iterable[T]) -> Iterable[T]:
    """return (x, f(x), f(f(x)), ...)"""
    return accumulate(repeat(x), lambda fx, _: f(fx))


def take_nth(n: int, x: Iterable[T]) -> T:
    """return list(x)[n]"""
    return next(islice(x, n, n + 1))
