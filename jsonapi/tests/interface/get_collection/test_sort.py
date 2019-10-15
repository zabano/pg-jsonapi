from collections import defaultdict

import pytest

from jsonapi.tests.util import *


@pytest.mark.asyncio
async def test_single(users, user_count):
    for attr_name in ('id', 'last', 'created-on'):
        for modifier in ('', '+', '-'):
            sort_spec = '{}{}'.format(modifier, attr_name)
            async with get_collection(users, {'sort': sort_spec}) as json:
                assert_sorted(json, attr_name, 'user', modifier == '-',
                              lambda size: size == user_count)


@pytest.mark.asyncio
async def test_exclude(users, user_count, superuser_id):
    for attr_name in ('last', 'created-on', 'article_count'):
        async with get_collection(users,
                                  {'fields[user]': 'email',
                                   'sort': attr_name},
                                  login=superuser_id) as json:
            for user in assert_collection(json, 'user', lambda size: size == user_count):
                assert_attribute(user, 'email')
                assert_no_attribute(user, attr_name)


@pytest.mark.asyncio
async def test_aggregate(users, user_count, superuser_id):
    async with get_collection(users,
                              {'sort': 'article-count'},
                              login=superuser_id) as json:
        for user in assert_collection(json, 'user', lambda size: size == user_count):
            assert_attribute(user, 'email')
            assert_attribute(user, 'createdOn')
            assert_attribute(user, 'name')
            assert_no_attribute(user, 'article-count')

    async with get_collection(users,
                              {'fields[user]': 'email',
                               'sort': 'article-count'},
                              login=superuser_id) as json:
        for user in assert_collection(json, 'user', lambda size: size == user_count):
            assert_attribute(user, 'email')
            assert_no_attribute(user, 'createdOn')
            assert_no_attribute(user, 'name')
            assert_no_attribute(user, 'article-count')

    async with get_collection(users,
                              {'fields[user]': 'email,article-count',
                               'sort': 'article-count'},
                              login=superuser_id) as json:
        for user in assert_collection(json, 'user', lambda size: size == user_count):
            assert_attribute(user, 'email')
            assert_no_attribute(user, 'createdOn')
            assert_no_attribute(user, 'name')
            assert_attribute(user, 'article-count', lambda v: is_size(v))
        assert_sorted(json, 'article-count', 'user',
                      validator_length=lambda size: size == user_count)

    async with get_collection(users,
                              {'fields[user]': 'article-count',
                               'sort': '-article-count'},
                              login=superuser_id) as json:
        for user in assert_collection(json, 'user', lambda size: size == user_count):
            assert_no_attribute(user, 'email')
            assert_no_attribute(user, 'createdOn')
            assert_no_attribute(user, 'name')
            assert_attribute(user, 'article-count', lambda v: is_size(v))
        assert_sorted(json, 'article-count', 'user', reverse=True,
                      validator_length=lambda size: size == user_count)


@pytest.mark.asyncio
async def test_relationship(users, user_count):
    async with get_collection(users,
                              {'include': 'bio',
                               'fields[user]': 'name,first,last',
                               'fields[user-bio]': 'birthday',
                               'sort': 'bio.birthday'}) as json:
        data = []
        for user in assert_collection(json, 'user', lambda size: size == user_count):
            bio = assert_relationship(user, 'bio')
            if bio is not None:
                included = assert_included(json, bio)
                birthday = assert_attribute(included, 'birthday')
                if birthday is not None:
                    data.append(birthday)
        assert data == sorted(data)


@pytest.mark.asyncio
async def test_multiple_1(users, user_count, superuser_id):
    async with get_collection(users,
                              {'fields[user]': 'article-count,last',
                               'sort': '-article-count,last'},
                              login=superuser_id) as json:
        data = list(assert_collection(json, 'user', lambda size: size == user_count))

        names_by_count = defaultdict(list)
        for user in data:
            names_by_count[assert_field(user, 'article-count')].append(
                assert_attribute(user, 'last'))

        article_counts = [assert_field(user, 'article-count') for user in data]
        assert article_counts == sorted(article_counts, reverse=True)
        for names in names_by_count.values():
            assert names == sorted(names)


@pytest.mark.asyncio
async def test_multiple_2(users, user_count, superuser_id):
    async with get_collection(users,
                              {'include': 'bio',
                               'fields[user]': 'article-count',
                               'sort': '-article-count,bio.birthday'},
                              login=superuser_id) as json:
        data = list(assert_collection(json, 'user', lambda size: size == user_count))
        birthdays_by_count = defaultdict(list)
        for user in data:
            bio = assert_relationship(user, 'bio')
            if bio:
                related = assert_included(json, bio)
                birthday = assert_attribute(related, 'birthday')
                if birthday:
                    birthdays_by_count[assert_attribute(user, 'article-count')].append(birthday)

        article_counts = [assert_attribute(user, 'article-count') for user in data]
        assert article_counts == sorted(article_counts, reverse=True)
        for birthdays in birthdays_by_count.values():
            assert birthdays == sorted(birthdays)
