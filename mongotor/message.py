# Copyright 2009-2010 10gen, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tools for creating `messages
<http://www.mongodb.org/display/DOCS/Mongo+Wire+Protocol>`_ to be sent to
MongoDB.

.. note:: This module is for internal use and is generally not needed by
   application developers.
"""

import random
import struct

import bson
from bson.son import SON
from mongotor.errors import InvalidOperationError


__ZERO = b"\x00\x00\x00\x00"


def __last_error(args):
    """Data to send to do a lastError.
    """
    cmd = SON([("getlasterror", 1)])
    cmd.update(args)
    return query(0, "admin.$cmd", 0, -1, cmd)


def __pack_message(operation, data):
    """Takes message data and adds a message header based on the operation.

    Returns the resultant message string.
    """
    request_id = random.randint(-2 ** 31 - 1, 2 ** 31)
    message = struct.pack("<i", 16 + len(data))
    message += struct.pack("<i", request_id)
    message += __ZERO  # responseTo
    message += struct.pack("<i", operation)
    return (request_id, message + data)


def insert(collection_name, docs, check_keys, safe, last_error_args):
    """Get an **insert** message.
    """
    data = __ZERO
    data += bson._make_c_string(collection_name)
    bson_data = b"".join([bson.BSON.encode(doc, check_keys) for doc in docs])
    if not bson_data:
        raise InvalidOperationError("cannot do an empty bulk insert")
    data += bson_data
    if safe:
        (_, insert_message) = __pack_message(2002, data)
        (request_id, error_message) = __last_error(last_error_args)
        return (request_id, insert_message + error_message)
    else:
        return __pack_message(2002, data)


def update(collection_name, upsert, multi, spec, doc, safe, last_error_args):
    """Get an **update** message.
    """
    options = 0
    if upsert:
        options += 1
    if multi:
        options += 2

    data = __ZERO
    data += bson._make_c_string(collection_name)
    data += struct.pack("<i", options)
    data += bson.BSON.encode(spec)
    data += bson.BSON.encode(doc)
    if safe:
        (_, update_message) = __pack_message(2001, data)
        (request_id, error_message) = __last_error(last_error_args)
        return (request_id, update_message + error_message)
    else:
        return __pack_message(2001, data)


def query(options, collection_name,
          num_to_skip, num_to_return, query, field_selector=None):
    """Get a **query** message.
    """
    data = struct.pack("<I", options)
    data += bson._make_c_string(collection_name)
    data += struct.pack("<i", num_to_skip)
    data += struct.pack("<i", num_to_return)
    data += bson.BSON.encode(query)
    if field_selector is not None:
        data += bson.BSON.encode(field_selector)
    return __pack_message(2004, data)


def get_more(collection_name, num_to_return, cursor_id):
    """Get a **getMore** message.
    """
    data = __ZERO
    data += bson._make_c_string(collection_name)
    data += struct.pack("<i", num_to_return)
    data += struct.pack("<q", cursor_id)
    return __pack_message(2005, data)


def delete(collection_name, spec, safe, last_error_args):
    """Get a **delete** message.
    """
    data = __ZERO
    data += bson._make_c_string(collection_name)
    data += __ZERO
    data += bson.BSON.encode(spec)
    if safe:
        (_, remove_message) = __pack_message(2006, data)
        (request_id, error_message) = __last_error(last_error_args)
        return (request_id, remove_message + error_message)
    else:
        return __pack_message(2006, data)


def kill_cursors(cursor_ids):
    """Get a **killCursors** message.
    """
    data = __ZERO
    data += struct.pack("<i", len(cursor_ids))
    for cursor_id in cursor_ids:
        data += struct.pack("<q", cursor_id)
    return __pack_message(2007, data)
