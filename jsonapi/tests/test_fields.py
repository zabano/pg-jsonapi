import pytest

from jsonapi.tests.util import *


@pytest.mark.asyncio
async def test_fields_get_articles_as_user_1(cli, user_1_id):
    qs = 'fields[article]=title'
    json = await get(cli, '/articles/?{}'.format(qs), 200, user_1_id)
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
async def test_fields_get_articles_and_authors_as_user_1(cli, user_1_id):
    qs = 'include=author&fields[article]=title,created-on&fields[user]=email,article-count'
    json = await get(cli, '/articles/?{}'.format(qs), 200, user_1_id)
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
        assert_attribute(author, 'articleCount', lambda v: is_positive(v))
        assert_attribute_does_not_exist(author, 'status')
        assert_attribute_does_not_exist(author, 'createdOn')
