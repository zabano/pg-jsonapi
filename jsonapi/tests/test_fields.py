import pytest

from jsonapi.tests.util import *


@pytest.mark.asyncio
async def test_1(articles, user_1_id):
    async with get_collection(articles, {'fields[article]': 'title'}, login=user_1_id) as json:
        assert isinstance(json['data'], list)
        assert len(json['data']) > 0
        for article in json['data']:
            assert_object(article, 'article')
            assert_attribute(article, 'title', lambda v: isinstance(v, str) and len(v) > 0)
            assert_attribute_does_not_exist(article, 'body')
            assert_attribute_does_not_exist(article, 'isPublished')
            assert_attribute_does_not_exist(article, 'createdOn')
            assert_attribute_does_not_exist(article, 'updatedOn')


@pytest.mark.asyncio
async def test_2(articles, user_1_id):
    async with get_collection(articles,
                              {'include': 'author',
                               'fields[article]': 'title,created-on',
                               'fields[user]': 'email,article-count'},
                              login=user_1_id) as json:
        assert isinstance(json['data'], list)
        assert len(json['data']) > 0
        for article in json['data']:
            assert_object(article, 'article')
            assert_attribute(article, 'title', lambda v: isinstance(v, str) and len(v) > 0)
            assert_attribute(article, 'createdOn')
            assert_attribute_does_not_exist(article, 'body')
            assert_attribute_does_not_exist(article, 'isPublished')
            assert_attribute_does_not_exist(article, 'updatedOn')
        assert 'included' in json
        assert len(json['included']) > 0
        for author in json['included']:
            assert_object(author, 'user')
            assert_attribute(author, 'email')
            assert_attribute(author, 'articleCount', lambda v: is_size(v))
            assert_attribute_does_not_exist(author, 'first')
            assert_attribute_does_not_exist(author, 'last')
            assert_attribute_does_not_exist(author, 'name')
            assert_attribute_does_not_exist(author, 'status')
            assert_attribute_does_not_exist(author, 'createdOn')
