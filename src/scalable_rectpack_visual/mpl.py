import matplotlib.patches as patches
import matplotlib.pyplot as plt
from matplotlib.figure import Figure

from scalable_rectpack._core import PerBoxPackingResult


def visualize_packing(
    fig: Figure,
    packing_result: PerBoxPackingResult,
    box_width: int,
    box_height: int,
) -> None:
    """Visualize the packed items in a single box using matplotlib.

    Parameters
    ----------
    fig : Figure
        The matplotlib Figure object to draw on
    packing_result : PerBoxPackingResult
        The packing result for a single box
    box_width : int
        Box width
    box_height : int
        Box height

    """
    ax = fig.add_subplot(1, 1, 1)

    colors = [
        "skyblue",
        "lightgreen",
        "salmon",
        "khaki",
        "plum",
        "orange",
        "lightpink",
        "lightcoral",
        "lightseagreen",
        "gold",
    ]

    ax.set_title(f"Box {packing_result.box_id}" if packing_result.box_id is not None else "Packing Result")
    ax.set_xlim(0, box_width)
    ax.set_ylim(0, box_height)
    ax.set_aspect("equal")
    ax.grid(True, alpha=0.3)

    if packing_result.packed_items is None:
        ax.text(box_width / 2, box_height / 2, "No items packed", ha="center", va="center", fontsize=14, color="red")
        return

    for idx, item in enumerate(packing_result.packed_items):
        color = colors[idx % len(colors)]
        rect = patches.Rectangle(
            (item.x, item.y),
            item.width,
            item.height,
            linewidth=1,
            edgecolor="black",
            facecolor=color,
            alpha=0.7,
        )
        ax.add_patch(rect)

        cx = item.x + item.width / 2
        cy = item.y + item.height / 2
        ax.text(cx, cy, str(item.id), ha="center", va="center", fontsize=12, fontweight="bold")

    box_border = patches.Rectangle(
        (0, 0),
        box_width,
        box_height,
        linewidth=2,
        edgecolor="black",
        facecolor="none",
    )
    ax.add_patch(box_border)
