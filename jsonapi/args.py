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
        return tuple((*parents, name)) == self.names[:1+len(parents)]


class SortArgument:

    def __init__(self, spec):
        order, dot_path = re.search(r'([-+]?)(.+)', spec).groups()
        self.desc = order == '-'
        self.path = AttributePath(dot_path)


FilterArgument = namedtuple('FilterArgument', 'attr_name operator value')


class RequestArguments:

    def __init__(self, args):
        """
        :param args: a dictionary representing the request query string
        """

        self.include = dict()
        self.fields = dict()
        self.sort = tuple()

        self.offset = 0
        self.limit = None
        self.filter = dict()

        if args is None:
            return

        #
        # include
        #

        if 'include' in args:
            for dot_path in args['include'].split(','):
                include = self.include
                for attr in dot_path.split('.'):
                    if attr not in include:
                        include[attr] = dict()
                    include = include[attr]

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

        #
        # filter
        #

        for key in args.keys():
            if key.startswith('filter['):
                try:
                    field_name, attr_name, operator = self.filter_parts(key)
                except (ValueError, TypeError):
                    raise Error('invalid filter parameter: "{}"'.format(key))
                else:
                    self.filter[underscore(field_name)] = FilterArgument(
                        underscore(attr_name.lstrip('.')) if attr_name else '',
                        operator.lstrip(':') if operator else '',
                        args[key])

    @classmethod
    def filter_parts(cls, key):
        match = re.match(r'filter\[([-_\w]+)(\.[-_\w]+)?(:[-_\w]+)?\]', key)
        if match:
            return match.groups()

    def in_include(self, name, parents):
        include = dict(self.include)
        for parent in reversed(parents):
            include = include[parent] if parent in include else dict()
        return underscore(name) in include.keys()

    def in_fieldset(self, resource_type, name):
        return self.fieldset_defined(resource_type) and name in self.fields[
            resource_type]

    def fieldset_defined(self, resource_type):
        return resource_type in self.fields.keys()

    def in_sort(self, name, parents):
        return any(s.path.exists(name, parents) for s in self.sort)

    def in_filter(self, name):
        return name in self.filter


def parse_arguments(args):
    return RequestArguments(args)
