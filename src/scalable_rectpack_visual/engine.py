from collections.abc import Callable
from typing import Literal

from nicegui import binding, ui
from nicegui.run import io_bound

from scalable_rectpack import Item
from scalable_rectpack_visual.algorithm import RectPacker
from scalable_rectpack_visual.utils import Observable


@binding.bindable_dataclass
class RectPackerEngine(RectPacker):
    def __post_init__(self):
        self.state: Observable[Literal["idle", "running", "finished", "error"]] = Observable("idle")
        self.error_message: str | None = None

    def run(self):
        self.state.value = "running"
        try:
            super().run()
        except Exception as e:
            self.state.value = "error"
            self.error_message = str(e)
            return
        self.state.value = "finished"

    async def run_async(self):
        await io_bound(self.run)
        if self.state.value == "error":
            ui.notify(f"Packing failed: {self.error_message}", type="negative")
        else:
            ui.notify("Packing finished", type="positive")

    def on_state_change(
        self,
        callback: Callable[[Literal["idle", "running", "finished", "error"]], None],
        id: str | int | None = None,
    ):
        return self.state.on_change(callback, id)

    def update(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


engines: dict[str, RectPackerEngine] = {}


def get_engine(session_id: str) -> RectPackerEngine:
    if session_id not in engines:
        engines[session_id] = RectPackerEngine()
    return engines[session_id]


_example_1 = {
    "items": [
        Item(1, 60, 60, 50, 50),
        Item(2, 55, 55, 45, 45),
        Item(3, 50, 50, 40, 40),
        Item(4, 65, 65, 55, 55),
        Item(5, 45, 45, 35, 35),
        Item(6, 50, 50, 40, 40),
        Item(7, 55, 55, 45, 45),
        Item(8, 60, 60, 50, 50),
        Item(9, 50, 50, 40, 40),
        Item(10, 45, 45, 35, 35),
        Item(11, 70, 40, 60, 30),
        Item(12, 60, 50, 50, 40),
    ],
    "box_width": 200,
    "box_height": 150,
}

_example_2 = {
    "items": [
        Item(1, 100, 80, 90, 20),
        Item(2, 90, 70, 80, 60),
        Item(3, 50, 50, 40, 40),
        Item(4, 65, 65, 55, 55),
        Item(5, 45, 45, 35, 35),
        Item(6, 50, 50, 40, 40),
        Item(7, 54, 55, 46, 42),
        Item(8, 60, 60, 50, 50),
        Item(9, 30, 30, 30, 30),
        Item(10, 15, 15, 10, 10),
    ],
    "box_width": 100,
    "box_height": 80,
}


default_example = {
    "Example 1": _example_1,
    "Example 2": _example_2,
}
