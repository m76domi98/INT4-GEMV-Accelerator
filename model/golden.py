"""Integer golden model for the up_proj INT4 x INT8 GEMV (spec 01, numeric format).

Integer arithmetic only. Python ints are exact, so the datapath matches the RTL
bit for bit. No floats and no NumPy appear in this file. `>>` is an arithmetic
shift (rounds toward -inf for negative values), which is what RTL does on signed values.
"""
import operator

REQUANT_SHIFT = 15
REQUANT_ROUND = 1 << (REQUANT_SHIFT - 1)  # 2^14: round half up before the shift
Y_MIN = -128
Y_MAX = 127


def raw_acc(q_rows: list[list[int]], x_int: list[int]) -> list[int]:
    """Raw per-row accumulators for one vector, before requant. The tile test compares these.

    q_rows and x_int have the same meaning as in gemv_int.
    """
    return [sum(map(operator.mul, row, x_int)) for row in q_rows]  # exact int dot product per row, no requant


def gemv_int(
    q_rows: list[list[int]], x_int: list[int], m_rows: list[int]
) -> tuple[list[int], int, int]:
    """One GEMV. Returns (y_int, max_abs_acc, requant_saturations).

    q_rows: one list of INT4 weight codes per output row, each in [-8, 7].
    x_int: INT8 activation vector, each value in [-127, 127].
    m_rows: fixed-point requant multiplier M_r per output row.
    """
    y_int = []  # one INT8 output per row, filled in below
    max_abs_acc = 0  # biggest |acc| seen so far, to check it fits the accumulator
    saturations = 0  # how many rows needed clipping after requant
    for row, m in zip(q_rows, m_rows):
        acc = sum(map(operator.mul, row, x_int))  # this row's dot product with x, exact int
        max_abs_acc = max(max_abs_acc, abs(acc))
        y = (acc * m + REQUANT_ROUND) >> REQUANT_SHIFT  # scale by M_r, shift back down; the +ROUND makes the shift round instead of chop
        if not Y_MIN <= y <= Y_MAX:  # outside INT8, so the clip below will kick in
            saturations += 1
        y_int.append(min(max(y, Y_MIN), Y_MAX))  # clamp to INT8, the RTL does the same saturate
    return y_int, max_abs_acc, saturations
