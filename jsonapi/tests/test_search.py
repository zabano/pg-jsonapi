import pytest

from jsonapi.tests.util import *


@pytest.mark.dev
@pytest.mark.asyncio
async def test_1(users, articles, user_count, article_count):
    async with search({}, 'John', users, articles) as json:
        assert_meta(json, 'total', lambda v: v == user_count + article_count)
        assert_meta(json, 'searchType', lambda v: (v['user']['total'] == user_count and
                                                   v['article']['total'] == article_count))
        assert_collection(json, 'user')


@pytest.mark.asyncio
async def test_2(users, articles, user_1_id):
    async with search({}, 'John', users, articles, login=user_1_id) as json:
        assert_collection(json, ('user', 'article'))


@pytest.mark.asyncio
async def test_3(users, articles, superuser_id):
    async with search({}, 'John', users, articles, login=superuser_id) as json:
        assert_collection(json, ('user', 'article'))


def assert_bio(json, user):
    bio = assert_relationship(user, 'bio')
    if bio:
        included = assert_included(json, bio)
        if included:
            assert_attribute(included, 'birthday')
            assert_attribute(included, 'age')
            assert_no_attribute(included, 'summary')


def assert_user(json, user):
    assert_attribute(user, 'email')
    assert_attribute(user, 'name')
    assert_no_attribute(user, 'created-on')
    assert_no_attribute(user, 'first')
    assert_no_attribute(user, 'last')
    assert_bio(json, user)


@pytest.mark.skip
@pytest.mark.asyncio
async def test_4(users, articles, superuser_id):
    async with search({
        'include[user]': 'bio',
        'include[article]': 'keywords,author.bio,publisher.bio',
        'fields[user]': 'name,email',
        'fields[user-bio]': 'birthday,age',
        'fields[article]': 'title'
    }, 'John', users, articles, login=superuser_id) as json:
        for obj in assert_collection(json, ('user', 'article')):
            if obj['type'] == 'user':
                assert_user(json, obj)
            else:
                author = assert_included(json, assert_relationship(obj, 'author'))
                assert_user(json, author)

                publisher = assert_relationship(obj, 'publisher')
                if publisher:
                    included = assert_included(json, publisher)
                    assert_user(json, included)
                for keyword in assert_relationship(obj, 'keywords'):
                    assert_included(json, keyword)
