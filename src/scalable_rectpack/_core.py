"""Core module of scalable_rectpack library, providing core functions for 2D rectangular packing.

This module implements resizable 2D rectangular packing algorithms using OR-Tools CP-SAT solver
with two-phase optimization: first minimize box count, then optimize item shrinkage.
"""

import time
from dataclasses import dataclass
from enum import Enum

from ortools.sat.cp_model_pb2 import CpSolverStatus
from ortools.sat.python import cp_model


class PackingOutcome(Enum):
    """Represents the high-level outcome of a packing optimization attempt."""

    OPTIMAL = "Optimal solution found"
    FEASIBLE = "Feasible solution found (not proven optimal)"
    NO_SOLUTION_INFEASIBLE = "No feasible solution exists (model proven infeasible)"
    NO_SOLUTION_TIMEOUT = "No feasible solution found within time limit"
    NO_SOLUTION_UNKNOWN = "No feasible solution found (unknown reason)"


@dataclass
class PerBoxPackingResult:
    """Represents the packing result for a single box or a global optimization phase 2.

    Attributes
    ----------
    box_id : int | None
        The identifier of the box if `per_box=True`. None if this represents
        a global optimization result (i.e., `per_box=False`).
    packed_items : list[PackedItem] | None
        List of PackedItem objects that were packed in this box (or globally).
        None if no feasible solution was found for this specific phase 2.
    total_shrink : int | None
        The total shrink value for items in this box (or globally).
        None if no feasible solution was found.
    status : CpSolverStatus
        The final solver status for this specific (or global) phase 2 optimization.
    solve_time : float
        The time taken by the solver for this specific (or global) phase 2 optimization in seconds.
    outcome : PackingOutcome
        The high-level outcome for this specific (or global) phase 2 optimization.
    message : str | None
        An optional message providing more details about this phase 2 result.

    """

    box_id: int | None
    packed_items: list["PackedItem"] | None
    total_shrink: int | None
    status: CpSolverStatus
    solve_time: float
    outcome: PackingOutcome
    message: str | None = None


@dataclass
class PackingResult:
    """Encapsulates the comprehensive result of the scalable rectangular packing process.

    Attributes
    ----------
    success : bool
        True if a feasible packing solution was found for all items, False otherwise.
    message : str
        A detailed message describing the overall outcome of the packing process.
    num_boxes_used : int | None
        The minimum number of boxes determined in Phase 1. None if Phase 1 failed.
    status_phase1 : CpSolverStatus
        The final solver status for the Phase 1 (box minimization) optimization.
    solve_time_phase1 : float
        The time taken by the solver for Phase 1 in seconds.
    outcome : PackingOutcome
        The high-level overall outcome of the packing process.
    box_width : int
        The width of the boxes.
    box_height : int
        The height of the boxes.
    packing_results : list[PerBoxPackingResult]
        A list of PerBoxPackingResult objects.
        If `per_box=True`, this list contains one entry for each physical box.
        If `per_box=False`, this list contains a single entry representing
        the global shrink optimization for all items.

    """

    success: bool
    message: str
    num_boxes_used: int | None
    status_phase1: CpSolverStatus
    solve_time_phase1: float
    outcome: PackingOutcome
    box_width: int
    box_height: int
    packing_results: list[PerBoxPackingResult]


# ------------------- Data Classes -------------------


@dataclass
class Item:
    """Represents a rectangular item to pack.

    Attributes
    ----------
    id : int
        Item identifier
    width : int
        Original width of the item
    height : int
        Original height of the item
    width_min : int
        Minimum allowed width after shrink
    height_min : int
        Minimum allowed height after shrink

    """

    id: int
    width: int
    height: int
    width_min: int
    height_min: int


@dataclass
class PackedItem:
    """Represents an item after packing, including position and size.

    Attributes
    ----------
    id : int
        Item identifier
    x : int
        X-coordinate in the box
    y : int
        Y-coordinate in the box
    width : int
        Width of the packed item
    height : int
        Height of the packed item
    box_id : int
        Assigned box identifier

    """

    id: int
    x: int
    y: int
    width: int
    height: int
    box_id: int


@dataclass
class Box:
    """Represents a box for packing items.

    Attributes
    ----------
    id : int
        Box identifier
    width : int
        Box width
    height : int
        Box height

    """

    id: int
    width: int
    height: int


# ------------------- Utility Functions -------------------


def _create_model() -> cp_model.CpModel:
    """Create a new OR-Tools CP-SAT model."""
    return cp_model.CpModel()


