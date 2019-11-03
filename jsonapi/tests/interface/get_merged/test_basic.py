import pytest

from jsonapi.tests.util import *


@pytest.mark.dev
@pytest.mark.asyncio
async def test_intersection(articles, article_count, superuser_id):
    article_ids = sample_integers(1, article_count)
    async with get_merged({'include': 'articles'}, articles, article_ids, 'keywords',
                          login=superuser_id) as json:
        assert isinstance(json['data'], list)
        for keyword in json['data']:
            assert_object(keyword, 'keyword')


@pytest.mark.dev
@pytest.mark.asyncio
async def test_intersection_exclude(articles, article_count, superuser_id):
    article_ids = sample_integers(1, article_count, 5)
    async with get_merged({'include': 'articles'}, articles, article_ids, 'keywords',
                          exclude=article_ids[-2:], login=superuser_id) as json:
        assert isinstance(json['data'], list)
        for keyword in json['data']:
            assert_object(keyword, 'keyword')
