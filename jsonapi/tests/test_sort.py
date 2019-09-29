import pytest
from jsonapi.tests.util import *


#
# single attribute sort
#


@pytest.mark.asyncio
async def test_sort_users_by_id_asc(cli, user_count):
    json = await get(cli, dict(url='/users/', sort='id'), 200)
    assert isinstance(json['data'], list)
    assert len(json['data']) == user_count
    for user_id, user in enumerate(json['data'], start=1):
        assert_object(user, 'user')
        assert user['id'] == str(user_id)


@pytest.mark.asyncio
async def test_sort_users_by_id_asc_plus_sign(cli, user_count):
    json = await get(cli, dict(url='/users/', sort='+id'), 200)
    assert isinstance(json['data'], list)
    assert len(json['data']) == user_count
    for user_id, user in enumerate(json['data'], start=1):
        assert_object(user, 'user')
        assert user['id'] == str(user_id)


@pytest.mark.asyncio
async def test_sort_users_by_id_desc(cli, user_count):
    json = await get(cli, dict(url='/users/', sort='-id'), 200)
    assert isinstance(json['data'], list)
    assert len(json['data']) == user_count
    for user_id, user in enumerate(reversed(json['data']), start=1):
        assert_object(user, 'user')
        assert user['id'] == str(user_id)


#
# aggregate sort
#

@pytest.mark.asyncio
async def test_sort_user_articles_keyword_count_1_as_superuser(cli, superuser_id):
    json = await get(cli, dict(
        url='/users/1/articles/',
        sort='keyword-count'
    ), 200, superuser_id)
    assert isinstance(json['data'], list)
    assert len(json['data']) > 0
    for article in json['data']:
        check_article(article)
        assert_attribute_does_not_exist(article, 'keyword-count')


@pytest.mark.asyncio
async def test_sort_user_articles_keyword_count_2_as_superuser(cli, superuser_id):
    json = await get(cli, dict(
        url='/users/1/articles/',
        fields=dict(article='title'),
        sort='keyword-count'
    ), 200, superuser_id)
    assert isinstance(json['data'], list)
    assert len(json['data']) > 0
    for article in json['data']:
        assert_object(article, 'article')
        assert_attribute(article, 'title')
        assert_attribute_does_not_exist(article, 'body')
        assert_attribute_does_not_exist(article, 'created_on')
        assert_attribute_does_not_exist(article, 'keyword-count')


@pytest.mark.asyncio
async def test_sort_user_articles_keyword_count_3_as_superuser(cli, superuser_id):
    json = await get(cli, dict(
        url='/users/1/articles/',
        fields=dict(article='title,keyword-count'),
        sort='keyword-count'
    ), 200, superuser_id)
    assert isinstance(json['data'], list)
    assert len(json['data']) > 0
    for article in json['data']:
        assert_object(article, 'article')
        assert_attribute(article, 'title')
        assert_attribute(article, 'keywordCount', lambda v: is_positive(v))
        assert_attribute_does_not_exist(article, 'created_on')
        assert_attribute_does_not_exist(article, 'body')


@pytest.mark.asyncio
async def test_sort_user_articles_keyword_count_4_as_superuser(cli, superuser_id):
    json = await get(cli, dict(
        url='/users/1/articles/',
        fields=dict(article='keyword-count'),
        sort='keyword-count'
    ), 200, superuser_id)
    assert isinstance(json['data'], list)
    assert len(json['data']) > 0
    for article in json['data']:
        assert_object(article, 'article')
        assert_attribute(article, 'keywordCount', lambda v: is_positive(v))
        assert_attribute_does_not_exist(article, 'title')
        assert_attribute_does_not_exist(article, 'created_on')
        assert_attribute_does_not_exist(article, 'body')


#
# multi attribute sort
#


