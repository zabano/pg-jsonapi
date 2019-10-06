from math import ceil

import pytest

from jsonapi.tests.util import *


@pytest.mark.asyncio
async def test_1(users, user_count):
    for step in (3, 10, 50):
        for offset in range(0, 100, step):
            async with get_collection(users,
                                      {'fields[user]': 'id',
                                       'sort': 'id',
                                       'page[size]': step,
                                       'page[number]': int(offset / step) + 1}) as json:
                assert isinstance(json['data'], list)
                assert len(json['data']) == step
                for user_id, user in enumerate(json['data'], start=offset + 1):
                    assert_object(user, 'user', lambda v: int(v) == user_id)
                assert_meta(json, 'total', lambda v: v == user_count)
                assert 'totalFiltered' not in json['meta']


@pytest.mark.asyncio
async def test_2(articles, article_count, superuser_id):
    for step in (3, 5, 10, 20, 25, 50, 100):
        async with get_collection(articles,
                                  {'fields[user]': 'id',
                                   'sort': 'id',
                                   'page[size]': step,
                                   'page[number]': ceil(article_count / step)},
                                  login=superuser_id) as json:
            assert isinstance(json['data'], list)
            assert len(json['data']) == (article_count % step) or step
            assert_object(json['data'][-1], 'article', lambda v: int(v) == article_count)
            assert_meta(json, 'total', lambda v: v == article_count)
            assert 'totalFiltered' not in json['meta']


@pytest.mark.asyncio
async def test_3(users, user_count):
    async with get_collection(users,
                              {'fields[user]': 'id',
                               'sort': 'id',
                               'page[size]': 3}) as json:
        assert isinstance(json['data'], list)
        assert len(json['data']) == 3
        for user_id, user in enumerate(json['data'], start=1):
            assert_object(user, 'user', lambda v: int(v) == user_id)
        assert_meta(json, 'total', lambda v: v == user_count)
        assert 'totalFiltered' not in json['meta']


@pytest.mark.asyncio
async def test_4(users, user_count):
    async with get_collection(users,
                              {'fields[user]': 'id',
                               'page[size]': 3,
                               'filter[status]': 'pending'}) as json:
        assert isinstance(json['data'], list)
        assert len(json['data']) == 3
        assert_meta(json, 'total', lambda v: v == user_count)
        assert_meta(json, 'totalFiltered', lambda v: v < user_count)
