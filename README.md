# scalable-rectpack

---

A scalable 2D rectangle packing tool for efficient space optimization.

<div align="center">

[![License](https://img.shields.io/github/license/MilkMilkMilky/scalable-rectpack)](https://github.com/MilkMilkMilky/scalable-rectpack/blob/main/LICENSE)
[![Commit activity](https://img.shields.io/github/commit-activity/m/MilkMilkMilky/scalable-rectpack)](https://github.com/MilkMilkMilky/scalable-rectpack/commits/main)
[![python versions](https://img.shields.io/badge/python-%3E%3D3.10-blue)](https://github.com/MilkMilkMilky/scalable-rectpack)

</div>

<div align="center">
    <a href="https://github.com/MilkMilkMilky/scalable-rectpack">Github</a>
</div>

## Overview

The Scalable 2D Rectangle Packing Tool is a flexible and efficient solution for the 2D bin packing problem, where rectangles of varying sizes need to be placed inside a bounded area with minimal wasted space.

## Features

- 📏 Scalable & Flexible – Supports rectangles with adjustable dimensions and constraints.
- ⚡ Optimization-Driven – Minimizes wasted area while ensuring feasible placement.
- 🧩 General-Purpose – Applicable in layout design, photo walls, cutting stock, game level
- 📊 Visualization Ready – Integrated plotting functions to visualize packing results.
- 🔬 Research & Practical Use – Useful both for algorithmic experimentation and real-world

## Installation

To install the project, run the following command:

```bash
python -m pip install git+https://github.com/MilkMilkMilky/scalable-rectpack.git
```

Or install from local:

```bash
git clone https://github.com/MilkMilkMilky/scalable-rectpack.git
cd scalable-rectpack
python -m pip install .
```

## Usage

### Quick start

```python
from scalable_rectpack._core import Item, solve_scalable_rectpack, PackingOutcome

# 1) Define items (original size and minimum allowed size)
items = [
    Item(id=1, width=120, height=80,  width_min=100, height_min=60),
    Item(id=2, width=90,  height=110, width_min=70,  height_min=90),
    Item(id=3, width=60,  height=60,  width_min=50,  height_min=50),
]

# 2) Define box size
box_width, box_height = 200, 200

# 3) Solve. Recommended defaults for speed: equal_shrink=True, per_box=True
result = solve_scalable_rectpack(
    items=items,
    box_width=box_width,
    box_height=box_height,
    equal_shrink=True,    # shrink equally in both dimensions (faster in practice)
    per_box=True,         # optimize shrink per physical box (faster to optimal)
    time_limit=30,
)

if not result.success:
    print(f"Failed: {result.outcome.value}. {result.message}")
else:
    print(f"Boxes used: {result.num_boxes_used}; outcome: {result.outcome.value}")
    for box_res in result.packing_results:
        if box_res.packed_items:
            print(f"Box {box_res.box_id if box_res.box_id is not None else 'GLOBAL'}: shrink={box_res.total_shrink}")
            for p in box_res.packed_items:
                print(f"  item {p.id} -> box {p.box_id}, pos=({p.x},{p.y}), size={p.width}x{p.height}")

```

### Concepts and parameters

- **Items and box**: You provide a list of `Item(id, width, height, width_min, height_min)` and a single box size `(box_width, box_height)`. The solver decides how many boxes are needed and where each item is placed.

- **Two-phase optimization**:

  - **Phase 1 (minimize box count)**: The solver first minimizes the number of boxes needed to pack all items without overlap.
  - **Phase 2 (minimize shrink)**: Given the minimum number of boxes from Phase 1, the solver minimizes the total shrink of items.

- **equal_shrink: bool**

  - `True` (recommended default): Each rectangle’s width and height shrink by the same amount. Squares remain squares after shrinking.
  - `False`: Width and height can shrink independently within their allowed ranges.

- **per_box: bool**

  - `True` (recommended default): Phase 2 optimizes shrink separately for each box using the items assigned in Phase 1. Faster to reach optimality. Because Phase 1 only minimizes box count and may assign items differently across runs, the final per-box total shrink can vary between runs.
  - `False`: Phase 2 performs a global optimization across all boxes while keeping the number of boxes at the Phase 1 minimum. This yields a deterministic total shrink when the result is optimal. However, it may take much longer to prove optimality; you may see feasible (but not proven optimal) solutions for tens of seconds or even minutes.

- **time_limit: int (seconds)**
  - Limits the OR-Tools CP-SAT solver wall time per phase/solve. If the optimal solution is not proven within the limit, a feasible solution (if found) is returned with outcome `FEASIBLE`.
  - If you already have a feasible solution and want to try to reach optimality, increase `time_limit`.

### API reference (core)

```python
from scalable_rectpack._core import Item, solve_scalable_rectpack, PackingResult

result: PackingResult = solve_scalable_rectpack(
    items: list[Item],
    box_width: int,
    box_height: int,
    equal_shrink: bool = False,
    per_box: bool = False,
    time_limit: int = 30,
)
```

- **Return value**: `PackingResult` contains
  - `success: bool`
  - `outcome: PackingOutcome` – `OPTIMAL`, `FEASIBLE`, or a no-solution status
  - `message: str`
  - `num_boxes_used: int | None`
  - `status_phase1: CpSolverStatus`, `solve_time_phase1: float`
  - `box_width: int`, `box_height: int`
  - `packing_results: list[PerBoxPackingResult]`

Each `PerBoxPackingResult` contains:

- `box_id: int | None` (None for global result when `per_box=False`)
- `packed_items: list[PackedItem] | None`
- `total_shrink: int | None`
- `status: CpSolverStatus`, `solve_time: float`, `outcome: PackingOutcome`, `message: str | None`

Each `PackedItem` contains: `id, x, y, width, height, box_id`.

### Examples

1. Equal shrink to keep squares square

```python
result = solve_scalable_rectpack(
    items=items,
    box_width=200,
    box_height=200,
    equal_shrink=True,   # width and height shrink equally
    per_box=True,
    time_limit=20,
)
```

2. Global optimization across boxes (deterministic total shrink when optimal)

```python
result = solve_scalable_rectpack(
    items=items,
    box_width=200,
    box_height=200,
    equal_shrink=False,
    per_box=False,       # global Phase-2
    time_limit=120,      # allow more time to prove optimality
)
```

3. Faster per-box optimization (final shrink may vary between runs)

```python
result = solve_scalable_rectpack(
    items=items,
    box_width=200,
    box_height=200,
    equal_shrink=False,
    per_box=True,        # per-box Phase-2
    time_limit=15,
)
```

### Practical tips

- Start with `per_box=True` for faster high-quality results. Switch to `per_box=False` and raise `time_limit` if you need globally optimal shrink.
- If some items’ minimum size exceeds the box size, the solver raises `ValueError`.
- For large instances, consider increasing `time_limit`.
- For speed in most cases, prefer `equal_shrink=True` and `per_box=True`.

## License

This project is licensed under the MIT license.
Check the [LICENSE](LICENSE) file for more details.

## Contributing

Please follow the [Contributing Guide](https://github.com/MilkMilkMilky/scalable-rectpack/blob/main/CONTRIBUTING.md) to contribute to this project.

## Contact

For support or inquiries, please contact:

- Email: milkcowmilky@gmail.com
