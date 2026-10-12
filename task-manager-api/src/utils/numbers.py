"""Pure numeric helpers with no domain knowledge.

`percentage` is salvaged from the dead utils/helpers.calculate_percentage,
which was imported by the reporting module and never called while the same
expression was written out three times (QUA-01).
"""

PERCENT_DECIMALS = 2


def percentage(part: float, total: float) -> float:
    """Percentage of `part` in `total`, rounded. Zero total yields 0."""
    if not total:
        return 0
    return round((part / total) * 100, PERCENT_DECIMALS)
