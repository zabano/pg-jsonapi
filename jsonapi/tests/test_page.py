import pytest
from math import ceil

from jsonapi.tests.util import *


@pytest.mark.asyncio
async def test_1(cli, superuser_id, user_count):
    for step in (3, 10, 50):
        for offset in range(0, 100, step):
            json = await get(cli, dict(
                url='/users/',
                fields=dict(user='id'),
                page=dict(size=step, number=int(offset / step) + 1),
                sort='+id'
            ), 200, superuser_id)
            assert isinstance(json['data'], list)
            assert len(json['data']) == step
            for user_id, user in enumerate(json['data'], start=offset + 1):
                assert_object(user, 'user', lambda v: int(v) == user_id)
            assert_meta(json, 'total', lambda v: v == user_count)
            assert 'totalFiltered' not in json['meta']


@pytest.mark.asyncio
async def test_2(cli, superuser_id, article_count):
    for step in (3, 5, 10, 20, 25, 50, 100):
        json = await get(cli, dict(
            url='/articles/',
            fields=dict(user='id'),
            page=dict(size=step, number=ceil(article_count / step)),  # last page
            sort='+id'
        ), 200, superuser_id)
        assert isinstance(json['data'], list)
        assert len(json['data']) == (article_count % step) or step
        assert_object(json['data'][-1], 'article', lambda v: int(v) == article_count)
        assert_meta(json, 'total', lambda v: v == article_count)
        assert 'totalFiltered' not in json['meta']


@pytest.mark.asyncio
async def test_3(cli, superuser_id, user_count):
    json = await get(cli, dict(
        url='/users/',
        fields=dict(user='id'),
        page=dict(size=3),  # no page requested, defaults to 1
        sort='+id'
    ), 200, superuser_id)
    assert isinstance(json['data'], list)
    assert len(json['data']) == 3
    for user_id, user in enumerate(json['data'], start=1):
        assert_object(user, 'user', lambda v: int(v) == user_id)
    assert_meta(json, 'total', lambda v: v == user_count)
    assert 'totalFiltered' not in json['meta']


@pytest.mark.asyncio
async def test_4(cli, superuser_id, user_count):
    json = await get(cli, dict(
        url='/users/',
        fields=dict(user='id'),
        page=dict(size=3),
        filter={'status': 'pending'}
    ), 200, superuser_id)
    assert isinstance(json['data'], list)
    assert len(json['data']) == 3
    assert_meta(json, 'total', lambda v: v == user_count)
    assert_meta(json, 'totalFiltered', lambda v: v < user_count)
