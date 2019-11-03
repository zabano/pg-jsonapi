import re

from inflection import underscore

from jsonapi.db.filter import MODIFIERS
from jsonapi.exc import Error


class AttributePath:

    def __init__(self, dot_path):
        self.names = tuple(underscore(name) for name in dot_path.split('.'))

    def __len__(self):
        return len(self.names)

    def __iter__(self):
        return iter(self.names)

    def __getitem__(self, index):
        return self.names[index]

    def exists(self, name, parents=tuple()):
        return tuple((*parents, name)) == self.names[:1 + len(parents)]

    def __repr__(self):
        return '{}({})'.format(self.__class__.__name__, '.'.join(self.names))


class FieldArgument:

    def __init__(self, spec, value):

        try:
            self.type = re.search(r'^fields\[([-_\w]+)\]$', spec).group(1)
        except AttributeError:
            raise Error('invalid fieldset spec: {!r}'.format(spec))
        else:
            self.names = tuple(set(underscore(x) for x in value.split(',') + ['id']))

    def __len__(self):
        return len(self.names)

    def __iter__(self):
        return iter(self.names)

    def __repr__(self):
        return '{}({}:{})'.format(self.__class__.__name__, self.type, '.'.join(self.names))


class SortArgument:

    def __init__(self, value):
        try:
            order, dot_path = re.search(r'([-+]?)(.+)', value).groups()
        except AttributeError:
            raise Error('invalid sort argument: {!r}'.format(value))
        else:
            self.desc = order == '-'
            self.path = AttributePath(dot_path)

    def __repr__(self):
        return '{}({!r}, desc={!r})'.format(self.__class__.__name__, self.path, self.desc)


class FilterArgument:

    def __init__(self, spec, value):

        try:
            dot_path, op = re.match(r'filter\[([-_.\w]+)(:[-_\w]+)?\]', spec).groups()
        except AttributeError:
            raise Error('invalid filter parameter: {!r}'.format(spec))
        else:
            self.path = AttributePath(dot_path)
            self.operator = op.strip(':') if op else 'eq'
            self.value = value

    def __repr__(self):
        return '{}({!r}, op={!r}, val={!r})'.format(
            self.__class__.__name__, self.path, self.operator,
            self.value[:10] + '...' if len(self.value) > 10 else self.value)


class PageArgument:

    def __init__(self, size, number):

        self.limit = None
        self.offset = 0

        if size is None and number is not None:
            raise Error('please provide page[size]'.format(size))

        if size is not None:
            try:
                self.limit = int(size)
            except ValueError:
                raise Error('invalid value for page[size]: {!r}'.format(size))
            else:
                if self.limit <= 0:
                    raise Error('invalid value for page[size]: {!r}'.format(size))

        if number is not None:
            try:
                self.offset = (int(number) - 1) * self.limit
            except ValueError:
                raise Error('invalid value for page[number]: {!r}'.format(number))
            else:
                if int(number) <= 0:
                    raise Error('invalid value for page[number]: {!r}'.format(number))

    def __repr__(self):
        return '{}(limit={}, offset={})'.format(self.__class__.__name__, self.limit, self.offset)


class MergeArgument:

    def __init__(self, spec=None):

        if spec is None:
            spec = ''

        if not isinstance(spec, str):
            raise Error('merge argument must be a string')

        merge_operator, merge_count, exclude_operator, exclude_count = '=', 0, '=', 0
        match = re.match(r'([><]?=?)(\d+)(,([><]?=?)(\d+))?', spec)
        if match:
            merge_operator, merge_count, _, exclude_operator, exclude_count = match.groups()

        self.merge_operator = MODIFIERS[merge_operator] if merge_operator else MODIFIERS['=']
        self.exclude_operator = MODIFIERS[exclude_operator] if exclude_operator else MODIFIERS['=']

        try:
            self.merge_count = int(merge_count) if merge_count else 0
            self.exclude_count = int(exclude_count) if exclude_count else 0
        except ValueError:
            raise Error('invalid merge argument: {!r}'.format(spec))

        if self.merge_count < 0 or self.exclude_count < 0:
            raise Error('invalid merge argument: {!r}'.format(spec))

    def __repr__(self):
        return '{}({merge_operator.__name__}:{merge_count},' \
               '{exclude_operator.__name__}:{exclude_count})'.format(self.__class__.__name__, **self.__dict__)


class RequestArguments:

    def __init__(self, args):
        """
        :param args: a dictionary representing the request query string
        """
        args = args if args else dict()
        try:
            self.include = tuple(
                AttributePath(path) for path in args['include'].split(',')) if 'include' in args else ()
            self.fields = {f.type: f for f in
                           (FieldArgument(k, args[k]) for k in args.keys() if k.startswith('fields'))}
            self.sort = tuple(SortArgument(spec) for spec in args['sort'].split(',')) if 'sort' in args else ()
            self.filter = tuple(FilterArgument(k, args[k]) for k in args.keys() if k.startswith('filter'))
            self.page = PageArgument(args.get('page[size]', None), args.get('page[number]', None))
            self.merge = MergeArgument(args['merge']) if 'merge' in args else None
        except (AttributeError, TypeError):
            raise Error('argument parser | invalid dictionary: {!r}'.format(args))

    def fieldset_defined(self, resource_type):
        return resource_type in self.fields.keys()

    def fieldset_wildcard(self, resource_type):
        return resource_type in self.fields.keys() and '*' in self.fields[resource_type]

    def in_fieldset(self, resource_type, name):
        return self.fieldset_defined(resource_type) and name in self.fields[resource_type]

    def in_include(self, name, parents):
        return any(i.exists(name, parents) for i in self.include)

    def in_sort(self, name, parents):
        return any(s.path.exists(name, parents) for s in self.sort)

    def in_filter(self, name, parents):
        return any(f.path.exists(name, parents) for f in self.filter)


def parse_arguments(args):
    return RequestArguments(args)
