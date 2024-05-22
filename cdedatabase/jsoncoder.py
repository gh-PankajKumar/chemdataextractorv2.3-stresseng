# -*- coding: utf-8 -*-
"""
JSON encoder and decoder for CDEDatabase.

.. codeauthor:: Taketomo Isazawa <ti250@cam.ac.uk>
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
import logging
import re
import os
import shutil
import ijson
import simplejson as json
import six
from tempfile import mkstemp

from .coder import PlainTextCoder


# Function from https://stackoverflow.com/questions/36766532/read-top-level-json-dictionary-incrementally-using-python-ijson to get all top-level JSON objects from a file
def _objects(file):
    key = '-'
    for prefix, event, value in ijson.parse(file):
        if prefix == '' and event == 'map_key':  # found new object at the root
            key = value  # mark the key value
            builder = ijson.ObjectBuilder()
        elif prefix.startswith(key):  # while at this key, build the object
            builder.event(event, value)
            if event == 'end_map':  # found the end of an object at the current key, yield
                yield key, builder.value


class JSONCoder(PlainTextCoder):
    """
    A :class:`~chemdataextractor.database.coder.BaseCoder` implementation for saving the records in JSON.
    The database is stored in a folder with the database name inside the folder from which
    the CDEDatabase is being called.

    All unique identifiers for this coder are of integer type.

    Each class gets its own JSON file (e.g. MeltingPoint.json) where the records themselves are stored,
    and an additioinal file with the class name followed by _ids (e.g. MeltingPoint_ids) where all
    the ids used in the database are stored. This is done to make checking for and creating
    unique identifiers more performant. Each record should occupy only one line in the JSON file,
    an assumption which is used in the update() and delete() methods.
    """
    file_extension = '.json'

    def record(self, record_type, id_, db_name):
        folder = db_name
        filename = self._get_file_name(record_type, folder)
        with open(filename) as f:
            items = ijson.items(f, str(id_))
            for element in items:
                return element
        return None

    def records(self, record_type, db_name):
        folder = db_name
        filename = self._get_file_name(record_type, folder)
        results = []
        with open(filename) as f:
            items = _objects(f)
            for element in items:
                results.append(element[1])
        return results

    def add(self, records, db_name):
        folder = db_name
        super(JSONCoder, self).add(records, db_name)
        for record_type, records_list in six.iteritems(records):
            if records_list:
                filename = self._get_file_name(record_type, folder)

                # Remove the closing bracket for the JSON and check if this database is populated or not.
                populated = False
                with open(filename, 'rb+') as f:
                    f.seek(-2, os.SEEK_END)
                    f.truncate()
                    f.seek(-1, os.SEEK_END)
                    if f.read() != b'\n':
                        populated = True

                # Append the new values to the end of the file
                with open(filename, 'a', newline='\n') as f:
                    if populated:
                        f.write(',\n')
                    previous_value = None
                    # Only addd a comma at the end of the line if it's not the final record.
                    for record in records_list:
                        if previous_value:
                            f.write(json.dumps({previous_value['_id']: previous_value})[1:-1] + ',\n')
                        previous_value = record
                    if previous_value:
                        f.write(json.dumps({previous_value['_id']: previous_value})[1:-1] + '\n')
                    f.write('}')

    def update(self, records, db_name):
        folder = db_name
        for record_type, records_list in six.iteritems(records):
            to_update = {}
            for record in records_list:
                to_update[str(record['_id'])] = record
            keys = to_update.keys()
            if keys:
                # Write everything that currently exists and any updates in a new temporary file,
                # then delete the current file and move the temporary file in its place.
                # Therefore, the longer the file, the slower the update function.
                file_handle, abs_path = mkstemp()
                filename = self._get_file_name(record_type, folder)
                print(filename)
                with open(filename, 'r', newline='\n') as old_file:
                    with open(file_handle, 'w', newline='\n') as new_file:
                        for line in old_file:
                            if line[0] in ['{', '}']:
                                new_file.write(line)
                            else:
                                # Functionality to ensure current values are read correctly.
                                if line[-2] == ',':
                                    adjusted_line = '{' + line[:-2] + '}'
                                else:
                                    adjusted_line = '{' + line[:-1] + '}'
                                print(adjusted_line)
                                dictionary_form = json.loads(adjusted_line)
                                key = None
                                for k in dictionary_form.keys():
                                    key = k
                                if key in keys:
                                    new_line = json.dumps({key: to_update[key]})[1:-1]
                                    if line[-2] == ',':
                                        new_line += ','
                                    new_line += '\n'
                                    new_file.write(new_line)
                                    to_update.pop(key)
                                    keys = to_update.keys()
                                else:
                                    new_file.write(line)
                os.remove(filename)
                shutil.move(abs_path, filename)

    def delete(self, record_type, ids, db_name):
        super(JSONCoder, self).delete(record_type, ids, db_name)
        folder = db_name
        ids = [str(id_) for id_ in ids]
        if ids:
            # Write everything that currently exists bar anything with the identifiers
            # that the user wants to delete in a new temporary file,
            # then delete the current file and move the temporary file in its place.
            # Therefore, the longer the file, the slower the delete function.
            file_handle, abs_path = mkstemp()
            filename = self._get_file_name(record_type, folder)
            num_records_written = 0
            with open(filename) as old_file:
                with open(file_handle, 'w', newline='\n') as new_file:
                    previous_line = None
                    for line in old_file:
                        if line[0] in ['{', '}']:
                            print('FINALPART', previous_line, line)
                            if previous_line:
                                print(previous_line)
                                new_file.write(previous_line + '\n')
                            if not num_records_written and line[0] != "{":
                                new_file.write("\n")
                            new_file.write(line)
                        else:
                            if line[-2] == ',':
                                adjusted_line = '{' + line[:-2] + '}'
                            else:
                                adjusted_line = '{' + line[:-1] + '}'
                            dictionary_form = json.loads(adjusted_line)
                            key = None
                            for k in dictionary_form.keys():
                                key = k
                            if key not in ids:
                                num_records_written += 1
                                if previous_line:
                                    new_file.write(previous_line + ',\n')
                                previous_line = adjusted_line[1:-1]
            os.remove(filename)
            shutil.move(abs_path, filename)

    def _initialise(self, file_path, record_type):
        with open(file_path, 'w', newline='\n') as f:
            f.writelines('{\n\n')
            f.writelines('}')
