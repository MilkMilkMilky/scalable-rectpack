from functools import partial
from typing import Any

from nicegui import ui

from scalable_rectpack import Item
from scalable_rectpack_visual.engine import default_example, get_engine


def to_int(value: Any):
    try:
        return int(value)
    except Exception:
        return None


class ControlPanel:
    def __init__(self):
        self.engine = get_engine("engine")
        self.create_control_panel()

    @property
    def is_running(self):
        return self.engine.state.value == "running"

    def create_control_panel(self):
        with ui.column().classes("w-1/3"):
            self.create_example_panel()
            self.create_boxes_panel()
            self.create_items_panel()
            self.algorithm_settings()
            self.create_packing_button()

    def create_example_panel(self):
        with ui.card().classes("w-full"):
            ui.label("Examples: ")
            with ui.card_section().props("horizontal"):
                for name, example in default_example.items():
                    ui.button(name, on_click=partial(self.load_example, example)).props(
                        "flat",
                    )

    def load_example(self, example: dict[str, Any]):
        self.engine.update(**example)
        self.refresh()

    def refresh(self):
        self.items_settings.refresh()
        self.boxes_settings.refresh()
        self.algorithm_settings.refresh()

    @ui.refreshable_method
    def create_boxes_panel(self):
        with ui.card().classes("w-full") as self.boxes_panel:
            ui.label("Settings for Boxes")
            with ui.card_section():
                self.boxes_settings()

    @ui.refreshable_method
    def boxes_settings(self):
        ui.number(
            "Box Width",
            value=self.engine.box_width,
            min=1,
            step=1,
            validation=partial(self.engine.validate_ge0_int, "Box Width"),
        ).bind_value(self.engine, "box_width", forward=to_int)

        ui.number(
            "Box Height",
            value=self.engine.box_height,
            min=1,
            step=1,
            validation=partial(self.engine.validate_ge0_int, "Box Height"),
        ).bind_value(self.engine, "box_height", forward=to_int)

    def create_items_panel(self):
        with ui.card().classes("w-full"):
            ui.label("Settings for Items")
            with ui.scroll_area().classes("w-full"):
                self.items_settings()
            with ui.row().classes("w-full"):
                ui.space()
                ui.button(icon="add", on_click=self.add_item).props("flat round")

    @ui.refreshable_method
    def items_settings(self):
        for item in self.engine.items:
            with ui.card(align_items="start").classes("w-full"):
                ui.label(f"ID: {item.id}")
                with ui.card_section().props("horizontal"):
                    width_input = ui.number(
                        "Width",
                        value=item.width,
                        min=1,
                        step=1,
                        validation=partial(self.engine.validate_ge0_int, "Width"),
                    )
                    width_input.bind_value(item, "width", forward=to_int)
                    height_input = ui.number(
                        "Height",
                        value=item.height,
                        min=1,
                        step=1,
                        validation=partial(self.engine.validate_ge0_int, "Height"),
                    )
                    height_input.bind_value(item, "height", forward=to_int)
                    width_min_input = ui.number(
                        "Width Min",
                        value=item.width_min,
                        min=1,
                        step=1,
                        validation=partial(self.engine.validate_ge0_int, "Width Min"),
                    )
                    width_min_input.bind_value(item, "width_min", forward=to_int)
                    height_min_input = ui.number(
                        "Height Min",
                        value=item.height_min,
                        min=1,
                        step=1,
                        validation=partial(self.engine.validate_ge0_int, "Height Min"),
                    )
                    height_min_input.bind_value(item, "height_min", forward=to_int)
                    ui.button(
                        icon="delete",
                        on_click=partial(self.delete_item, item.id),
                    ).props("flat round")

    @ui.refreshable_method
    def algorithm_settings(self):
        with ui.card().classes("w-full"):
            ui.label("Settings for Algorithm")
            with ui.card_section().props("horizontal"):
                time_limit_input = ui.number(
                    "Time Limit",
                    value=self.engine.time_limit,
                    min=1,
                    step=1,
                    validation=partial(self.engine.validate_ge0_int, "Time Limit"),
                )
                time_limit_input.bind_value(self.engine, "time_limit", forward=to_int)
                equal_shrink_input = ui.checkbox(
                    "Equal Shrink",
                    value=self.engine.equal_shrink,
                )
                equal_shrink_input.bind_value(self.engine, "equal_shrink")
                per_box_input = ui.checkbox("Per Box", value=self.engine.per_box)
                per_box_input.bind_value(self.engine, "per_box")

    def create_packing_button(self):
        with ui.card().classes("w-full"), ui.card_section().props("horizontal"):
            self.run_button = ui.button("Run Packing").props("flat")
            self.run_button.on(
                "click",
                self.run_packing,
                throttle=0.1,
                trailing_events=False,
            )
            self.run_button.bind_enabled_from(
                self,
                "is_running",
                backward=lambda x: not x,
            )

            ui.circular_progress(show_value=False).props(
                "indeterminate",
            ).bind_visibility_from(self, "is_running")

    async def run_packing(self):
        await self.engine.run_async()

    def add_item(self):
        item = Item(
            id=len(self.engine.items),
            width=1,
            height=1,
            width_min=1,
            height_min=1,
        )
        self.engine.append_item(item)
        self.items_settings.refresh()

    def delete_item(self, item_id: int):
        self.engine.delete_item(item_id)
        self.items_settings.refresh()
