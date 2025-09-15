from typing import Any, Literal

from nicegui import ui
from ortools.sat.python import cp_model

from scalable_rectpack_visual.engine import get_engine
from scalable_rectpack_visual.mpl import visualize_packing


class ResultView:
    def __init__(self):
        self.engine = get_engine("engine")
        with ui.column().classes("w-1/2 h-full"):
            self.create_result_view()
            self.create_log_view()
        self.bind_engine_state()

    def bind_engine_state(self):
        self.engine.state.on_change(self.on_engine_state_change)

    def on_engine_state_change(self, state: Literal["idle", "running", "finished"]):
        if state == "finished":
            self.result_view.refresh()
            self.create_log_view.refresh()

    def create_result_view(self):
        with ui.card().classes("w-full"):
            ui.label("Result")
            with ui.card_section():
                self.result_view()

    @ui.refreshable_method
    def result_view(self):
        result = self.engine.packing_result
        if not result:
            return
        if not result.success:
            ui.notify("No solution found", type="negative")
            ui.label(result.message)
            return
        tabs = {}
        len_boxes = len(result.packing_results)
        with ui.tabs().classes("w-full") as tabs_component:
            for i in range(len_boxes):
                tabs[i] = ui.tab(f"Box {i}")
        with ui.tab_panels(tabs_component, value=tabs[0]).classes("w-full"):
            for i in range(len_boxes):
                with ui.tab_panel(tabs[i]), ui.matplotlib().figure as fig:
                    visualize_packing(
                        fig,
                        result.packing_results[i],
                        self.engine.box_width,
                        self.engine.box_height,
                    )

    def _status_to_str(self, status: Any) -> str:
        try:
            key = int(status)
        except Exception:
            key = status
        mapping = {
            int(cp_model.OPTIMAL): "OPTIMAL",
            int(cp_model.FEASIBLE): "FEASIBLE",
            int(cp_model.INFEASIBLE): "INFEASIBLE",
            int(cp_model.MODEL_INVALID): "MODEL_INVALID",
            int(cp_model.UNKNOWN): "UNKNOWN",
        }
        return mapping.get(key, str(status))

    @ui.refreshable_method
    def create_log_view(self):
        with ui.card().classes("w-full"):
            ui.label("Logs")
            with ui.card_section():
                result = self.engine.packing_result
                if not result:
                    ui.label("No logs yet. Run packing to see details.")
                    return

                with ui.column().classes("w-full gap-1"):
                    ui.label(f"Success: {result.success}")
                    ui.label(f"Outcome: {result.outcome.value}")
                    ui.label(f"Message: {result.message}")
                    ui.label(
                        f"Phase1 Status: {self._status_to_str(result.status_phase1)}; Time: {result.solve_time_phase1:.3f}s",
                    )
                    ui.label(
                        f"Boxes used: {result.num_boxes_used if result.num_boxes_used is not None else '-'}; Box size: {result.box_width}x{result.box_height}",
                    )
                    ui.label(
                        f"Settings -> equal_shrink: {self.engine.equal_shrink}, per_box: {self.engine.per_box}, time_limit: {self.engine.time_limit}s",
                    )

                with ui.expansion("Details").classes("w-full"):
                    for per in result.packing_results:
                        title = f"Box {per.box_id}" if per.box_id is not None else "Global Optimization"
                        with ui.expansion(title).classes("w-full"):
                            ui.label(
                                f"Status: {self._status_to_str(per.status)}; Outcome: {per.outcome.value}; Solve time: {per.solve_time:.3f}s; Total shrink: {per.total_shrink if per.total_shrink is not None else '-'}",
                            )
                            if per.message:
                                ui.label(per.message)
                            if per.packed_items is None:
                                ui.label("No items packed or no feasible solution.")
                            else:
                                ui.label(f"Items packed: {len(per.packed_items)}")
                                with ui.expansion("Items").classes("w-full"):
                                    for item in per.packed_items:
                                        ui.label(
                                            f"Item {item.id}: box {item.box_id}, pos ({item.x}, {item.y}), size {item.width}x{item.height}",
                                        )
