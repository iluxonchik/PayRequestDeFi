from dataclasses import dataclass
from typing import Any


class ValueRange:
    min_value: Any
    max_value: Any


@dataclass
class IntegerValueRange(ValueRange):
    min_value: int
    max_value: int


class IntegerValue(ValueRange):
    def __init__(self, value: int):
        self._integer_value_range: IntegerValueRange = IntegerValueRange(min_value=value, max_value=value)

    @property
    def min_value(self):
        return self._integer_value_range.min_value

    @property
    def max_value(self):
        return self._integer_value_range.max_value
