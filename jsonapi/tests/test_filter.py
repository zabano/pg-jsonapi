import pytest
from sqlalchemy.sql.elements import BinaryExpression

from jsonapi.datatypes import Bool
from jsonapi.db.filter import FilterClause
from jsonapi.exc import Error
from jsonapi.tests.db import test_data_t
from jsonapi.tests.util import *


#
# FilterClause
#


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


#
# int (single)
#


@pytest.mark.asyncio
async def test_int(articles, superuser_id):
    async with get_collection(articles,
                              {'fields[article]': 'id',
                               'filter[id]': '5',
                               'page[size]': 10},
                              login=superuser_id) as json:
        assert isinstance(json['data'], list)
        assert len(json['data']) == 1
        for article in json['data']:
            assert_object(article, 'article', lambda v: int(v) == 5)


@pytest.mark.asyncio
async def test_int_eq(articles, superuser_id):
    async with get_collection(articles,
                              {'fields[article]': 'id',
                               'filter[id:eq]': '5',
                               'page[size]': 10},
                              login=superuser_id) as json:
        assert isinstance(json['data'], list)
        assert len(json['data']) == 1
        for article in json['data']:
            assert_object(article, 'article', lambda v: int(v) == 5)


@pytest.mark.asyncio
async def test_int_ne(articles, superuser_id):
    async with get_collection(articles,
                              {'fields[article]': 'id',
                               'filter[id:ne]': '5',
                               'page[size]': 10},
                              login=superuser_id) as json:
        assert isinstance(json['data'], list)
        assert len(json['data']) == 10
        for article in json['data']:
            assert_object(article, 'article', lambda v: v != '5')


@pytest.mark.asyncio
async def test_int_lt(articles, superuser_id):
    async with get_collection(articles,
                              {'fields[article]': 'id',
                               'filter[id:lt]': '5',
                               'page[size]': 10},
                              login=superuser_id) as json:
        assert isinstance(json['data'], list)
    assert len(json['data']) == 4
    for article in json['data']:
        assert_object(article, 'article', lambda v: int(v) < 5)


@pytest.mark.asyncio
async def test_int_le(articles, superuser_id):
    async with get_collection(articles,
                              {'fields[article]': 'id',
                               'filter[id:le]': '5',
                               'page[size]': 10},
                              login=superuser_id) as json:
        assert isinstance(json['data'], list)
        assert len(json['data']) == 5
        for article in json['data']:
            assert_object(article, 'article', lambda v: int(v) <= 5)


@pytest.mark.asyncio
async def test_int_gt(articles, superuser_id):
    async with get_collection(articles,
                              {'fields[article]': 'id',
                               'filter[id:gt]': '5',
                               'page[size]': 10},
                              login=superuser_id) as json:
        assert isinstance(json['data'], list)
        assert len(json['data']) == 10
        for article in json['data']:
            assert_object(article, 'article', lambda v: int(v) > 5)


@pytest.mark.asyncio
async def test_int_ge(articles, superuser_id):
    async with get_collection(articles,
                              {'fields[article]': 'id',
                               'filter[id:ge]': '5',
                               'page[size]': 10},
                              login=superuser_id) as json:
        assert isinstance(json['data'], list)
        assert len(json['data']) == 10
        for article in json['data']:
            assert_object(article, 'article', lambda v: int(v) >= 5)


#
# integer (multiple)
#

@pytest.mark.asyncio
async def test_int_multiple_1(articles, superuser_id):
    async with get_collection(articles,
                              {'fields[article]': 'id',
                               'filter[id]': '1,2,3,4,5,6,7,8,9,10'},
                              login=superuser_id) as json:
        assert isinstance(json['data'], list)
        assert len(json['data']) == 10
        for article in json['data']:
            assert_object(article, 'article', lambda v: int(v) <= 10)


@pytest.mark.asyncio
async def test_int_multiple_2(articles, article_count, superuser_id):
    async with get_collection(articles,
                              {'fields[article]': 'id',
                               'filter[id]': '<4,6,>={:d}'.format(article_count - 1)},
                              login=superuser_id) as json:
        assert isinstance(json['data'], list)
        assert len(json['data']) == 6
        for article in json['data']:
            assert_object(article, 'article',
                          lambda v: int(v) in (1, 2, 3, 6, article_count - 1, article_count))


#
# bool
#


@pytest.mark.asyncio
async def test_bool_1(articles, superuser_id):
    for val in ('t', 'T', 'true', 'True', 'TRUE', '1', 'on', 'On', 'ON', 'yes', 'Yes', 'YES'):
        async with get_collection(articles,
                                  {'fields[article]': 'is-published',
                                   'filter[is-published]': val,
                                   'page[size]': 10},
                                  login=superuser_id) as json:
            assert isinstance(json['data'], list)
            assert len(json['data']) == 10
            for article in json['data']:
                assert_attribute(article, 'isPublished', lambda v: v is True)


