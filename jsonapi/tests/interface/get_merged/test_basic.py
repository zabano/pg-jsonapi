import pytest

from jsonapi.tests.util import *


@pytest.mark.asyncio
async def test_intersection(articles, superuser_id):
    async with get_collection({'filter[keywords]': '1'}, articles, login=superuser_id) as article_json:
        async with get_merged({
            'include': 'articles'
        }, articles, [int(rec['id']) for rec in article_json['data']], 'keywords', login=superuser_id) as json:
            for keyword in assert_collection(json, 'keyword', lambda s: s > 0):
                assert_object(keyword, 'keyword')


@pytest.mark.asyncio
async def test_union(articles, article_count, superuser_id):
    article_ids = sample_integers(1, article_count, 5)
    async with get_merged({
        'merge': '>=1',
    }, articles, article_ids, 'keywords', login=superuser_id) as json:
        for keyword in assert_collection(json, 'keyword', lambda s: s > 0):
            assert_object(keyword, 'keyword')

