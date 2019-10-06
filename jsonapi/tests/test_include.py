import pytest

from jsonapi.tests.util import *


@pytest.mark.asyncio
async def test_1(users, user_1_id):
    async with get_object(users, user_1_id,
                          {'include': 'articles.comments.replies'},
                          login=user_1_id) as json:
        check_user(json['data'], lambda v: int(v) == user_1_id)
        assert_relationship(json['data'], 'articles', lambda size: size > 0)
        for article in get_relationship(json['data'], 'articles'):
            assert_object(article, 'article')
        assert 'included' in json
        for obj in json['included']:
            assert obj['type'] in ('article', 'comment', 'reply')
            if obj['type'] == 'article':
                check_article(obj)
                assert_relationship(obj, 'comments')
                for comment in get_relationship(obj, 'comments'):
                    assert_object(comment, 'comment')
            elif obj['type'] == 'comment':
                check_comment(obj)
                assert_relationship(obj, 'replies')
                for reply in get_relationship(obj, 'replies'):
                    assert_object(reply, 'reply')
            elif obj['type'] == 'reply':
                check_reply(obj)
                assert 'relationships' not in obj
