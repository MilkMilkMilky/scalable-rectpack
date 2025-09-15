from nicegui import ui

from scalable_rectpack_visual.components.control import ControlPanel
from scalable_rectpack_visual.components.result_view import ResultView


@ui.page("/")
async def index():
    with ui.row().classes("w-full h-full"):
        ControlPanel()
        ResultView()

def main():
    ui.run(title="Scalable Rectpack Visual", reload=False)


def run():
    ui.run(title="Scalable Rectpack Visual")


if __name__ in ["__main__", "__mp_main__"]:
    run()
