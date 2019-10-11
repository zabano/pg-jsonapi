from jsonapi.tests.util import assert_object, assert_relationship, assert_included


def check_include_multiple(json, obj):
    assert_object(obj, 'user')
    for bio in assert_relationship(obj, 'bio'):
        assert_object(bio, 'user-bio')
        assert_included(json, bio)
    for article in assert_relationship(obj, 'articles'):
        assert_object(article, 'article')
        assert_included(json, article)
    assert 'included' in json
    for included in json['included']:
        if included['type'] == 'article':
            for author in assert_relationship(included, 'author'):
                assert_object(author, 'user')
                assert_included(json, author)
            for publisher in assert_relationship(included, 'publisher'):
                assert_object(publisher, 'user')
                assert_included(json, publisher)
            for comment in assert_relationship(included, 'comments'):
                assert_object(comment, 'comment')
                assert_included(json, comment)
            for keyword in assert_relationship(included, 'keywords'):
                assert_object(keyword, 'keyword')
                assert_included(json, keyword)
        elif included['type'] == 'comment':
            for reply in assert_relationship(included, 'replies'):
                assert_object(reply, 'reply')
                assert_included(json, reply)
