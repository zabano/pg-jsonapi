import operator

import pytest

from jsonapi.tests.util import *


@pytest.mark.asyncio
async def test_int(users, authors, superuser_id):
    for user_id in authors[:5]:
        for op in ('', 'eq', 'lt', 'le', 'gt', 'ge'):
            filter_name = '{}:{}'.format('keyword-count', op) if op else 'keyword-count'
            compare = getattr(operator, op if op else 'eq')
            async with get_related(users, user_id, 'articles',
                                   {'fields[article]': 'keyword-count',
                                    'filter[{}]'.format(filter_name): '3'},
                                   login=superuser_id) as json:
                for article in assert_collection(json, 'article', lambda size: size <= 5):
                    total = assert_meta(json, 'total')
                    assert 0 < total <= 5
                    assert_meta(json, 'totalFiltered',
                                lambda v: v <= total and v == len(json['data']))
                    assert_object(article, 'article')
                    assert_attribute(article, 'keyword-count', lambda v: compare(int(v), 3))


@pytest.mark.asyncio
async def test_int_multiple(users, authors, superuser_id):
    for user_id in authors[:5]:
        async with get_related(users, user_id, 'articles',
                               {'filter[author]': ','.join(str(x) for x in authors)},
                               login=superuser_id) as json:
            for article in assert_collection(json, 'article', lambda size: size <= 5):
                total = assert_meta(json, 'total')
                assert 0 < total <= 5
                assert_meta(json, 'totalFiltered',
                            lambda v: v == total and v == len(json['data']))
                assert_object(article, 'article')


@pytest.mark.asyncio
async def test_int_range(users, user_count, superuser_id):
    for user_id in sample_integers(1, user_count):
        for (filter_spec, id_list) in (
                ('<100,>=200,325', list(range(1, 100)) + list(range(200, 326))),
                ('>=900,<500', list(range(1, 500)) + list(range(900, user_count + 1)))):
            async with get_related(users, user_id, 'followers',
                                   {'fields[user]': 'id', 'filter[id]': filter_spec},
                                   login=superuser_id) as json:
                for user in assert_collection(json, 'user', lambda size: 0 < size <= len(id_list)):
                    assert_object(user, 'user', lambda v: int(v) in id_list)


@pytest.mark.asyncio
async def test_bool(users, superuser_id, authors):
    for user_id in authors[:5]:
        async with get_related(users, user_id, 'articles',
                               {'fields[article]': 'is-published',
                                'filter[is-published]': 't'},
                               login=superuser_id) as json:
            for article in assert_collection(json, 'article'):
                assert_attribute(article, 'is-published', lambda v: v is True)
        async with get_related(users, user_id, 'articles',
                               {'fields[article]': 'is-published',
                                'filter[is-published]': 'f'},
                               login=superuser_id) as json:
            for article in assert_collection(json, 'article'):
                assert_attribute(article, 'is-published', lambda v: v is False)


@pytest.mark.asyncio
async def test_enum(users, user_count):
    for user_id in sample_integers(1, user_count):
        for val in ('active', 'pending', 'active,pending'):
            async with get_related(users, user_id, 'followers', {'filter[status]': val}) as json:
                total = assert_meta(json, 'total')
                total_filtered = assert_meta(json, 'totalFiltered')
                assert 0 <= total_filtered <= total
                for user in assert_collection(json, 'user', lambda size: size == total_filtered):
                    assert_attribute(user, 'status',
                                     lambda v: v in val.split(',') if ',' in val else v == val)


