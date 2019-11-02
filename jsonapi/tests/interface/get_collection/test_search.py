import pytest

from jsonapi.exc import APIError
from jsonapi.tests.util import *


@pytest.mark.asyncio
async def test_simple(users):
    async with get_collection({}, users, search='John') as json:
        for user in assert_collection(json, 'user', lambda size: size > 0):
            total = assert_meta(json, 'total')
            assert 0 < len(json['data']) <= total
            assert any('john' in val.lower() for val in (
                assert_attribute(user, 'first'),
                assert_attribute(user, 'last'),
                assert_attribute(user, 'email')))


@pytest.mark.asyncio
async def test_page(users):
    async with get_collection({'page[size]': 5}, users, search='John') as json:
        for user in assert_collection(json, 'user', lambda size: 0 < size <= 5):
            total = assert_meta(json, 'total')
            search_total = assert_meta(json, 'searchTotal')
            assert total >= search_total >= len(json['data'])
            assert any('john' in val.lower() for val in (
                assert_attribute(user, 'first'),
                assert_attribute(user, 'last'),
                assert_attribute(user, 'email')))


@pytest.mark.asyncio
async def test_prefix(users):
    async with get_collection({}, users, search='Ann:*') as json:
        for user in assert_collection(json, 'user', lambda size: size > 0):
            total = assert_meta(json, 'total')
            assert 0 < len(json['data']) <= total
            assert any('ann' in val.lower() for val in (
                assert_attribute(user, 'first'),
                assert_attribute(user, 'last'),
                assert_attribute(user, 'email')))


@pytest.mark.asyncio
async def test_complex(users):
    async with get_collection({}, users, search='Al:B* & !Alan:B') as json:
        for user in assert_collection(json, 'user', lambda size: size > 0):
            name = assert_attribute(user, 'name')
            assert 'alan' not in name.lower().split()


@pytest.mark.asyncio
async def test_filter(users):
    with pytest.raises(APIError):
        await users.get_collection({'filter[first]': 'John'}, search='John:B')
