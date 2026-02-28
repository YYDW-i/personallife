from dataclasses import dataclass
from secrets import SystemRandom
from typing import List, Optional, Tuple

_rng = SystemRandom()

@dataclass
class CastState:
    # bottom -> top
    primary_arr: List[int]           # 6 bits: 1 yang, 0 yin
    relating_arr: Optional[List[int]]
    moving_lines: List[int]          # 1..6
    line_nums: List[int]             # 6/7/8/9 bottom->top
    coin_results: List[Tuple[int, int, int]]

def _throw_three_coins() -> Tuple[int, int, int]:
    """抛三枚硬币，返回三个值（2=反面，3=正面）"""
    return (_rng.choice([2, 3]),
            _rng.choice([2, 3]),
            _rng.choice([2, 3]))

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
    coins: List[Tuple[int, int, int]] = []

    for idx in range(1, 7):  # 1..6 bottom->top
        if method in ("coins", "random"):
            a, b, c = _throw_three_coins()
            n = a + b + c
        elif method == "time":
            # 时间起卦不涉及真实硬币，但我们仍可模拟一个随机组合
            n = _rng.choice([6, 7, 8, 9])
            # 为了视觉一致性，用 n 生成一个假的三硬币组合（仅用于显示）
            if n == 6:
                a, b, c = 2, 2, 2
            elif n == 7:
                a, b, c = 3, 2, 2
            elif n == 8:
                a, b, c = 2, 3, 3
            else:  # 9
                a, b, c = 3, 3, 3
        else:
            raise ValueError("method must be coins/random/time")

        nums.append(n)
        coins.append((a, b, c))

        if n in (6, 9):
            moving.append(idx)

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
        coin_results=coins,
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