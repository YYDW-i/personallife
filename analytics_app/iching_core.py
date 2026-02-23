from dataclasses import dataclass
from secrets import SystemRandom
from typing import List, Optional

_rng = SystemRandom()

@dataclass
class CastState:
    # bottom -> top
    primary_arr: List[int]           # 6 bits: 1 yang, 0 yin
    relating_arr: Optional[List[int]]
    moving_lines: List[int]          # 1..6
    line_nums: List[int]             # 6/7/8/9 bottom->top


def _cast_three_coins_one_line() -> int:
    # heads=3 tails=2 => 6/7/8/9
    a = _rng.choice([2, 3])
    b = _rng.choice([2, 3])
    c = _rng.choice([2, 3])
    return a + b + c


def cast_hexagram(method: str = "coins") -> CastState:
    primary_arr: List[int] = []
    moving: List[int] = []
    nums: List[int] = []

    for idx in range(1, 7):  # 1..6 bottom->top
        if method in ("coins", "random"):
            n = _cast_three_coins_one_line()
        elif method == "time":
            # 简化版：本质还是随机，但你后面可以替换成“梅花易数”的时间取数
            n = _rng.choice([6, 7, 8, 9])
        else:
            raise ValueError("method must be coins/random/time")

        nums.append(n)

        # 6 老阴（动） 7 少阳 8 少阴 9 老阳（动）
        if n in (6, 9):
            moving.append(idx)

        # 阳：7/9 => 1；阴：6/8 => 0
        primary_arr.append(1 if n in (7, 9) else 0)

    relating_arr = None
    if moving:
        relating_arr = primary_arr[:]
        for idx in moving:
            relating_arr[idx - 1] = 1 - relating_arr[idx - 1]

    return CastState(
        primary_arr=primary_arr,
        relating_arr=relating_arr,
        moving_lines=moving,
        line_nums=nums,
    )


def render_lines(arr: List[int], moving_lines: List[int], nums: List[int]) -> List[str]:
    """
    arr: bottom->top, 1 yang 0 yin
    moving_lines: 1..6
    nums: 6/7/8/9 bottom->top
    """
    out: List[str] = []
    for i in range(6):
        is_yang = arr[i] == 1
        is_moving = (i + 1) in moving_lines
        
        if is_yang:
            s = "█████████"
            mark = " ○" if (is_moving and nums[i] == 9) else ""
        else:
            s = "███      ███"
            mark = " ×" if (is_moving and nums[i] == 6) else ""
        out.append(f"{s}{mark}")
    return out