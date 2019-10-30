import pytest

from jsonapi.exc import APIError
from jsonapi.tests.util import *


@pytest.mark.asyncio
async def test_size(users, user_count):
    for step in (3, 10, 50):
        async with get_collection(users, {'page[size]': step}) as json:
            assert isinstance(json['data'], list)
            assert len(json['data']) == step
            for user in json['data']:
                assert_object(user, 'user')
            assert_meta(json, 'total', lambda v: v == user_count)
            assert 'totalFiltered' not in json['meta']


@pytest.mark.asyncio
async def test_size_number(users, user_count):
    for step in (3, 10, 50):
        user_id_list = list()
        for offset in range(0, 100, step):
            async with get_collection(users,
                                      {'page[size]': step,
                                       'page[number]': int(offset / step) + 1}) as json:
                assert isinstance(json['data'], list)
                assert len(json['data']) == step
                for user in json['data']:
                    assert_object(user, 'user', lambda v: v not in user_id_list)
                    user_id_list.append(user['id'])
                assert_meta(json, 'total', lambda v: v == user_count)
                assert 'totalFiltered' not in json['meta']


@pytest.mark.asyncio
async def test_number(users):
    with pytest.raises(APIError):
        await users.get_collection({'page[number]': 1})


@pytest.mark.asyncio
async def test_filter(users, user_count):
    async with get_collection(users,
                              {'page[size]': 3,
                               'filter[status]': 'active'}) as json:
        assert isinstance(json['data'], list)
        assert len(json['data']) == 3
        for user in json['data']:
            assert_object(user, 'user')
            assert_attribute(user, 'status', lambda v: v == 'active')
        assert_meta(json, 'total', lambda v: v == user_count)
        assert_meta(json, 'totalFiltered', lambda v: v < user_count)
