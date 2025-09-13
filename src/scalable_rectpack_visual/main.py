from nicegui import ui

from scalable_rectpack_visual.components.control import ControlPanel
from scalable_rectpack_visual.components.result_view import ResultView


@ui.page("/")
async def index():
    with ui.row():
        ControlPanel()
        ResultView()


ui.run(title="Scalable Rectpack Visual")
