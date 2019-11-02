import pytest

from jsonapi.exc import Forbidden, NotFound
from jsonapi.tests.util import *


@pytest.mark.asyncio
async def test_no_args(users, user_count):
    for user_id in sample_integers(1, user_count):
        async with get_object({}, users, user_id) as json:
            check_user(json['data'], lambda v: int(v) == user_id)
            assert_no_attribute(json['data'], 'article-count')
            assert 'included' not in json


@pytest.mark.asyncio
async def test_forbidden(articles, article_count):
    for article_id in sample_integers(1, article_count, 3):
        with pytest.raises(Forbidden):
            await articles.get_object({}, article_id)


@pytest.mark.asyncio
async def test_not_found(articles, article_count):
    for inc in sample_integers(1, 100, 3):
        with pytest.raises(NotFound):
            await articles.get_object({}, article_count + inc)
