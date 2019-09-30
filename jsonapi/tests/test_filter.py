import pytest

from jsonapi.db.util import parse_datetime
from jsonapi.tests.util import *


#
# int (single)
#


@pytest.mark.asyncio
async def test_filter_int(cli, superuser_id):
    json = await get(cli, dict(
        url='/articles/',
        fields=dict(article='id'),
        filter={'id': '5'},
        page=dict(size=10)
    ), 200, superuser_id)
    assert isinstance(json['data'], list)
    assert len(json['data']) == 1
    for article in json['data']:
        assert_object(article, 'article', lambda v: int(v) == 5)


@pytest.mark.asyncio
async def test_filter_int_eq(cli, superuser_id):
    json = await get(cli, dict(
        url='/articles/',
        filter={'id:eq': '5'},
        page=dict(size=10)
    ), 200, superuser_id)
    assert isinstance(json['data'], list)
    assert len(json['data']) == 1
    for article in json['data']:
        assert_object(article, 'article', lambda v: int(v) == 5)


@pytest.mark.asyncio
async def test_filter_int_ne(cli, superuser_id):
    json = await get(cli, dict(
        url='/articles/',
        filter={'id:ne': '5'},
        page=dict(size=10)
    ), 200, superuser_id)
    assert isinstance(json['data'], list)
    assert len(json['data']) == 10
    for article in json['data']:
        assert_object(article, 'article', lambda v: v != '5')


@pytest.mark.asyncio
async def test_filter_int_lt(cli, superuser_id):
    json = await get(cli, dict(
        url='/articles/',
        filter={'id:lt': '5'},
        page=dict(size=10)
    ), 200, superuser_id)
    assert isinstance(json['data'], list)
    assert len(json['data']) == 4
    for article in json['data']:
        assert_object(article, 'article', lambda v: int(v) < 5)


@pytest.mark.asyncio
async def test_filter_int_le(cli, superuser_id):
    json = await get(cli, dict(
        url='/articles/',
        filter={'id:le': '5'},
        page=dict(size=10)
    ), 200, superuser_id)
    assert isinstance(json['data'], list)
    assert len(json['data']) == 5
    for article in json['data']:
        assert_object(article, 'article', lambda v: int(v) <= 5)


@pytest.mark.asyncio
async def test_filter_int_gt(cli, superuser_id):
    json = await get(cli, dict(
        url='/articles/',
        filter={'id:gt': '5'},
        page=dict(size=10)
    ), 200, superuser_id)
    assert isinstance(json['data'], list)
    assert len(json['data']) == 10
    for article in json['data']:
        assert_object(article, 'article', lambda v: int(v) > 5)


@pytest.mark.asyncio
async def test_filter_int_ge(cli, superuser_id):
    json = await get(cli, dict(
        url='/articles/',
        filter={'id:ge': '5'},
        page=dict(size=10)
    ), 200, superuser_id)
    assert isinstance(json['data'], list)
    assert len(json['data']) == 10
    for article in json['data']:
        assert_object(article, 'article', lambda v: int(v) >= 5)


#
# integer (multiple)
#

@pytest.mark.asyncio
async def test_filter_int_multiple_1(cli, superuser_id):
    json = await get(cli, dict(
        url='/articles/',
        fields=dict(article='id'),
        filter=dict(id='1,2,3,4,5,6,7,8,9,10')
    ), 200, superuser_id)
    assert isinstance(json['data'], list)
    assert len(json['data']) == 10
    for article in json['data']:
        assert_object(article, 'article', lambda v: int(v) <= 10)


@pytest.mark.asyncio
async def test_filter_int_multiple_2(cli, superuser_id):
    json = await get(cli, dict(
        url='/articles/',
        filter={'id': '<4,6,>=8'},
        sort='id',
        page=dict(size=7)
    ), 200, superuser_id)
    assert isinstance(json['data'], list)
    assert len(json['data']) == 7
    for article in json['data']:
        assert_object(article, 'article', lambda v: int(v) in (1, 2, 3, 6, 8, 9, 10))


#
# bool
#


@pytest.mark.asyncio
async def test_filter_bool_1(cli, superuser_id):
    for val in ('t', 'T', 'true', 'True', 'TRUE', '1', 'on', 'On', 'ON'):
        json = await get(cli, dict(
            url='/articles/',
            filter={'is-published': val},
            page=dict(size=10)
        ), 200, superuser_id)
        assert isinstance(json['data'], list)
        assert len(json['data']) == 10
        for article in json['data']:
            assert_attribute(article, 'isPublished', lambda v: v is True)


