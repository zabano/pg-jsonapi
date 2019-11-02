import pytest

from jsonapi.tests.util import *


@pytest.mark.asyncio
async def test_no_fieldset(comments, superuser_id):
    for comment_id in sample_integers(1, 1000):
        async with get_related({}, comments, comment_id, 'article', login=superuser_id) as json:
            article = assert_object(json['data'], 'article')
            assert_attribute(article, 'title')
            assert_attribute(article, 'body')
            assert_attribute(article, 'is-published')
            assert_attribute(article, 'created-on')
            assert_attribute(article, 'updated-on')
            assert_no_attribute(article, 'comment-count')
            assert_no_attribute(article, 'keyword-count')


@pytest.mark.asyncio
async def test_fieldset(comments, superuser_id):
    for comment_id in sample_integers(1, 1000):
        async with get_related({
            'fields[article]': 'title'
        }, comments, comment_id, 'article', login=superuser_id) as json:
            article = assert_object(json['data'], 'article')
            assert_attribute(article, 'title')
            assert_no_attribute(article, 'body')
            assert_no_attribute(article, 'is-published')
            assert_no_attribute(article, 'created-on')
            assert_no_attribute(article, 'updated-on')
            assert_no_attribute(article, 'comment-count')
            assert_no_attribute(article, 'keyword-count')


@pytest.mark.asyncio
async def test_include_fieldset(comments, superuser_id):
    for comment_id in sample_integers(1, 1000):
        async with get_related({
            'include': 'author',
            'fields[article]': 'title,comment-count',
            'fields[user]': 'email'
        }, comments, comment_id, 'article', login=superuser_id) as json:
            article = assert_object(json['data'], 'article')
            assert_attribute(article, 'title')
            assert_no_attribute(article, 'body')
            assert_no_attribute(article, 'is-published')
            assert_no_attribute(article, 'created-on')
            assert_no_attribute(article, 'updated-on')
            assert_attribute(article, 'comment-count')
            assert_no_attribute(article, 'keyword-count')

            author = assert_relationship(article, 'author')
            assert_object(author, 'user')
            included = assert_included(json, author)
            assert_attribute(included, 'email')
            assert_no_attribute(included, 'first')
            assert_no_attribute(included, 'last')
            assert_no_attribute(included, 'name')
            assert_no_attribute(included, 'status')
            assert_no_attribute(included, 'created-on')
            assert_no_attribute(included, 'article-count')
