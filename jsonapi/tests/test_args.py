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
    assert args.in_include('author', parents=())


def test_include_2():
    args = RequestArguments({'include': 'author.articles'})
    assert args.in_include('author', parents=())
    assert args.in_include('articles', parents=('author',))


def test_include_3():
    args = RequestArguments(
        {'include': 'author.articles.comments.replies,author.articles.publisher'})
    assert args.in_include('author', parents=())
    assert args.in_include('articles', parents=('author',))
    assert args.in_include('comments', parents=('author', 'articles'))
    assert args.in_include('publisher', parents=('author', 'articles'))
    assert args.in_include('replies', parents=('author', 'articles', 'comments'))


def test_filter_1():
    assert RequestArguments.filter_parts('filter[author]') == ('author', None, None)
    assert RequestArguments.filter_parts('filter[author:eq]') == ('author', None, ':eq')
    assert RequestArguments.filter_parts('filter[author.id]') == ('author', '.id', None)
    assert RequestArguments.filter_parts('filter[author.id:eq]') == ('author', '.id', ':eq')
    assert RequestArguments.filter_parts('filter[author.:eq]') is None
    assert RequestArguments.filter_parts('filter[is-published]') == ('is-published', None, None)