@pytest.mark.asyncio
async def test_filter_bool_2(cli, superuser_id):
    for val in ('f', 'F', 'false', 'False', 'FALSE', '0', 'off', 'Off', 'OFF'):
        json = await get(cli, dict(
            url='/articles/',
            filter={'is-published': val},
            page=dict(size=10)
        ), 200, superuser_id)
        assert isinstance(json['data'], list)
        assert len(json['data']) == 10
        for article in json['data']:
            assert_attribute(article, 'isPublished', lambda v: v is False)


#
# bool
#

@pytest.mark.asyncio
async def test_filter_enum(cli, superuser_id):
    for val in ('active', 'pending', 'active,pending'):
        json = await get(cli, dict(
            url='/users/',
            filter={'status': val},
            page=dict(size=5)
        ), 200, superuser_id)
        assert isinstance(json['data'], list)
        assert len(json['data']) == 5
        for user in json['data']:
            assert_attribute(user, 'status',
                             lambda v: v in val.split(',') if ',' in val else v == val)


#
# datetime
#


@pytest.mark.asyncio
async def test_filter_datetime(cli, superuser_id):
    for val in ('2019-09-01T00:00:00Z', '2019-09-01T00:00:00',
                '2019-09-01T00:00', '2019-09-01', '2019-09'):
        json = await get(cli, dict(
            url='/users/',
            filter={'created-on:gt': val},
            page=dict(size=5),
            sort='created-on'
        ), 200, superuser_id)
        assert isinstance(json['data'], list)
        assert len(json['data']) == 5
        for user in json['data']:
            assert_attribute(user, 'createdOn',
                             lambda v: parse_datetime(v) > dt.datetime(2019, 9, 1))


#
# aggregate filter
#


@pytest.mark.asyncio
async def test_filter_aggregate_1(cli, superuser_id):
    json = await get(cli, dict(
        url='/users/',
        filter={'article-count': 5},
        fields=dict(user='article-count'),
        page=dict(size=5),
    ), 200, superuser_id)
    assert isinstance(json['data'], list)
    assert len(json['data']) == 5
    for user in json['data']:
        assert_object(user, 'user')
        assert_attribute(user, 'articleCount', lambda v: v == 5)


@pytest.mark.asyncio
async def test_filter_aggregate_2(cli, superuser_id):
    json = await get(cli, dict(
        url='/users/',
        filter={'article-count:le': 3},
        fields=dict(user='article-count'),
        page=dict(size=10),
    ), 200, superuser_id)
    assert isinstance(json['data'], list)
    assert len(json['data']) == 10
    for user in json['data']:
        assert_object(user, 'user')
        assert_attribute(user, 'articleCount', lambda v: v <= 3)


@pytest.mark.asyncio
async def test_filter_aggregate_3(cli, superuser_id):
    json = await get(cli, dict(
        url='/articles/',
        filter={'comment-count:gt': 30, 'keyword-count': 3},
        fields=dict(article='comment-count,keyword-count'),
        page=dict(size=10),
    ), 200, superuser_id)
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
async def test_filter_mixed_1(cli, superuser_id):
    json = await get(cli, dict(
        url='/users/',
        filter={
            'created-on:lt': '2019-09-01',
            'status': 'pending',
            'id:gt': 100,
            'article-count:le': 2
        },
        fields=dict(user='created-on,status,article-count'),
        page=dict(size=3),
    ), 200, superuser_id)
    assert isinstance(json['data'], list)
    assert len(json['data']) == 3
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
async def test_filter_custom_1(cli, superuser_id):
    json = await get(cli, dict(
        url='/articles/',
        filter={'custom': 15},
        fields=dict(article='title'),
        page=dict(size=5),
    ), 200, superuser_id)
    assert isinstance(json['data'], list)
    assert len(json['data']) == 5
    for article in json['data']:
        assert_object(article, 'article')
        assert_attribute(article, 'title', lambda v: len(v) == 15)


@pytest.mark.asyncio
async def test_filter_custom_2(cli, superuser_id):
    json = await get(cli, dict(
        url='/articles/',
        filter={'custom': 15, 'is-published': False},
        fields=dict(article='title,is-published')
    ), 200, superuser_id)
    assert isinstance(json['data'], list)
    assert len(json['data']) == 1
    for article in json['data']:
        assert_object(article, 'article')
        assert_attribute(article, 'title', lambda v: len(v) == 15)
        assert_attribute(article, 'isPublished', lambda v: v is False)
