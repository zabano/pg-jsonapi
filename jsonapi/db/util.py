import datetime as dt
import operator

from jsonapi.exc import Error

DATETIME_FORMATS = ('%Y-%m-%dT%H:%M:%SZ', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M', '%Y-%m-%d', '%Y-%m')
DATE_FORMATS = ('%Y-%m-%d', '%Y-%m')
TIME_FORMATS = ('%H:%M:%SZ', '%H:%M')

TRUE_VALUES = ('t', 'true', 'on', '1')
FALSE_VALUES = ('f', 'false', 'off', '0')
NULL_VALUES = ('null', 'none', 'na')

OPERATORS = ('', 'eq', 'ne', 'gt', 'ge', 'lt', 'le')
MODIFIERS = {'=': operator.eq, '<>': operator.ne, '!=': operator.ne,
             '>=': operator.ge, '<=': operator.le, '>': operator.gt, '<': operator.lt}


def get_primary_key(table):
    """
    Get table primary key column.

    .. note::

        Assumes a simple (non-composite) key and returns the first column.

    :param table: SQLAlchemy Table object
    :return: the primary key column
    """
    return table.primary_key.columns.values()[0]


def parse_bool(val):
    if val.lower() in NULL_VALUES:
        return
    if val.lower() not in TRUE_VALUES and val.lower() not in FALSE_VALUES:
        raise Error('invalid value: {}'.format(val))
    return val.lower() in TRUE_VALUES


def parse_int(val):
    if val.lower() in NULL_VALUES:
        return
    try:
        return int(val)
    except ValueError:
        raise Error('invalid value: {}'.format(val))


def parse_float(val):
    if val.lower() in NULL_VALUES:
        return
    try:
        return float(val)
    except ValueError:
        raise Error('invalid value: {}'.format(val))


def parse_date(val):
    if val.lower() in NULL_VALUES:
        return
    fmt = {len(fmt) + 2: fmt for fmt in DATE_FORMATS}
    if len(val) not in fmt:
        raise Error('invalid value: {}'.format(val))
    return dt.datetime.strptime(val, fmt[len(val)])


def parse_time(val):
    if val.lower() in NULL_VALUES:
        return
    fmt = {len(fmt): fmt for fmt in TIME_FORMATS}
    if len(val) not in fmt:
        raise Error('invalid value: {}'.format(val))
    return dt.datetime.strptime(val, fmt[len(val)])


def parse_datetime(val):
    if val.lower() in NULL_VALUES:
        return
    fmt = {len(fmt) + 2: fmt for fmt in DATETIME_FORMATS}
    if len(val) not in fmt:
        raise Error('invalid value: {}'.format(val))
    return dt.datetime.strptime(val, fmt[len(val)])