def _add_item_variables(
    model: cp_model.CpModel,
    item: Item,
    max_boxes: int,
    box: Box,
    equal_shrink: bool = False,
) -> dict:
    """Add CP-SAT variables for a single item (position, size, box assignment)."""
    box_id = model.NewIntVar(0, max_boxes - 1, f"box_{item.id}")
    x = model.NewIntVar(0, box.width, f"x_{item.id}")
    y = model.NewIntVar(0, box.height, f"y_{item.id}")

    if equal_shrink:
        max_shrink = min(item.width - item.width_min, item.height - item.height_min)
        shrink = model.NewIntVar(0, max_shrink, f"shrink_{item.id}")
        w = model.NewIntVar(item.width_min, item.width, f"w_{item.id}")
        h = model.NewIntVar(item.height_min, item.height, f"h_{item.id}")
        model.Add(w == item.width - shrink)
        model.Add(h == item.height - shrink)
    else:
        w = model.NewIntVar(item.width_min, item.width, f"w_{item.id}")
        h = model.NewIntVar(item.height_min, item.height, f"h_{item.id}")

    # Ensure item is within box boundaries
    model.Add(x + w <= box.width)
    model.Add(y + h <= box.height)

    return {"box_id": box_id, "x": x, "y": y, "w": w, "h": h}


def _add_non_overlap_constraints(model: cp_model.CpModel, item_vars: list[dict]) -> None:
    """Add non-overlapping constraints between items."""
    n = len(item_vars)
    for i in range(n):
        for j in range(i + 1, n):
            xi, yi, wi, hi, box_i = (
                item_vars[i]["x"],
                item_vars[i]["y"],
                item_vars[i]["w"],
                item_vars[i]["h"],
                item_vars[i]["box_id"],
            )
            xj, yj, wj, hj, box_j = (
                item_vars[j]["x"],
                item_vars[j]["y"],
                item_vars[j]["w"],
                item_vars[j]["h"],
                item_vars[j]["box_id"],
            )

            b_left = model.NewBoolVar(f"b_left_{i}_{j}")
            b_right = model.NewBoolVar(f"b_right_{i}_{j}")
            b_above = model.NewBoolVar(f"b_above_{i}_{j}")
            b_below = model.NewBoolVar(f"b_below_{i}_{j}")
            b_diff_box = model.NewBoolVar(f"diff_box_{i}_{j}")

            model.Add(box_i != box_j).OnlyEnforceIf(b_diff_box)
            model.Add(box_i == box_j).OnlyEnforceIf(b_diff_box.Not())

            model.Add(xi + wi <= xj).OnlyEnforceIf(b_left)
            model.Add(xj + wj <= xi).OnlyEnforceIf(b_right)
            model.Add(yi + hi <= yj).OnlyEnforceIf(b_below)
            model.Add(yj + hj <= yi).OnlyEnforceIf(b_above)

            model.AddBoolOr([b_left, b_right, b_above, b_below, b_diff_box])


def _add_objective_min_boxes(model: cp_model.CpModel, item_vars: list[dict]) -> cp_model.IntVar:
    """Add objective to minimize the total number of boxes used."""
    max_box_id = model.NewIntVar(0, len(item_vars), "max_box_id")
    for v in item_vars:
        model.Add(v["box_id"] <= max_box_id)
    model.Minimize(max_box_id)
    return max_box_id


def _add_objective_min_shrink(model: cp_model.CpModel, items: list[Item], item_vars: list[dict]) -> None:
    """Add objective to minimize total shrink across all items."""
    shrink_sum = sum(
        (item.width - vars["w"]) + (item.height - vars["h"]) for item, vars in zip(items, item_vars, strict=False)
    )
    model.Minimize(shrink_sum)


def _solve_model(
    items: list[Item],
    box_template: Box,
    max_boxes: int,
    equal_shrink: bool = False,
    time_limit: int = 30,
) -> tuple[list[PackedItem] | None, CpSolverStatus, float, int | None]:
    """Solve the packing problem for given items and box template."""
    model = _create_model()
    item_vars = [_add_item_variables(model, item, max_boxes, box_template, equal_shrink) for item in items]
    _add_non_overlap_constraints(model, item_vars)

    # Only add shrink objective if items are actually shrinkable
    total_initial_area = sum(item.width * item.height for item in items)
    total_min_area = sum(item.width_min * item.height_min for item in items)
    if total_initial_area > total_min_area:
        _add_objective_min_shrink(model, items, item_vars)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit

    start_time = time.time()
    status = solver.Solve(model)
    end_time = time.time()
    solve_time = end_time - start_time

    packed_items = None
    total_shrink_value = None

    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        packed_items = [
            PackedItem(
                id=item.id,
                x=solver.Value(vars["x"]),
                y=solver.Value(vars["y"]),
                width=solver.Value(vars["w"]),
                height=solver.Value(vars["h"]),
                box_id=solver.Value(vars["box_id"]),
            )
            for item, vars in zip(items, item_vars, strict=False)
        ]
        # Calculate total shrink value from the solution
        total_shrink_value = sum(
            (item.width - solver.Value(vars["w"])) + (item.height - solver.Value(vars["h"]))
            for item, vars in zip(items, item_vars, strict=False)
        )

    return packed_items, status, solve_time, total_shrink_value