@pytest.mark.asyncio
async def test_datetime(users, user_count):
    for user_id in sample_integers(1, user_count):
        for val in ('2019-10-01T00:00:00Z', '2019-10-01T00:00:00',
                    '2019-10-01T00:00', '2019-10-01', '2019-10'):
            async with get_related(users, user_id, 'followers',
                                   {'filter[created-on:gt]': val,
                                    'sort': 'created-on'}) as json:
                total = assert_meta(json, 'total', lambda v: int(v) > 0)
                total_filtered = assert_meta(json, 'totalFiltered')
                assert 0 < total_filtered <= total
                for user in assert_collection(json, 'user', lambda size: size == total_filtered):
                    assert_attribute(user, 'created-on',
                                     lambda v: parse_datetime(v) > dt.datetime(2019, 10, 1))

        async with get_related(users, user_id, 'followers',
                               {'filter[created-on]': '>2018-08,<2018-09,'
                                                      '>2019-08,<2019-09'}) as json:
            total = assert_meta(json, 'total', lambda v: int(v) > 0)
            total_filtered = assert_meta(json, 'totalFiltered')
            assert 0 < total_filtered <= total
            for user in assert_collection(json, 'user', lambda size: size > 0):
                assert_attribute(
                    user, 'created-on',
                    lambda v: (dt.datetime(2018, 8, 1) < parse_datetime(v)
                               < dt.datetime(2018, 9, 1)) or
                              (dt.datetime(2019, 8, 1) < parse_datetime(v)
                               < dt.datetime(2019, 9, 1)))


@pytest.mark.asyncio
async def test_aggregate(users, authors, superuser_id):
    for user_id in authors[:5]:
        async with get_related(users, user_id, 'articles',
                               {'filter[comment-count:gt]': '10',
                                'filter[keyword-count:le]': '5',
                                'fields[article]': 'comment-count,keyword-count'},
                               login=superuser_id) as json:
            total = assert_meta(json, 'total', lambda v: int(v) > 0)
            total_filtered = assert_meta(json, 'totalFiltered')
            assert 0 < total_filtered <= total
            for article in assert_collection(json, 'article', lambda size: size == total_filtered):
                assert_object(article, 'article')
                assert_attribute(article, 'comment-count', lambda v: v > 10)
                assert_attribute(article, 'keyword-count', lambda v: v <= 5)


@pytest.mark.asyncio
async def test_custom(users, authors, superuser_id):
    for user_id in authors[:5]:
        async with get_related(users, user_id, 'articles',
                               {'filter[custom:le]': '200',
                                'fields[article]': 'title,is-published'},
                               login=superuser_id) as json:
            total = assert_meta(json, 'total', lambda v: int(v) > 0)
            total_filtered = assert_meta(json, 'totalFiltered')
            assert 0 < total_filtered <= total
            for article in assert_collection(json, 'article', lambda size: size == total_filtered):
                assert_object(article, 'article')
                assert_attribute(article, 'title', lambda v: len(v) <= 200)


@pytest.mark.asyncio
async def test_relationship(users, authors, superuser_id):
    for user_id in authors[:10]:
        for args in [{'filter[publisher]': 'none'},
                     {'filter[publisher:eq]': 'none'},
                     {'filter[publisher.id]': 'none'},
                     {'filter[publisher.id:eq]': 'none'}]:
            async with get_related(users, user_id, 'articles',
                                   args, login=superuser_id) as json:
                assert_meta(json, 'total', lambda v: int(v) > 0)
                total_filtered = assert_meta(json, 'totalFiltered')
                if total_filtered > 0:
                    for article in assert_collection(json, 'article',
                                                     lambda size: size == total_filtered):
                        assert_object(article, 'article')
                        assert_attribute(article, 'isPublished', lambda v: v is False)

        async with get_related(users, user_id, 'articles',
                               {'include': 'author',
                                'fields[user]': 'article-count',
                                'filter[author.article-count:eq]': '3',
                                'filter[publisher:ne]': 'none'},
                               login=superuser_id) as json:
            for article in assert_collection(json, 'article'):
                assert_attribute(article, 'is-published', lambda v: v is True)
                author = assert_included(json, assert_relationship(article, 'author'))
                assert_attribute(author, 'article-count', lambda v: v == 3)