@pytest.mark.asyncio
async def test_bool_2(articles, superuser_id):
    for val in ('f', 'F', 'false', 'False', 'FALSE', '0', 'off', 'Off', 'OFF', 'no', 'No', 'NO'):
        async with get_collection(articles,
                                  {'fields[article]': 'is-published',
                                   'filter[is-published]': val,
                                   'page[size]': 10},
                                  login=superuser_id) as json:
            assert isinstance(json['data'], list)
            assert len(json['data']) == 10
            for article in json['data']:
                assert_attribute(article, 'isPublished', lambda v: v is False)


#
# enum
#

@pytest.mark.asyncio
async def test_enum(users):
    for val in ('active', 'pending', 'active,pending'):
        async with get_collection(users,
                                  {'filter[status]': val,
                                   'page[size]': 5}) as json:
            assert isinstance(json['data'], list)
            assert len(json['data']) == 5
            for user in json['data']:
                assert_attribute(user, 'status',
                                 lambda v: v in val.split(',') if ',' in val else v == val)


#
# datetime
#


@pytest.mark.asyncio
async def test_datetime(users):
    for val in ('2019-09-01T00:00:00Z', '2019-09-01T00:00:00',
                '2019-09-01T00:00', '2019-09-01', '2019-09'):
        async with get_collection(users,
                                  {'filter[created-on:gt]': val,
                                   'page[size]': 5,
                                   'sort': 'created-on'}) as json:
            assert isinstance(json['data'], list)
            assert len(json['data']) == 5
            for user in json['data']:
                assert_attribute(user, 'createdOn',
                                 lambda v: parse_datetime(v) > dt.datetime(2019, 9, 1))


#
# aggregate filter
#


@pytest.mark.asyncio
async def test_aggregate_1(users):
    async with get_collection(users,
                              {'filter[article-count]': '5',
                               'fields[user]': 'article-count',
                               'page[size]': 5,
                               'sort': 'created-on'}) as json:
        assert isinstance(json['data'], list)
        assert len(json['data']) == 5
        for user in json['data']:
            assert_object(user, 'user')
            assert_attribute(user, 'articleCount', lambda v: v == 5)


@pytest.mark.asyncio
async def test_aggregate_2(users):
    async with get_collection(users,
                              {'filter[article-count:le]': '3',
                               'fields[user]': 'article-count',
                               'page[size]': 10}) as json:
        assert isinstance(json['data'], list)
        assert len(json['data']) == 10
        for user in json['data']:
            assert_object(user, 'user')
            assert_attribute(user, 'articleCount', lambda v: v <= 3)


@pytest.mark.asyncio
async def test_aggregate_3(articles, superuser_id):
    async with get_collection(articles,
                              {'filter[comment-count:gt]': '30',
                               'filter[keyword-count]': '3',
                               'fields[article]': 'comment-count,keyword-count',
                               'page[size]': 10},
                              login=superuser_id) as json:
        assert isinstance(json['data'], list)
        assert len(json['data']) == 10
        for article in json['data']:
            assert_object(article, 'article')
            assert_attribute(article, 'commentCount', lambda v: v > 30)
            assert_attribute(article, 'keywordCount', lambda v: v == 3)


#
# mixed filters
#


@pytest.mark.asyncio
async def test_mixed_1(users, superuser_id):
    async with get_collection(users,
                              {'filter[created-on:lt]': '2019-09-01',
                               'filter[status]': 'pending',
                               'filter[id:gt]': '100',
                               'filter[article-count]:le': '2',
                               'fields[user]': 'created-on,status,article-count',
                               'page[size]': 3},
                              login=superuser_id) as json:
        assert isinstance(json['data'], list)
        assert len(json['data']) > 0
        for user in json['data']:
            assert_object(user, 'user', lambda v: int(v) > 100)
            assert_attribute(user, 'status', lambda v: v == 'pending')
            assert_attribute(user, 'articleCount', lambda v: v <= 2)
            assert_attribute(user, 'createdOn',
                             lambda v: parse_datetime(v) < dt.datetime(2019, 9, 1))


#
# custom filter
#

@pytest.mark.asyncio
async def test_custom_1(articles, superuser_id):
    async with get_collection(articles,
                              {'filter[custom]': '15',
                               'fields[article]': 'title',
                               'page[size]': 5},
                              login=superuser_id) as json:
        assert isinstance(json['data'], list)
        assert len(json['data']) == 5
        for article in json['data']:
            assert_object(article, 'article')
            assert_attribute(article, 'title', lambda v: len(v) == 15)


@pytest.mark.asyncio
async def test_custom_2(articles, superuser_id):
    async with get_collection(articles,
                              {'filter[custom]': '15',
                               'filter[is-published]': 't',
                               'fields[article]': 'title,is-published'},
                              login=superuser_id) as json:
        assert isinstance(json['data'], list)
        assert len(json['data']) > 0
        for article in json['data']:
            assert_object(article, 'article')
            assert_attribute(article, 'title', lambda v: len(v) == 15)
            assert_attribute(article, 'isPublished', lambda v: v is True)


#
# relationship filters
#

@pytest.mark.dev
@pytest.mark.asyncio
async def test_relationship(articles, superuser_id):
    async with get_collection(articles,
                              {'filter[author:lt]': '15',
                               'filter[publisher]': 'none'},
                              login=superuser_id) as json:
        assert 'data' in json
