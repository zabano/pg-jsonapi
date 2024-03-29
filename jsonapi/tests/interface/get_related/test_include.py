import pytest

from jsonapi.tests.interface.util import check_include_multiple
from jsonapi.tests.util import *


@pytest.mark.asyncio
async def test_one_to_one(articles, article_count, superuser_id):
    for article_id in sample_integers(1, article_count, 10):
        async with get_related({'include': 'bio'}, articles, article_id, 'author', login=superuser_id) as json:
            assert_object(json['data'], 'user')
            check_included(json, json['data'], 'bio', 'user-bio', lambda size: size <= 1)


@pytest.mark.asyncio
async def test_many_to_one(users, user_count, superuser_id):
    for user_id in sample_integers(1, user_count, 10):
        async with get_related({'include': 'author'}, users, user_id, 'articles', login=superuser_id) as json:
            assert isinstance(json['data'], list)
            for article in json['data']:
                assert_object(article, 'article')
                check_included(json, article, 'author', 'user', lambda size: size == 1)


@pytest.mark.asyncio
async def test_one_to_many(articles, article_count, superuser_id):
    for article_id in sample_integers(1, article_count, 10):
        async with get_related({'include': 'articles'}, articles, article_id, 'author', login=superuser_id) as json:
            assert isinstance(json['data'], dict)
            assert_object(json['data'], 'user')
            check_included(json, json['data'], 'articles', 'article', lambda size: size >= 0)


@pytest.mark.asyncio
async def test_many_to_many(users, user_count, superuser_id):
    for user_id in sample_integers(1, user_count, 10):
        async with get_related({'include': 'keywords'}, users, user_id, 'articles', login=superuser_id) as json:
            assert isinstance(json['data'], list)
            for article in json['data']:
                assert_object(article, 'article')
                check_included(json, article, 'keywords', 'keyword', lambda size: size >= 0)


@pytest.mark.asyncio
async def test_multiple(articles, article_count, superuser_id):
    for article_id in sample_integers(1, article_count):
        async with get_related({
            'include': 'articles.comments.replies,'
                       'articles.keywords,'
                       'articles.author,'
                       'articles.publisher,'
                       'bio'
        }, articles, article_id, 'author', login=superuser_id) as json:
            check_include_multiple(json, json['data'])
