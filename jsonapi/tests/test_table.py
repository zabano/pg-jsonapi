import pytest
from sqlalchemy.sql import Join, and_
from sqlalchemy.sql.schema import Table

from jsonapi.db.table import FromClause, FromItem, is_clause, is_from_item
from jsonapi.exc import Error
from jsonapi.tests.db import user_names_t, users_t


def test_is_clause():
    assert is_clause(users_t.c.id == 1)
    assert is_clause(and_(users_t.c.id == 1, users_t.c.status == 'active'))
    assert not is_clause(1)
    assert not is_clause(False)
    assert not is_clause(None)
    assert not is_clause('test')
    assert not is_clause(users_t)


####################################################################################################
# FromItem
####################################################################################################


def test_is_from_item():
    users_a = users_t.alias('test')
    assert is_from_item(FromItem(users_t))
    assert is_from_item(users_t)
    assert is_from_item(users_a)
    assert not is_from_item(1)
    assert not is_from_item(False)
    assert not is_from_item(None)
    assert not is_from_item('test')


def test_from_item_1():
    from_item = FromItem(users_t)
    assert from_item.table == users_t
    assert from_item.left is False
    assert from_item.onclause is None
    assert from_item.name == users_t.name


def test_from_item_2():
    users_a = users_t.alias('test')
    from_item = FromItem(users_a)
    assert from_item.table == users_a
    assert from_item.left is False
    assert from_item.onclause is None
    assert from_item.name == 'test'


def test_from_item_3():
    from_item = FromItem(users_t, left=True)
    assert from_item.table == users_t
    assert from_item.left is True
    assert from_item.onclause is None


def test_from_item_4():
    from_item = FromItem(users_t, onclause=users_t.c.id == 1, left=True)
    assert from_item.table == users_t
    assert from_item.left is True
    assert from_item.onclause is not None


def test_from_item_5():
    from_item = FromItem(users_t, onclause=users_t.c.id == 1)
    assert from_item.table == users_t
    assert from_item.left is False
    assert from_item.onclause is not None


def test_from_item_exc_1():
    with pytest.raises(Error):
        FromItem(None)


def test_from_item_exc_2():
    with pytest.raises(Error):
        FromItem('test')


def test_from_item_exc_3():
    with pytest.raises(Error):
        FromItem(users_t, onclause=True)


def test_from_item_exc_4():
    with pytest.raises(Error):
        FromItem(users_t, onclause=1)


def test_from_item_exc_5():
    with pytest.raises(Error):
        FromItem(users_t, onclause='test')


####################################################################################################
# FromClause
####################################################################################################

def test_from_clause():
    fc = FromClause(users_t)
    assert len(fc) == 1
    fc.append(FromItem(user_names_t, left=True))
    assert len(fc) == 2
    fc.append(FromItem(user_names_t, left=True))
    assert len(fc) == 2
    fc.append(FromItem(users_t.alias('test')))
    assert len(fc) == 3
    for from_item in fc:
        assert isinstance(from_item, FromItem)
    assert isinstance(fc(), Join)
    assert isinstance(fc.pop(), FromItem)
    assert isinstance(fc(), Join)
    assert isinstance(fc.pop(), FromItem)
    assert isinstance(fc(), Table)


def test_from_clause_exc():
    with pytest.raises(Error):
        FromClause(users_t, user_names_t, 'test')
