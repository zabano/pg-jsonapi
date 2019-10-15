from jsonapi.args import RequestArguments


def test_fields_1():
    args = RequestArguments({'fields[user]': 'email,name'})
    assert 'user' in args.fields.keys()
    assert args.fieldset_defined('user')
    assert not args.fieldset_defined('article')
    assert not args.in_fieldset('article', 'body')
    assert 'name' in args.fields['user']
    assert args.in_fieldset('user', 'id')
    assert args.in_fieldset('user', 'email')


def test_fields_2():
    args = RequestArguments({'fields[user]': 'email,name',
                             'fields[article]': 'title,body'})
    assert 'user' in args.fields.keys()
    assert args.fieldset_defined('user')
    assert 'article' in args.fields.keys()
    assert args.fieldset_defined('article')
    assert args.in_fieldset('user', 'id')
    assert args.in_fieldset('user', 'email')
    assert args.in_fieldset('user', 'name')
    assert args.in_fieldset('article', 'id')
    assert args.in_fieldset('article', 'body')
    assert args.in_fieldset('article', 'title')


def test_include_1():
    args = RequestArguments({'include': 'author'})
    assert 'author' in args.include.keys()
    assert args.include['author'] == dict()


def test_include_2():
    args = RequestArguments({'include': 'author.articles'})
    assert 'author' in args.include.keys()
    assert 'articles' in args.include['author'].keys()


def test_include_3():
    args = RequestArguments(
        {'include': 'author.articles.comments.replies,author.articles.publisher'})
    assert 'author' in args.include.keys()
    author = args.include['author']
    assert 'articles' in author.keys()
    articles = author['articles']
    assert 'publisher' in articles.keys()
    assert 'comments' in articles.keys()
    comments = articles['comments']
    assert 'replies' in comments.keys()
    assert articles['publisher'] == dict()
    assert comments['replies'] == dict()


def test_filter_1():
    assert RequestArguments.filter_parts('filter[author]') == ('author', None, None)
    assert RequestArguments.filter_parts('filter[author:eq]') == ('author', None, ':eq')
    assert RequestArguments.filter_parts('filter[author.id]') == ('author', '.id', None)
    assert RequestArguments.filter_parts('filter[author.id:eq]') == ('author', '.id', ':eq')
    assert RequestArguments.filter_parts('filter[author.:eq]') is None
    assert RequestArguments.filter_parts('filter[is-published]') == ('is-published', None, None)
