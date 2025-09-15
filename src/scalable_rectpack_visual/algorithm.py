from dataclasses import dataclass, field

from scalable_rectpack import Item, PackingResult, solve_scalable_rectpack


@dataclass
class RectPacker:
    items: list[Item] = field(default_factory=list)
    box_width: int = 0
    box_height: int = 0
    equal_shrink: bool = True
    per_box: bool = True
    time_limit: int = 30
    packing_result: PackingResult | None = None

    def run(self):
        self.packing_result = solve_scalable_rectpack(
            self.items,
            self.box_width,
            self.box_height,
            self.equal_shrink,
            self.per_box,
            self.time_limit,
        )

    @staticmethod
    def validate_ge0_int(name: str, value: int):
        if isinstance(value, int):
            value_int = value
        else:
            try:
                value_int = int(value)
            except Exception:
                return f"{name} must be an integer"

            if value_int - value > 1e-6:
                return f"{name} must be an integer"

        if value_int <= 0:
            return f"{name} must be greater than 0"
        return None

    def append_item(self, item: Item):
        self.items.append(item)

    def delete_item(self, item_id: int):
        self.items.pop(item_id)
        for i, item in enumerate(self.items):
            item.id = i
