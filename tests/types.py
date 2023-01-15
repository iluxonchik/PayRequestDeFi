import functools
from enum import Enum


class MinMaxEnum(Enum):
    @classmethod
    @functools.lru_cache(maxsize=1)
    def min_value(cls) -> int:
        return min([member.value for member in cls])

    @classmethod
    @functools.lru_cache(maxsize=1)
    def max_value(cls) -> int:
        return max([member.value for member in cls])