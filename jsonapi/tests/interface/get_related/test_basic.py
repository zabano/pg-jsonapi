import pytest

from jsonapi.tests.util import *


@pytest.mark.dev
@pytest.mark.asyncio
async def test_one_to_one(users, user_count, superuser_id):
    for user_id in sample_integers(1, user_count, 10):
        async with get_related({}, users, user_id, 'bio', login=superuser_id) as json:
            assert 'data' in json
            if json['data'] is not None:
                assert_object(json['data'], 'user-bio', lambda v: int(v) == user_id)


@pytest.mark.asyncio
async def test_many_to_one(articles, article_count, superuser_id):
    for article_id in sample_integers(1, article_count, 10):
        async with get_related({}, articles, article_id, 'author', login=superuser_id) as json:
            assert_object(json['data'], 'user')


@pytest.mark.asyncio
async def test_one_to_many(users, user_count, superuser_id):
    for user_id in sample_integers(1, user_count):
        async with get_related({}, users, user_id, 'articles', login=superuser_id) as json:
            assert isinstance(json['data'], list)
            for article in json['data']:
                assert_object(article, 'article')


@pytest.mark.asyncio
async def test_many_to_many(articles, article_count, superuser_id):
    for article_id in sample_integers(1, article_count, 10):
        async with get_related({}, articles, article_id, 'keywords', login=superuser_id) as json:
            assert isinstance(json['data'], list)
            for keyword in json['data']:
                assert_object(keyword, 'keyword')
