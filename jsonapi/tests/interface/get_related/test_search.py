import pytest

from jsonapi.exc import APIError
from jsonapi.tests.util import *


@pytest.mark.asyncio
async def test_simple(users, user_count):
    for user_id in sample_integers(1, user_count, 10):
        async with get_related(users, user_id, 'followers', search='John') as json:
            for user in assert_collection(json, 'user'):
                total = assert_meta(json, 'total')
                assert len(json['data']) <= total
                assert any('john' in val.lower() for val in (
                    assert_attribute(user, 'first'),
                    assert_attribute(user, 'last'),
                    assert_attribute(user, 'email')))


@pytest.mark.asyncio
async def test_page(users, user_count):
    for user_id in sample_integers(1, user_count, 10):
        async with get_related(users, user_id, 'followers',
                               {'page[size]': 5}, search='John') as json:
            for user in assert_collection(json, 'user', lambda size: size <= 5):
                total = assert_meta(json, 'total')
                search_total = assert_meta(json, 'searchTotal')
                assert total >= search_total >= len(json['data'])
                assert any('john' in val.lower() for val in (
                    assert_attribute(user, 'first'),
                    assert_attribute(user, 'last'),
                    assert_attribute(user, 'email')))


@pytest.mark.asyncio
async def test_prefix(users, user_count):
    for user_id in sample_integers(1, user_count, 10):
        async with get_related(users, user_id, 'followers', search='Al:*') as json:
            for user in assert_collection(json, 'user'):
                assert any('al' in val.lower() for val in (
                    assert_attribute(user, 'first'),
                    assert_attribute(user, 'last'),
                    assert_attribute(user, 'email')))


@pytest.mark.asyncio
async def test_filter(users):
    with pytest.raises(APIError):
        await users.get_related({'filter[first]': 'John'}, 1, 'followers', search='John:B')
