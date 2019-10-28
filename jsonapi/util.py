from collections.abc import Sequence


def v(val):
    if isinstance(val, str) or not isinstance(val, Sequence):
        yield val
    else:
        for item in val:
            yield item
