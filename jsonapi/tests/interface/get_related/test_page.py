import pytest

from jsonapi.exc import APIError
from jsonapi.tests.util import *


@pytest.fixture()
async def users_with_5_articles(users, superuser_id):
    async with get_collection(users,
                              {'filter[article-count]': '5',
                               'filter[article.is-published]': 't',  # at least one is published
                               'page[size]': 3},
                              login=superuser_id) as json:
        return [int(user['id']) for user in json['data']]


@pytest.mark.asyncio
async def test_size(users, users_with_5_articles, superuser_id):
    for user_id in users_with_5_articles:
        for step in (3, 5, 10):
            async with get_related(users, user_id, 'articles',
                                   {'page[size]': step},
                                   login=superuser_id) as json:
                assert isinstance(json['data'], list)
                assert len(json['data']) <= step
                for article in json['data']:
                    assert_object(article, 'article')
                assert_meta(json, 'total', lambda v: v == 5)
                assert 'totalFiltered' not in json['meta']


@pytest.mark.asyncio
async def test_size_number(users, users_with_5_articles, superuser_id):
    for user_id in users_with_5_articles:
        for step in (3, 5, 10):
            article_id_list = list()
            for offset in range(0, 100, step):
                async with get_related(users, user_id, 'articles',
                                       {'page[size]': step,
                                        'page[number]': int(offset / step) + 1},
                                       login=superuser_id) as json:
                    assert isinstance(json['data'], list)
                    if offset == 0:
                        assert len(json['data']) == min(step, 5)
                    else:
                        assert len(json['data']) <= step
                    for article in json['data']:
                        assert_object(article, 'article', lambda v: v not in article_id_list)
                        article_id_list.append(article['id'])
                    assert_meta(json, 'total', lambda v: v == 5)
                    assert 'totalFiltered' not in json['meta']


@pytest.mark.asyncio
async def test_number(users):
    with pytest.raises(APIError):
        await users.get_related({'page[number]': 1}, 1, 'articles')


@pytest.mark.asyncio
async def test_filter(users, users_with_5_articles, superuser_id):
    for user_id in users_with_5_articles:
        async with get_related(users, user_id, 'articles',
                               {'page[size]': 3,
                                'filter[is-published]': 't'},
                               login=superuser_id) as json:
            assert isinstance(json['data'], list)
            assert 1 <= len(json['data']) <= 3
            for article in json['data']:
                assert_object(article, 'article')
                assert_attribute(article, 'isPublished', lambda v: v is True)
            assert_meta(json, 'total', lambda v: v == 5)
            assert_meta(json, 'totalFiltered', lambda v: v <= 5)
