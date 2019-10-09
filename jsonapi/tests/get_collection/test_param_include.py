import pytest

from jsonapi.tests.util import *


# @pytest.mark.asyncio
# async def test_no_include(users, user_count, superuser_id):
#     for user_id in sample_integers(1, user_count, 10):
#         async with get_collection(users, user_id,
#                                   login=superuser_id) as json:
#             check_user(json['data'], lambda v: int(v) == user_id)
#             assert 'included' not in json


@pytest.mark.asyncio
async def test_one_to_one(users, user_count, superuser_id):
    user_id_list = sample_integers(1, user_count, 5)
    async with get_collection(users,
                              {'include': 'bio',
                               'filter[id]': ','.join(str(x) for x in user_id_list)},
                              login=superuser_id) as json:
        for user in json['data']:
            assert_object(user, 'user', lambda v: int(v) in user_id_list)
            check_included(json, user, 'bio', 'user-bio',
                           lambda size: size <= 1,
                           lambda v: int(v) in user_id_list)


@pytest.mark.asyncio
async def test_many_to_one(articles, article_count, superuser_id):
    article_id_list = sample_integers(1, article_count, 5)
    async with get_collection(articles,
                              {'include': 'author',
                               'filter[id]': ','.join(str(x) for x in article_id_list)},
                              login=superuser_id) as json:
        for article in json['data']:
            assert_object(article, 'article', lambda v: int(v) in article_id_list)
            check_included(json, article, 'author', 'user', lambda size: size == 1)


@pytest.mark.asyncio
async def test_one_to_many(users, user_count, superuser_id):
    user_id_list = sample_integers(1, user_count, 5)
    async with get_collection(users,
                              {'include': 'articles',
                               'filter[id]': ','.join(str(x) for x in user_id_list)},
                              login=superuser_id) as json:
        for user in json['data']:
            assert_object(user, 'user', lambda v: int(v) in user_id_list)
            check_included(json, user, 'articles', 'article', lambda size: size >= 0)


@pytest.mark.asyncio
async def test_many_to_many(articles, article_count, superuser_id):
    article_id_list = sample_integers(1, article_count, 5)
    async with get_collection(articles,
                              {'include': 'keywords',
                               'filter[id]': ','.join(str(x) for x in article_id_list)},
                              login=superuser_id) as json:
        for article in json['data']:
            assert_object(article, 'article', lambda v: int(v) in article_id_list)
            check_included(json, article, 'keywords', 'keyword', lambda size: size >= 0)
