from collections.abc import Callable
from itertools import count
from typing import Any, Generic, TypeVar

_T = TypeVar("_T")


class Observable(Generic[_T]):
    def __init__(self, value: _T):
        self._value = value
        self.listeners = {}
        self.listener_id = count()

    def on_change(self, listener: Callable[[Any], None], id: str | int | None = None) -> int | str:
        if id is None:
            id = next(self.listener_id)
        self.listeners[id] = listener
        return id

    def cancel_on_change(self, id: int | str):
        self.listeners.pop(id)

    @property
    def value(self) -> _T:
        return self._value

    @value.setter
    def value(self, value: _T):
        self._value = value
        try:
            for listener in self.listeners.values():
                listener(value)
        except Exception:  # noqa: S110
            pass
