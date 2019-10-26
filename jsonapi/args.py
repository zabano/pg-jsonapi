import re
from collections import namedtuple

from inflection import underscore

from jsonapi.exc import Error


class AttributePath:

    def __init__(self, dot_path):
        self.names = tuple(underscore(name) for name in dot_path.split('.'))

    def __len__(self):
        return len(self.names)

    def __iter__(self):
        return iter(self.names)

    def exists(self, name, parents=tuple()):
        return tuple((*parents, name)) == self.names[:1 + len(parents)]

    def __repr__(self):
        return '{}({})'.format(self.__class__.__name__, '.'.join(self.names))


class SortArgument:

    def __init__(self, spec):
        order, dot_path = re.search(r'([-+]?)(.+)', spec).groups()
        self.desc = order == '-'
        self.path = AttributePath(dot_path)

    def __repr__(self):
        return '{}({!r}, desc={!r})'.format(self.__class__.__name__, self.path, self.desc)


class FilterArgument:

    def __init__(self, spec, value):

        try:
            match = re.match(r'filter\[([-_.\w]+)(:[-_\w]+)?\]', spec)
            if not match:
                raise Error('invalid filter parameter: {!r}'.format(spec))
            dot_path, op = match.groups()
        except (ValueError, TypeError):
            raise Error('invalid filter parameter: {!r}'.format(spec))
        else:
            self.path = AttributePath(dot_path)
            self.operator = op.strip(':') if op else 'eq'
            self.value = value

    def __repr__(self):
        return '{}({!r}, op={!r}, val={!r})'.format(
            self.__class__.__name__, self.path, self.operator,
            self.value[:10] + '...' if len(self.value) > 10 else self.value)


class RequestArguments:

    def __init__(self, args):
        """
        :param args: a dictionary representing the request query string
        """

        self.fields = dict()
        self.include = tuple()
        self.sort = tuple()
        self.filter = tuple()

        self.offset = 0
        self.limit = None

        if args is None:
            return

        #
        # include
        #

        if 'include' in args:
            self.include = tuple(AttributePath(dot_path) for dot_path in args['include'].split(','))

        #
        # fields
        #

        for key, value in args.items():
            match = re.search(r'^fields\[([-_\w]+)\]$', key)
            if match:
                self.fields[match.group(1)] = set(
                    underscore(x.lower()) for x in value.split(',') + ['id'])

        #
        # sort
        #

        if 'sort' in args:
            self.sort = tuple(SortArgument(spec) for spec in args['sort'].split(','))

        #
        # filter
        #
        self.filter = tuple(FilterArgument(key, args[key])
                            for key in args.keys() if key.startswith('filter'))

        #
        # page
        #

        if 'page[size]' in args:
            try:
                self.limit = int(args['page[size]'])
            except ValueError:
                raise Error('page[size] option must be an integer')
            if self.limit <= 0:
                raise Error('page[size] option must be positive')
            if 'page[number]' in args and self.limit > 0:
                try:
                    number = int(args['page[number]'])
                except ValueError:
                    raise Error('page[number] option must be an integer')
                else:
                    if number <= 0:
                        raise Error('page[number] option must be positive')
                    self.offset = (number - 1) * self.limit
        elif 'page[number]' in args:
            raise Error('page[size] option not provided')

    def fieldset_defined(self, resource_type):
        return resource_type in self.fields.keys()

    def in_fieldset(self, resource_type, name):
        return self.fieldset_defined(resource_type) and name in self.fields[
            resource_type]

    def in_include(self, name, parents):
        return any(i.exists(name, parents) for i in self.include)

    def in_sort(self, name, parents):
        return any(s.path.exists(name, parents) for s in self.sort)

    def in_filter(self, name, parents):
        return any(f.path.exists(name, parents) for f in self.filter)


def parse_arguments(args):
    return RequestArguments(args)
