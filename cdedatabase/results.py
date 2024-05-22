# -*- coding: utf-8 -*-
"""
Results wrapper for iterables.

.. codeauthor:: Taketomo Isazawa <ti250@cam.ac.uk>
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
import logging
import re


class Results(object):
    """
    The Results wrapper for iterables easily allows for filters and sorts on
    query results from CDEDatabase without having to learn the query language
    for each separate backend.

    ..note::

        Results objects cannot be indexed as it just wraps around iterables,
        which may not have indices. This is so that results which are discarded as
        a result of filters are not kept in memory, which is more important when
        dealing with larger databases. Furthermore, Results objects cannot currently
        go back, so if one wishes to get the first element of a result again,
        one should perform the query again.
    """

    def __init__(self, iterable, database=None):
        """
        :param iterable iterable: Some iterable sequence.
        :param Optional(CDEDatabase) database: The database from which this result arose
        """
        self.iterable = iterable
        self.database = database

    def filtered(self, filter_function):
        """
        Filter the results by the given filter function.

        :param func(element)->bool filter_function: A function which returns true if an element should
            be part of the filtered results.
        :returns: The filtered results
        :rtype: Results
        """
        def internal_generator():
            for element in self.iterable:
                if filter_function(element):
                    yield element
        return Results(internal_generator(), self.database)

    def sorted(self, key):
        """
        The results sorted by the given key.

        ..note::

            This method loads the entire iterable into memory
            so if the results are going to be filtered, this should preferably be called after all filters
            have been applied.

        :param func(element)->object key: A function which returns a comparable object.
        :returns: The sorted results
        :rtype: Results
        """
        els = self.all()
        return Results(sorted(els, key=key), self.database)

    def all(self):
        """
        All the elements in Results loaded into a list.

        :returns: All the elements in this Results instance.
        :rtype: list
        """
        els = []
        for element in self.iterable:
            els.append(element)
        return els

    def __iter__(self):
        return self.iterable

