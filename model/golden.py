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


def gemv_int(
    q_rows: list[list[int]], x_int: list[int], m_rows: list[int]
) -> tuple[list[int], int, int]:
    """One GEMV. Returns (y_int, max_abs_acc, requant_saturations).

    q_rows: one list of INT4 weight codes per output row, each in [-8, 7].
    x_int: INT8 activation vector, each value in [-127, 127].
    m_rows: fixed-point requant multiplier M_r per output row.
    """
    y_int = []
    max_abs_acc = 0
    saturations = 0
    for row, m in zip(q_rows, m_rows):
        acc = sum(map(operator.mul, row, x_int))
        max_abs_acc = max(max_abs_acc, abs(acc))
        y = (acc * m + REQUANT_ROUND) >> REQUANT_SHIFT
        if not Y_MIN <= y <= Y_MAX:
            saturations += 1
        y_int.append(min(max(y, Y_MIN), Y_MAX))
    return y_int, max_abs_acc, saturations
