import pytest
from sqlalchemy.sql.elements import BinaryExpression

from jsonapi.datatypes import Bool
from jsonapi.db.filter import FilterClause
from jsonapi.exc import Error
from jsonapi.tests.db import test_data_t


def test_filter_clause_bool():
    fc = Bool.filter_clause
    assert isinstance(fc, FilterClause)

    assert fc.has_operator('')
    assert fc.has_operator('eq')
    assert fc.has_operator('ne')
    assert fc.has_operator('', multiple=True)
    assert fc.has_operator('eq', multiple=True)
    assert fc.has_operator('ne', multiple=True)

    assert not fc.has_operator('gt')
    assert not fc.has_operator('lt')
    assert not fc.has_operator('gt')
    assert not fc.has_operator('lt')
    assert not fc.has_operator('gt', multiple=True)
    assert not fc.has_operator('lt', multiple=True)
    assert not fc.has_operator('gt', multiple=True)
    assert not fc.has_operator('lt', multiple=True)

    assert isinstance(fc.get(test_data_t.c.test_bool, '', 't'), BinaryExpression)
    assert isinstance(fc.get(test_data_t.c.test_bool, 'eq', 'none'), BinaryExpression)
    assert isinstance(fc.get(test_data_t.c.test_bool, 'ne', 't'), BinaryExpression)
    assert isinstance(fc.get(test_data_t.c.test_bool, '', 'f,t'), BinaryExpression)
    assert isinstance(fc.get(test_data_t.c.test_bool, 'eq', 'f,none'), BinaryExpression)
    assert isinstance(fc.get(test_data_t.c.test_bool, 'ne', 'f,none'), BinaryExpression)

    with pytest.raises(Error, match='invalid operator: gt'):
        fc.get(test_data_t.c.test_bool, 'gt', 'f')
    with pytest.raises(Error, match='invalid operator: lt'):
        fc.get(test_data_t.c.test_bool, 'lt', 't')
    with pytest.raises(Error, match='invalid operator: ge'):
        fc.get(test_data_t.c.test_bool, 'ge', 'none')
    with pytest.raises(Error, match='invalid operator: le'):
        fc.get(test_data_t.c.test_bool, 'le', 't,f')
