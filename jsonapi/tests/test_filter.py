import pytest

from jsonapi.tests.util import *


#
# int (single)
#


@pytest.mark.asyncio
async def test_filter_int_as_superuser(cli, superuser_id):
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
async def test_filter_int_eq_as_superuser(cli, superuser_id):
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
async def test_filter_int_ne_as_superuser(cli, superuser_id):
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
async def test_filter_int_lt_as_superuser(cli, superuser_id):
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
async def test_filter_int_le_as_superuser(cli, superuser_id):
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
async def test_filter_int_gt_as_superuser(cli, superuser_id):
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
async def test_filter_int_ge_as_superuser(cli, superuser_id):
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
async def test_filter_int_multiple_1_as_superuser(cli, superuser_id):
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
async def test_filter_int_multiple_2_as_superuser(cli, superuser_id):
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
async def test_filter_bool_1_as_superuser(cli, superuser_id):
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
async def test_filter_bool_2_as_superuser(cli, superuser_id):
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
