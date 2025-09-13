from nicegui import binding

from scalable_rectpack_visual.algorithm import RectPacker


@binding.bindable_dataclass
class RectPackerEngine(RectPacker): ...


engines: dict[str, RectPackerEngine] = {}


def get_engine(session_id: str) -> RectPackerEngine:
    if session_id not in engines:
        engines[session_id] = RectPackerEngine()
    return engines[session_id]
