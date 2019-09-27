import re
import inflection
from collections import OrderedDict

from jsonapi.exc import Error


class RequestArguments:

    def __init__(self, args):
        """
        :param args: a dictionary representing the request query string
        :param include: an additional include value
        """

        self.include = dict()
        self.fields = dict()
        self.sort = OrderedDict()

        self.offset = 0
        self.limit = None

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
            match = re.search('^fields\[([-_\w]+)\]$', key)
            if match:
                self.fields[match.group(1)] = set(inflection.underscore(x.lower()) for
                                                  x in value.split(',') + ['id'])

        #
        # sort
        #

        if 'sort' in args:
            for sort_spec in args['sort'].split(','):
                order, name = re.search('([-+]?)(.+)', sort_spec).groups()
                if '.' in name:
                    raise Error('"sort" parameter does not support '
                                'dot notation: "{}"'.format(name))
                self.sort[inflection.underscore(name).strip()] = (order == '-')

        #
        # page
        #

        if 'page[size]' in args:

            try:
                self.limit = int(args['page[size]'])
            except ValueError:
                raise Error('page[size] request parameter must be an integer')

            if self.limit <= 0:
                raise Error('page[size] request parameter must be positive')

            if 'page[number]' in args and self.limit > 0:

                try:
                    number = int(args['page[number]'])
                except ValueError:
                    raise Error('page[number] request parameter must be an integer')
                else:
                    if number <= 0:
                        raise Error('page[number] request parameter must be positive')
                    self.offset = (number - 1) * self.limit

    def in_include(self, name):
        return name in self.include.keys()

    def in_fieldset(self, resource_type, name):
        return self.fieldset_defined(resource_type) and name in self.fields[resource_type]

    def fieldset_defined(self, resource_type):
        return resource_type in self.fields.keys()

    def in_sort(self, name):
        return name in self.sort.keys()