def solve_scalable_rectpack(
    items: list[Item],
    box_width: int,
    box_height: int,
    equal_shrink: bool = False,
    per_box: bool = False,
    time_limit: int = 30,
) -> PackingResult:
    """Solve the two-dimensional rectangular packing problem with resizable items.

    The `solve_scalable_rectpack` function addresses the two-dimensional rectangular
    packing problem with resizable items. It employs a two-phase optimization approach:

    1. **Phase 1 (Box Minimization)**: Minimizes the total number of boxes required
       to pack all items by solving a constraint satisfaction problem that assigns
       items to boxes while ensuring no overlapping within each box.

    2. **Phase 2 (Shrink Optimization)**: Given the minimum number of boxes from
       Phase 1, optimizes the shrink of items to minimize total area reduction.
       This can be done either globally (across all boxes) or per-box.

    The algorithm uses Google OR-Tools CP-SAT solver for both phases, ensuring
    optimal or near-optimal solutions within the specified time limit.

    Parameters
    ----------
    items : list[Item]
        List of Item objects to pack. Each item has original dimensions (width, height)
        and minimum allowed dimensions (width_min, height_min) after shrinking.
    box_width : int
        Width of each packing box in the same units as item dimensions.
    box_height : int
        Height of each packing box in the same units as item dimensions.
    equal_shrink : bool, optional
        If True, items shrink equally in both width and height dimensions.
        If False, items can shrink independently in width and height.
        Default is False.
    per_box : bool, optional
        If True, shrink optimization is performed separately for each box
        (local optimization). If False, shrink optimization is performed
        globally across all boxes (global optimization). Default is False.
    time_limit : int, optional
        Maximum time in seconds for the CP-SAT solver to find a solution.
        Default is 30 seconds.

    Returns
    -------
    PackingResult
        A `PackingResult` object encapsulating the outcome of the packing process,
        including: a detailed `message`, `num_boxes_used`, `status_phase1`,
        `solve_time_phase1`, `outcome` (a `PackingOutcome` enum indicating the
        high-level result), and a list of `packing_results_per_mode`.
        The `success` property of `PackingResult` is derived from its `outcome`.
        Each entry in `packing_results_per_mode` is a `PerBoxPackingResult` object
        providing granular details for each box (if `per_box=True`) or for the
        global shrink optimization (if `per_box=False`).

    Raises
    ------
    ValueError
        If any of the input parameters have invalid values (e.g., negative numbers,
        empty items list, or logical inconsistencies in item dimensions).
    TypeError
        If any of the input parameters have incorrect types (e.g., non-Item objects
        in the items list).

    Notes
    -----
    - The algorithm guarantees that the minimum number of boxes is used
      (from Phase 1) before optimizing shrink (Phase 2).
    - Items are constrained to not overlap within the same box.
    - Each item's final dimensions must be >= its minimum dimensions.
    - For large problem instances, consider increasing time_limit or using
      per_box=True for better performance.

    Examples
    --------
    >>> from scalable_rectpack._core import Item, solve_scalable_rectpack, PackingOutcome
    >>> items = [
    ...     Item(id=1, width=100, height=50, width_min=80, height_min=40),
    ...     Item(id=2, width=60, height=80, width_min=50, height_min=70),
    ... ]
    >>> try:
    ...     result = solve_scalable_rectpack(items, box_width=200, box_height=200)
    ...     if result.success:
    ...         print(f"Packing successful. Outcome: {result.outcome.value}")
    ...         for res_box in result.packing_results_per_mode:
    ...             if res_box.packed_items:
    ...                 for item in res_box.packed_items:
    ...                     print(
    ...                         f"Item {item.id}: box {item.box_id}, pos ({item.x}, {item.y}), size {item.width}x{item.height}"
    ...                     )
    ...     else:
    ...         print(f"Packing failed. Outcome: {result.outcome.value}. Message: {result.message}")
    ... except (ValueError, TypeError) as e:
    ...     print(f"Input error: {e}")

    """
    # Input validation
    if not items:
        raise ValueError("Input 'items' list cannot be empty.")

    if not isinstance(box_width, int) or box_width <= 0:
        raise ValueError("'box_width' must be a positive integer.")

    if not isinstance(box_height, int) or box_height <= 0:
        raise ValueError("'box_height' must be a positive integer.")

    if not isinstance(time_limit, int) or time_limit <= 0:
        raise ValueError("'time_limit' must be a positive integer.")

    for item in items:
        if not isinstance(item, Item):
            raise TypeError(
                f"All elements in 'items' must be instances of Item, but found {type(item)}.",
            )
        if not isinstance(item.width, int) or item.width <= 0:
            raise ValueError(f"Item {item.id}: 'width' must be a positive integer.")
        if not isinstance(item.height, int) or item.height <= 0:
            raise ValueError(f"Item {item.id}: 'height' must be a positive integer.")
        if not isinstance(item.width_min, int) or item.width_min <= 0:
            raise ValueError(f"Item {item.id}: 'width_min' must be a positive integer.")
        if not isinstance(item.height_min, int) or item.height_min <= 0:
            raise ValueError(f"Item {item.id}: 'height_min' must be a positive integer.")
        if item.width_min > item.width:
            raise ValueError(
                f"Item {item.id}: 'width_min' ({item.width_min}) cannot be greater than 'width' ({item.width}).",
            )
        if item.height_min > item.height:
            raise ValueError(
                f"Item {item.id}: 'height_min' ({item.height_min}) cannot be greater than 'height' ({item.height}).",
            )
        if item.width_min > box_width or item.height_min > box_height:
            raise ValueError(
                f"Item {item.id}: minimum dimensions ({item.width_min}x{item.height_min}) exceed box dimensions ({box_width}x{box_height}).",
            )

    box_template = Box(0, box_width, box_height)
    max_boxes = len(items)

    # Step 1: Model1 - minimize number of boxes
    model1 = _create_model()
    item_vars1 = [_add_item_variables(model1, item, max_boxes, box_template, equal_shrink) for item in items]
    _add_non_overlap_constraints(model1, item_vars1)
    max_box_id = _add_objective_min_boxes(model1, item_vars1)

    solver1 = cp_model.CpSolver()
    solver1.parameters.max_time_in_seconds = time_limit
    status1 = solver1.Solve(model1)
    solve_time_phase1 = solver1.WallTime()

    if status1 not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        # Determine outcome for Phase 1 failure
        outcome_phase1 = (
            PackingOutcome.NO_SOLUTION_INFEASIBLE
            if status1 == cp_model.INFEASIBLE
            else PackingOutcome.NO_SOLUTION_TIMEOUT
        )
        return PackingResult(
            success=False,
            message="Phase 1 (Box Minimization) failed to find a feasible solution.",
            num_boxes_used=None,
            status_phase1=status1,
            solve_time_phase1=solve_time_phase1,
            outcome=outcome_phase1,
            box_width=box_width,
            box_height=box_height,
            packing_results=[],
        )

    min_boxes = solver1.Value(max_box_id) + 1

    # Step 2: Assign items to boxes
    box_to_items = {b: [] for b in range(min_boxes)}
    for item, vars in zip(items, item_vars1, strict=False):
        b = solver1.Value(vars["box_id"])
        box_to_items[b].append(item)

    # Step 3: Model2 - shrink optimization
    packing_results_per_mode: list[PerBoxPackingResult] = []
    overall_success_phase2 = True
    overall_message_phase2 = []
    total_shrink_global_sum = 0  # To accumulate if per_box=True

    if per_box:
        for box_id, box_items in box_to_items.items():
            # Call solve_model for each box
            packed_box, status_box_solve, solve_time_box, total_shrink_box = _solve_model(
                box_items,
                Box(box_id, box_width, box_height),
                1,
                equal_shrink,
                time_limit,
            )

            outcome_box_solve = (
                PackingOutcome.OPTIMAL
                if status_box_solve == cp_model.OPTIMAL
                else PackingOutcome.FEASIBLE
                if status_box_solve == cp_model.FEASIBLE
                else PackingOutcome.NO_SOLUTION_INFEASIBLE
                if status_box_solve == cp_model.INFEASIBLE
                else PackingOutcome.NO_SOLUTION_TIMEOUT
                if status_box_solve == cp_model.UNKNOWN
                else PackingOutcome.NO_SOLUTION_UNKNOWN
            )  # Fallback for other UNKNOWN cases

            if packed_box is None:
                overall_success_phase2 = False
                overall_message_phase2.append(
                    f"Box {box_id} local model2: No feasible solution. Status: {status_box_solve}.",
                )
                packing_results_per_mode.append(
                    PerBoxPackingResult(
                        box_id=box_id,
                        packed_items=None,
                        total_shrink=None,
                        status=status_box_solve,
                        solve_time=solve_time_box,
                        outcome=outcome_box_solve,
                        message=f"No feasible solution for box {box_id} shrink optimization.",
                    ),
                )
            else:
                for p in packed_box:
                    p.box_id = box_id  # Assign correct box_id
                total_shrink_global_sum += total_shrink_box if total_shrink_box is not None else 0
                packing_results_per_mode.append(
                    PerBoxPackingResult(
                        box_id=box_id,
                        packed_items=packed_box,
                        total_shrink=total_shrink_box,
                        status=status_box_solve,
                        solve_time=solve_time_box,
                        outcome=outcome_box_solve,
                        message=f"Box {box_id} shrink optimization successful.",
                    ),
                )

        # After loop, if any box failed, the overall_success_phase2 will be False
        if not overall_success_phase2:
            return PackingResult(
                success=False,
                message=f"Phase 2 (Shrink Optimization) failed for some boxes. Details: {'; '.join(overall_message_phase2)}",
                num_boxes_used=min_boxes,
                status_phase1=status1,
                solve_time_phase1=solve_time_phase1,
                outcome=PackingOutcome.NO_SOLUTION_UNKNOWN,  # If any box failed, overall is failure
                box_width=box_width,
                box_height=box_height,
                packing_results=packing_results_per_mode,  # Include partial results
            )
        else:
            # If all boxes succeeded, check if all were optimal or some feasible
            all_optimal = all(res.outcome == PackingOutcome.OPTIMAL for res in packing_results_per_mode)
            overall_outcome_phase2 = PackingOutcome.OPTIMAL if all_optimal else PackingOutcome.FEASIBLE
            return PackingResult(
                success=True,
                message=f"Packing successful with {min_boxes} boxes. Total shrink: {total_shrink_global_sum}",
                num_boxes_used=min_boxes,
                status_phase1=status1,
                solve_time_phase1=solve_time_phase1,
                outcome=overall_outcome_phase2,
                box_width=box_width,
                box_height=box_height,
                packing_results=packing_results_per_mode,
            )

    else:  # per_box == False
        all_items = [item for box_items in box_to_items.values() for item in box_items]
        packed_global, status_global_solve, solve_time_global, total_shrink_global = _solve_model(
            all_items,
            box_template,
            min_boxes,
            equal_shrink,
            time_limit,
        )

        outcome_global_solve = (
            PackingOutcome.OPTIMAL
            if status_global_solve == cp_model.OPTIMAL
            else PackingOutcome.FEASIBLE
            if status_global_solve == cp_model.FEASIBLE
            else PackingOutcome.NO_SOLUTION_INFEASIBLE
            if status_global_solve == cp_model.INFEASIBLE
            else PackingOutcome.NO_SOLUTION_TIMEOUT
            if status_global_solve == cp_model.UNKNOWN
            else PackingOutcome.NO_SOLUTION_UNKNOWN
        )  # Fallback for other UNKNOWN cases

        if packed_global is None:
            packing_results_per_mode.append(
                PerBoxPackingResult(
                    box_id=None,
                    packed_items=None,
                    total_shrink=None,
                    status=status_global_solve,
                    solve_time=solve_time_global,
                    outcome=outcome_global_solve,
                    message=f"Global shrink optimization failed: {status_global_solve}.",
                ),
            )
            return PackingResult(
                success=False,
                message=f"Phase 2 (Global Shrink Optimization) failed. Solver status: {status_global_solve}.",
                num_boxes_used=min_boxes,
                status_phase1=status1,
                solve_time_phase1=solve_time_phase1,
                outcome=outcome_global_solve,
                box_width=box_width,
                box_height=box_height,
                packing_results=packing_results_per_mode,
            )
        else:
            packing_results_per_mode.append(
                PerBoxPackingResult(
                    box_id=None,
                    packed_items=packed_global,
                    total_shrink=total_shrink_global,
                    status=status_global_solve,
                    solve_time=solve_time_global,
                    outcome=outcome_global_solve,
                    message="Global shrink optimization successful.",
                ),
            )
            return PackingResult(
                success=True,
                message=f"Packing successful with {min_boxes} boxes. Total shrink: {total_shrink_global}",
                num_boxes_used=min_boxes,
                status_phase1=status1,
                solve_time_phase1=solve_time_phase1,
                outcome=outcome_global_solve,
                box_width=box_width,
                box_height=box_height,
                packing_results=packing_results_per_mode,
            )
