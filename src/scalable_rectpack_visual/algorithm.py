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
    def validate_box_width(box_width: int):
        if not isinstance(box_width, int):
            raise ValueError("Box width must be an integer")
        if box_width <= 0:
            raise ValueError("Box width must be greater than 0")

    @staticmethod
    def validate_box_height(box_height: int):
        if not isinstance(box_height, int):
            raise ValueError("Box height must be an integer")
        if box_height <= 0:
            raise ValueError("Box height must be greater than 0")

    @staticmethod
    def validate_items(items: list[Item]):
        if not items:
            raise ValueError("Items must be a non-empty list")
        for item in items:
            if not isinstance(item, Item):
                raise ValueError("Items must be a list of Item objects")
            if item.width <= 0 or item.height <= 0 or item.width_min <= 0 or item.height_min <= 0:
                raise ValueError("Item dimensions must be greater than 0")

    @staticmethod
    def validate_time_limit(time_limit: int):
        if time_limit <= 0:
            raise ValueError("Time limit must be greater than 0")

    def append_item(self, item: Item):
        self.items.append(item)

    def delete_item(self, item_id: int):
        self.items.pop(item_id)
        for i, item in enumerate(self.items):
            item.id = i
