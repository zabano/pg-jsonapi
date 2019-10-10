import pytest

from jsonapi.tests.util import *
from jsonapi.tests.interface.util import check_include_multiple


@pytest.mark.asyncio
async def test_one_to_one(users, user_count, superuser_id):
    for user_id in sample_integers(1, user_count):
        async with get_object(users, user_id,
                              {'include': 'bio'},
                              login=superuser_id) as json:
            assert_object(json['data'], 'user', lambda v: int(v) == user_id)
            check_included(json, json['data'], 'bio', 'user-bio',
                           lambda size: size <= 1,
                           lambda v: int(v) == user_id)


@pytest.mark.asyncio
async def test_many_to_one(articles, article_count, superuser_id):
    for article_id in sample_integers(1, article_count, 10):
        async with get_object(articles, article_id,
                              {'include': 'author'},
                              login=superuser_id) as json:
            assert_object(json['data'], 'article', lambda v: int(v) == article_id)
            check_included(json, json['data'], 'author', 'user', lambda size: size == 1)


@pytest.mark.asyncio
async def test_one_to_many(users, user_count, superuser_id):
    for user_id in sample_integers(1, user_count):
        async with get_object(users, user_id,
                              {'include': 'articles'},
                              login=superuser_id) as json:
            assert_object(json['data'], 'user', lambda v: int(v) == user_id)
            check_included(json, json['data'], 'articles', 'article', lambda size: size >= 0)


@pytest.mark.asyncio
async def test_many_to_many(articles, article_count, superuser_id):
    for article_id in sample_integers(1, article_count, 10):
        async with get_object(articles, article_id,
                              {'include': 'keywords'},
                              login=superuser_id) as json:
            assert_object(json['data'], 'article', lambda v: int(v) == article_id)
            check_included(json, json['data'], 'keywords', 'keyword', lambda size: size >= 0)


@pytest.mark.asyncio
async def test_multiple(users, superuser_id):
    async with get_collection(users,
                              {'filter[bio:ne]': 'none',
                               'filter[articles:ne]': 'none',
                               'page[size]': 3},
                              login=superuser_id) as user_json:
        for user in user_json['data']:
            async with get_object(users, int(user['id']),
                                  {'include': 'articles.comments.replies,'
                                              'articles.keywords,'
                                              'articles.author,'
                                              'articles.publisher,'
                                              'bio'},
                                  login=superuser_id) as json:
                check_include_multiple(json, json['data'])
