from __future__ import absolute_import

import datetime
import time
import decimal
import gridfs
import re
import uuid

import six
from bson import Binary, DBRef, SON, ObjectId

from .base import (BaseField, ComplexBaseField, ObjectIdField,
                  ValidationError, get_document)
from .queryset import DO_NOTHING, QuerySet
from .document import Document, EmbeddedDocument
from .connection import get_db, DEFAULT_CONNECTION_NAME
from operator import itemgetter


try:
    from PIL import Image, ImageOps
except ImportError:
    Image = None
    ImageOps = None


__all__ = ['StringField', 'IntField', 'FloatField', 'BooleanField',
           'DateTimeField', 'EmbeddedDocumentField', 'ListField', 'DictField',
           'ObjectIdField', 'ReferenceField', 'ValidationError', 'MapField',
           'DecimalField', 'ComplexDateTimeField', 'URLField',
           'GenericReferenceField', 'FileField', 'BinaryField',
           'SortedListField', 'EmailField', 'GeoPointField', 'ImageField',
           'SequenceField', 'UUIDField', 'GenericEmbeddedDocumentField']

RECURSIVE_REFERENCE_CONSTANT = 'self'


class StringField(BaseField):
    """A unicode string field.
    """

    def __init__(self, regex=None, max_length=None, min_length=None, **kwargs):
        self.regex = re.compile(regex) if regex else None
        self.max_length = max_length
        self.min_length = min_length
        super(StringField, self).__init__(**kwargs)

    def to_python(self, value):
        return six.text_type(value)

    def validate(self, value):
        if not isinstance(value, six.string_types):
            self.error('StringField only accepts string values')

        if self.max_length is not None and len(value) > self.max_length:
            self.error('String value is too long')

        if self.min_length is not None and len(value) < self.min_length:
            self.error('String value is too short')

        if self.regex is not None and self.regex.match(value) is None:
            self.error('String value did not match validation regex')

    def lookup_member(self, member_name):
        return None

    def prepare_query_value(self, op, value):
        if not isinstance(op, six.string_types):
            return value

        if op.lstrip('i') in ('startswith', 'endswith', 'contains', 'exact'):
            flags = 0
            if op.startswith('i'):
                flags = re.IGNORECASE
                op = op.lstrip('i')

            regex = r'%s'
            if op == 'startswith':
                regex = r'^%s'
            elif op == 'endswith':
                regex = r'%s$'
            elif op == 'exact':
                regex = r'^%s$'

            # escape unsafe characters which could lead to a re.error
            value = re.escape(value)
            value = re.compile(regex % value, flags)
        return value


class URLField(StringField):
    """A field that validates input as an URL.

    .. versionadded:: 0.3
    """

    URL_REGEX = re.compile(
        r'^https?://'
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'
        r'localhost|'
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
        r'(?::\d+)?'
        r'(?:/?|[/?]\S+)$', re.IGNORECASE
    )

    def __init__(self, verify_exists=False, **kwargs):
        self.verify_exists = verify_exists
        super(URLField, self).__init__(**kwargs)

    def validate(self, value):
        if not URLField.URL_REGEX.match(value):
            self.error('Invalid URL: %s' % value)

        if self.verify_exists:
            try:
                request = six.moves.urllib.request.Request(value)
                six.moves.urllib.request.urlopen(request)
            except Exception as e:
                self.error('This URL appears to be a broken link: %s' % e)


class EmailField(StringField):
    """A field that validates input as an E-Mail-Address.

    .. versionadded:: 0.4
    """

    EMAIL_REGEX = re.compile(
        r"(^[-!#$%&'*+/=?^_`{}|~0-9A-Z]+(\.[-!#$%&'*+/=?^_`{}|~0-9A-Z]+)*"  # dot-atom  # noqa
        r'|^"([\001-\010\013\014\016-\037!#-\[\]-\177]|\\[\001-011\013\014\016-\177])*"'  # quoted-string  # noqa
        r')@(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?$', re.IGNORECASE  # domain  # noqa
    )

    def validate(self, value):
        if not EmailField.EMAIL_REGEX.match(value):
            self.error('Invalid Mail-address: %s' % value)


class IntField(BaseField):
    """An integer field.
    """

    def __init__(self, min_value=None, max_value=None, **kwargs):
        self.min_value, self.max_value = min_value, max_value
        super(IntField, self).__init__(**kwargs)

    def to_python(self, value):
        return int(value)

    def validate(self, value):
        try:
            value = int(value)
        except:
            self.error('%s could not be converted to int' % value)

        if self.min_value is not None and value < self.min_value:
            self.error('Integer value is too small')

        if self.max_value is not None and value > self.max_value:
            self.error('Integer value is too large')

    def prepare_query_value(self, op, value):
        return int(value)


class FloatField(BaseField):
    """An floating point number field.
    """

    def __init__(self, min_value=None, max_value=None, **kwargs):
        self.min_value, self.max_value = min_value, max_value
        super(FloatField, self).__init__(**kwargs)

    def to_python(self, value):
        return float(value)

    def validate(self, value):
        if isinstance(value, int):
            value = float(value)
        if not isinstance(value, float):
            self.error('FoatField only accepts float values')

        if self.min_value is not None and value < self.min_value:
            self.error('Float value is too small')

        if self.max_value is not None and value > self.max_value:
            self.error('Float value is too large')

    def prepare_query_value(self, op, value):
        return float(value)


class DecimalField(BaseField):
    """A fixed-point decimal number field.

    .. versionadded:: 0.3
    """

    def __init__(self, min_value=None, max_value=None, **kwargs):
        self.min_value, self.max_value = min_value, max_value
        super(DecimalField, self).__init__(**kwargs)

    def to_python(self, value):
        if not isinstance(value, six.string_types):
            value = six.text_type(value)
        return decimal.Decimal(value)

    def to_mongo(self, value):
        return six.text_type(value)

    def validate(self, value):
        if not isinstance(value, decimal.Decimal):
            if not isinstance(value, six.string_types):
                value = six.text_type(value)
            try:
                value = decimal.Decimal(value)
            except Exception as exc:
                self.error('Could not convert value to decimal: %s' % exc)

        if self.min_value is not None and value < self.min_value:
            self.error('Decimal value is too small')

        if self.max_value is not None and value > self.max_value:
            self.error('Decimal value is too large')


class BooleanField(BaseField):
    """A boolean field type.

    .. versionadded:: 0.1.2
    """

    def to_python(self, value):
        return bool(value)

    def validate(self, value):
        if not isinstance(value, bool):
            self.error('BooleanField only accepts boolean values')


class DateTimeField(BaseField):
    """A datetime field.

    Note: Microseconds are rounded to the nearest millisecond.
      Pre UTC microsecond support is effecively broken.
      Use :class:`~mongoengine.fields.ComplexDateTimeField` if you
      need accurate microsecond support.
    """

    def validate(self, value):
        if not isinstance(value, (datetime.datetime, datetime.date)):
            self.error(u'cannot parse date "%s"' % value)

    def to_mongo(self, value):
        return self.prepare_query_value(None, value)

    def prepare_query_value(self, op, value):
        if value is None:
            return value
        if isinstance(value, datetime.datetime):
            return value
        if isinstance(value, datetime.date):
            return datetime.datetime(value.year, value.month, value.day)

        # Attempt to parse a datetime:
        # value = smart_str(value)
        # split usecs, because they are not recognized by strptime.
        if '.' in value:
            try:
                value, usecs = value.split('.')
                usecs = int(usecs)
            except ValueError:
                return None
        else:
            usecs = 0
        kwargs = {'microsecond': usecs}
        try:  # Seconds are optional, so try converting seconds first.
            return datetime.datetime(
                *time.strptime(value, '%Y-%m-%d %H:%M:%S')[:6], **kwargs)
        except ValueError:
            try:  # Try without seconds.
                return datetime.datetime(
                    *time.strptime(value, '%Y-%m-%d %H:%M')[:5], **kwargs)
            except ValueError:  # Try without hour/minutes/seconds.
                try:
                    return datetime.datetime(
                        *time.strptime(value, '%Y-%m-%d')[:3], **kwargs)
                except ValueError:
                    return None


class ComplexDateTimeField(StringField):
    """
    ComplexDateTimeField handles microseconds exactly instead of rounding
    like DateTimeField does.

    Derives from a StringField so you can do `gte` and `lte` filtering by
    using lexicographical comparison when filtering / sorting strings.

    The stored string has the following format:

        YYYY,MM,DD,HH,MM,SS,NNNNNN

    Where NNNNNN is the number of microseconds of the represented `datetime`.
    The `,` as the separator can be easily modified by passing the `separator`
    keyword when initializing the field.

    .. versionadded:: 0.5
    """

    def __init__(self, separator=',', **kwargs):
        self.names = ['year', 'month', 'day', 'hour', 'minute', 'second',
                      'microsecond']
        self.separtor = separator
        super(ComplexDateTimeField, self).__init__(**kwargs)

    def _leading_zero(self, number):
        """
        Converts the given number to a string.

        If it has only one digit, a leading zero so as it has always at least
        two digits.
        """
        if int(number) < 10:
            return "0%s" % number
        else:
            return str(number)

    def _convert_from_datetime(self, val):
        """
        Convert a `datetime` object to a string representation (which will be
        stored in MongoDB). This is the reverse function of
        `_convert_from_string`.

        >>> a = datetime(2011, 6, 8, 20, 26, 24, 192284)
        >>> RealDateTimeField()._convert_from_datetime(a)
        '2011,06,08,20,26,24,192284'
        """
        data = []
        for name in self.names:
            data.append(self._leading_zero(getattr(val, name)))
        return ','.join(data)

    def _convert_from_string(self, data):
        """
        Convert a string representation to a `datetime` object (the object you
        will manipulate). This is the reverse function of
        `_convert_from_datetime`.

        >>> a = '2011,06,08,20,26,24,192284'
        >>> ComplexDateTimeField()._convert_from_string(a)
        datetime.datetime(2011, 6, 8, 20, 26, 24, 192284)
        """
        data = data.split(',')
        data = list(map(int, data))
        values = {}
        for i in range(7):
            values[self.names[i]] = data[i]
        return datetime.datetime(**values)

    def __get__(self, instance, owner):
        data = super(ComplexDateTimeField, self).__get__(instance, owner)
        if data is None:
            return datetime.datetime.now()
        return self._convert_from_string(data)

    def __set__(self, instance, value):
        value = self._convert_from_datetime(value)
        return super(ComplexDateTimeField, self).__set__(instance, value)

    def validate(self, value):
        if not isinstance(value, datetime.datetime):
            self.error('Only datetime objects may used in a '
                       'ComplexDateTimeField')

    def to_python(self, value):
        return self._convert_from_string(value)

    def to_mongo(self, value):
        return self._convert_from_datetime(value)

    def prepare_query_value(self, op, value):
        return self._convert_from_datetime(value)


class EmbeddedDocumentField(BaseField):
    """An embedded document field - with a declared document_type.
    Only valid values are subclasses of :class:`~mongoengine.EmbeddedDocument`.
    """

    def __init__(self, document_type, **kwargs):
        if not isinstance(document_type, six.string_types):
            if not issubclass(document_type, EmbeddedDocument):
                self.error('Invalid embedded document class provided to an '
                           'EmbeddedDocumentField')
        self.document_type_obj = document_type
        super(EmbeddedDocumentField, self).__init__(**kwargs)

    @property
    def document_type(self):
        if isinstance(self.document_type_obj, six.string_types):
            if self.document_type_obj == RECURSIVE_REFERENCE_CONSTANT:
                self.document_type_obj = self.owner_document
            else:
                self.document_type_obj = get_document(self.document_type_obj)
        return self.document_type_obj

    def to_python(self, value):
        if not isinstance(value, self.document_type):
            return self.document_type._from_son(value)
        return value

    def to_mongo(self, value):
        if not isinstance(value, self.document_type):
            return value
        return self.document_type.to_mongo(value)

    def validate(self, value):
        """Make sure that the document instance is an instance of the
        EmbeddedDocument subclass provided when the document was defined.
        """
        # Using isinstance also works for subclasses of self.document
        if not isinstance(value, self.document_type):
            self.error('Invalid embedded document instance provided to an '
                       'EmbeddedDocumentField')
        self.document_type.validate(value)

    def lookup_member(self, member_name):
        return self.document_type._fields.get(member_name)

    def prepare_query_value(self, op, value):
        return self.to_mongo(value)


class GenericEmbeddedDocumentField(BaseField):
    """A generic embedded document field - allows any
    :class:`~mongoengine.EmbeddedDocument` to be stored.

    Only valid values are subclasses of :class:`~mongoengine.EmbeddedDocument`.
    """

    def prepare_query_value(self, op, value):
        return self.to_mongo(value)

    def to_python(self, value):
        if isinstance(value, dict):
            doc_cls = get_document(value['_cls'])
            value = doc_cls._from_son(value)

        return value

    def validate(self, value):
        if not isinstance(value, EmbeddedDocument):
            self.error('Invalid embedded document instance provided to an '
                       'GenericEmbeddedDocumentField')

        value.validate()

    def to_mongo(self, document):
        if document is None:
            return None

        data = document.to_mongo()
        if '_cls' not in data:
            data['_cls'] = document._class_name
        return data


class ListField(ComplexBaseField):
    """A list field that wraps a standard field, allowing multiple instances
    of the field to be used as a list in the database.

    .. note::
        Required means it cannot be empty - as the default for ListFields is []
    """

    def __init__(self, field=None, **kwargs):
        self.field = field
        kwargs.setdefault('default', lambda: [])
        super(ListField, self).__init__(**kwargs)

    def validate(self, value):
        """Make sure that a list of valid fields is being used.
        """
        if (not isinstance(value, (list, tuple, QuerySet)) or
                isinstance(value, six.string_types)):
            self.error('Only lists and tuples may be used in a list field')
        super(ListField, self).validate(value)

    def prepare_query_value(self, op, value):
        if self.field:
            if op in ('set', 'unset') \
                    and (not isinstance(value, six.string_types) and
                         hasattr(value, '__iter__')):
                return [self.field.prepare_query_value(op, v) for v in value]
            return self.field.prepare_query_value(op, value)
        return super(ListField, self).prepare_query_value(op, value)


class SortedListField(ListField):
    """A ListField that sorts the contents of its list before writing to
    the database in order to ensure that a sorted list is always
    retrieved.

    .. warning::
        There is a potential race condition when handling lists.  If you set /
        save the whole list then other processes trying to save the whole list
        as well could overwrite changes.  The safest way to append to a list is
        to perform a push operation.

    .. versionadded:: 0.4
    .. versionchanged:: 0.6 - added reverse keyword
    """

    _ordering = None
    _order_reverse = False

    def __init__(self, field, **kwargs):
        if 'ordering' in kwargs:
            self._ordering = kwargs.pop('ordering')
        if 'reverse' in kwargs:
            self._order_reverse = kwargs.pop('reverse')
        super(SortedListField, self).__init__(field, **kwargs)

    def to_mongo(self, value):
        value = super(SortedListField, self).to_mongo(value)
        if self._ordering is not None:
            return sorted(value,
                          key=itemgetter(self._ordering),
                          reverse=self._order_reverse)
        return sorted(value, reverse=self._order_reverse)


class DictField(ComplexBaseField):
    """A dictionary field that wraps a standard Python dictionary. This is
    similar to an embedded document, but the structure is not defined.

    .. note::
        Required means it cannot be empty - as the default for ListFields is []

    .. versionadded:: 0.3
    .. versionchanged:: 0.5 - Can now handle complex / varying types of data
    """

    def __init__(self, basecls=None, field=None, *args, **kwargs):
        self.field = field
        self.basecls = basecls or BaseField
        if not issubclass(self.basecls, BaseField):
            self.error('DictField only accepts dict values')
        kwargs.setdefault('default', lambda: {})
        super(DictField, self).__init__(*args, **kwargs)

    def validate(self, value):
        """Make sure that a list of valid fields is being used.
        """
        if not isinstance(value, dict):
            self.error('Only dictionaries may be used in a DictField')

        if any(k for k in value.keys() if not isinstance(k, six.string_types)):
            self.error(
                'Invalid dictionary key - documents must have only string keys')
        if any(('.' in k or '$' in k) for k in value.keys()):
            self.error('Invalid dictionary key name - keys may not contain "."'
                       ' or "$" characters')
        super(DictField, self).validate(value)

    def lookup_member(self, member_name):
        return DictField(basecls=self.basecls, db_field=member_name)

    def prepare_query_value(self, op, value):
        match_operators = ['contains', 'icontains', 'startswith',
                           'istartswith', 'endswith', 'iendswith',
                           'exact', 'iexact']

        if op in match_operators and isinstance(value, six.string_types):
            return StringField().prepare_query_value(op, value)

        return super(DictField, self).prepare_query_value(op, value)


class MapField(DictField):
    """A field that maps a name to a specified field type. Similar to
    a DictField, except the 'value' of each item must match the specified
    field type.

    .. versionadded:: 0.5
    """

    def __init__(self, field=None, *args, **kwargs):
        if not isinstance(field, BaseField):
            self.error('Argument to MapField constructor must be a valid '
                       'field')
        super(MapField, self).__init__(field=field, *args, **kwargs)


class ReferenceField(BaseField):
    """A reference to a document that will be automatically dereferenced on
    access (lazily).

    Use the `reverse_delete_rule` to handle what should happen if the document
    the field is referencing is deleted.  EmbeddedDocuments, DictFields and
    MapFields do not support reverse_delete_rules and an `InvalidDocumentError`
    will be raised if trying to set on one of these Document / Field types.

    The options are:

      * DO_NOTHING  - don't do anything (default).
      * NULLIFY     - Updates the reference to null.
      * CASCADE     - Deletes the documents associated with the reference.
      * DENY        - Prevent the deletion of the reference object.

    .. versionchanged:: 0.5 added `reverse_delete_rule`
    """

    def __init__(self, document_type, reverse_delete_rule=DO_NOTHING, **kwargs):
        """Initialises the Reference Field.

        :param reverse_delete_rule: Determines what to do when the referring
          object is deleted
        """
        if not isinstance(document_type, six.string_types):
            if not issubclass(document_type, Document):
                self.error('Argument to ReferenceField constructor must be a '
                           'document class or a string')
        self.document_type_obj = document_type
        self.reverse_delete_rule = reverse_delete_rule
        super(ReferenceField, self).__init__(**kwargs)

    @property
    def document_type(self):
        if isinstance(self.document_type_obj, six.string_types):
            if self.document_type_obj == RECURSIVE_REFERENCE_CONSTANT:
                self.document_type_obj = self.owner_document
            else:
                self.document_type_obj = get_document(self.document_type_obj)
        return self.document_type_obj

    def __get__(self, instance, owner):
        """Descriptor to allow lazy dereferencing.
        """
        if instance is None:
            # Document class being used rather than a document object
            return self

        # Get value from document instance if available
        value = instance._data.get(self.name)
        # Dereference DBRefs
        if isinstance(value, (DBRef)):
            value = self.document_type._get_db().dereference(value)
            if value is not None:
                instance._data[self.name] = self.document_type._from_son(value)

        return super(ReferenceField, self).__get__(instance, owner)

    def to_mongo(self, document):
        id_field_name = self.document_type._meta['id_field']
        id_field = self.document_type._fields[id_field_name]

        if isinstance(document, Document):
            # We need the id from the saved object to create the DBRef
            id_ = document.id
            if id_ is None:
                self.error('You can only reference documents once they have'
                           ' been saved to the database')
        else:
            id_ = document

        id_ = id_field.to_mongo(id_)
        collection = self.document_type._get_collection_name()
        return DBRef(collection, id_)

    def prepare_query_value(self, op, value):
        if value is None:
            return None

        return self.to_mongo(value)

    def validate(self, value):
        if not isinstance(value, (self.document_type, DBRef)):
            self.error('A ReferenceField only accepts DBRef')

        if isinstance(value, Document) and value.id is None:
            self.error('You can only reference documents once they have been '
                       'saved to the database')

    def lookup_member(self, member_name):
        return self.document_type._fields.get(member_name)


class GenericReferenceField(BaseField):
    """A reference to *any* :class:`~mongoengine.document.Document` subclass
    that will be automatically dereferenced on access (lazily).

    ..note ::  Any documents used as a generic reference must be registered in
    the document registry.  Importing the model will automatically register it.

    .. versionadded:: 0.3
    """

    def __get__(self, instance, owner):
        if instance is None:
            return self

        value = instance._data.get(self.name)
        if isinstance(value, (dict, SON)):
            instance._data[self.name] = self.dereference(value)

        return super(GenericReferenceField, self).__get__(instance, owner)

    def validate(self, value):
        if not isinstance(value, (Document, DBRef)):
            self.error('GenericReferences can only contain documents')

        # We need the id from the saved object to create the DBRef
        if isinstance(value, Document) and value.id is None:
            self.error('You can only reference documents once they have been'
                       ' saved to the database')

    def dereference(self, value):
        doc_cls = get_document(value['_cls'])
        reference = value['_ref']
        doc = doc_cls._get_db().dereference(reference)
        if doc is not None:
            doc = doc_cls._from_son(doc)
        return doc

    def to_mongo(self, document):
        if document is None:
            return None

        id_field_name = document.__class__._meta['id_field']
        id_field = document.__class__._fields[id_field_name]

        if isinstance(document, Document):
            # We need the id from the saved object to create the DBRef
            id_ = document.id
            if id_ is None:
                self.error('You can only reference documents once they have'
                           ' been saved to the database')
        else:
            id_ = document

        id_ = id_field.to_mongo(id_)
        collection = document._get_collection_name()
        ref = DBRef(collection, id_)
        return {'_cls': document._class_name, '_ref': ref}

    def prepare_query_value(self, op, value):
        if value is None:
            return None

        return self.to_mongo(value)


class BinaryField(BaseField):
    """A binary data field.
    """

    def __init__(self, max_bytes=None, **kwargs):
        self.max_bytes = max_bytes
        super(BinaryField, self).__init__(**kwargs)

    def to_mongo(self, value):
        return Binary(value)

    def to_python(self, value):
        return six.binary_type(value)

    def validate(self, value):
        if not isinstance(value, six.binary_type):
            self.error('BinaryField only accepts binary values')

        if self.max_bytes is not None and len(value) > self.max_bytes:
            self.error('Binary value is too long')


class GridFSError(Exception):
    pass


class GridFSProxy(object):
    """Proxy object to handle writing and reading of files to and from GridFS

    .. versionadded:: 0.4
    .. versionchanged:: 0.5 - added optional size param to read
    .. versionchanged:: 0.6 - added collection name param
    """

    _fs = None

    def __init__(self, grid_id=None, key=None,
                 instance=None,
                 db_alias=DEFAULT_CONNECTION_NAME,
                 collection_name='fs'):
        self.grid_id = grid_id                  # Store GridFS id for file
        self.key = key
        self.instance = instance
        self.db_alias = db_alias
        self.collection_name = collection_name
        self.newfile = None                     # Used for partial writes
        self.gridout = None

    def __getattr__(self, name):
        attrs = ('_fs', 'grid_id', 'key', 'instance', 'db_alias',
                 'collection_name', 'newfile', 'gridout')
        if name in attrs:
            return self.__getattribute__(name)
        obj = self.get()
        if name in dir(obj):
            return getattr(obj, name)
        raise AttributeError

    def __get__(self, instance, value):
        return self

    def __bool__(self):
        return bool(self.grid_id)

    __nonzero__ = __bool__

    def __getstate__(self):
        self_dict = self.__dict__
        self_dict['_fs'] = None
        return self_dict

    @property
    def fs(self):
        if not self._fs:
            self._fs = gridfs.GridFS(get_db(self.db_alias),
                                     self.collection_name)
        return self._fs

    def get(self, id=None):
        if id:
            self.grid_id = id
        if self.grid_id is None:
            return None
        try:
            if self.gridout is None:
                self.gridout = self.fs.get(self.grid_id)
            return self.gridout
        except:
            # File has been deleted
            return None

    def new_file(self, **kwargs):
        self.newfile = self.fs.new_file(**kwargs)
        self.grid_id = self.newfile._id

    def put(self, file_obj, **kwargs):
        if self.grid_id:
            raise GridFSError('This document already has a file. Either delete '
                              'it or call replace to overwrite it')
        self.grid_id = self.fs.put(file_obj, **kwargs)
        self._mark_as_changed()

    def write(self, string):
        if self.grid_id:
            if not self.newfile:
                raise GridFSError('This document already has a file. Either '
                                  'delete it or call replace to overwrite it')
        else:
            self.new_file()
        self.newfile.write(string)

    def writelines(self, lines):
        if not self.newfile:
            self.new_file()
            self.grid_id = self.newfile._id
        self.newfile.writelines(lines)

    def read(self, size=-1):
        try:
            return self.get().read(size)
        except:
            return None

    def delete(self):
        # Delete file from GridFS, FileField still remains
        self.fs.delete(self.grid_id)
        self.grid_id = None
        self.gridout = None
        self._mark_as_changed()

    def replace(self, file_obj, **kwargs):
        self.delete()
        self.put(file_obj, **kwargs)

    def close(self):
        if self.newfile:
            self.newfile.close()

    def _mark_as_changed(self):
        """Inform the instance that `self.key` has been changed"""
        if self.instance:
            self.instance._mark_as_changed(self.key)


class FileField(BaseField):
    """A GridFS storage field.

    .. versionadded:: 0.4
    .. versionchanged:: 0.5 added optional size param for read
    .. versionchanged:: 0.6 added db_alias for multidb support
    """
    proxy_class = GridFSProxy

    def __init__(self,
                 db_alias=DEFAULT_CONNECTION_NAME,
                 collection_name="fs", **kwargs):
        super(FileField, self).__init__(**kwargs)
        self.collection_name = collection_name
        self.db_alias = db_alias

    def __get__(self, instance, owner):
        if instance is None:
            return self

        # Check if a file already exists for this model
        grid_file = instance._data.get(self.name)
        self.grid_file = grid_file
        if isinstance(self.grid_file, self.proxy_class):
            if not self.grid_file.key:
                self.grid_file.key = self.name
                self.grid_file.instance = instance
            return self.grid_file
        return self.proxy_class(key=self.name, instance=instance,
                                db_alias=self.db_alias,
                                collection_name=self.collection_name)

    def __set__(self, instance, value):
        key = self.name
        is_file = hasattr(value, 'read') and not isinstance(value, GridFSProxy)
        if is_file or isinstance(value, six.string_types + (six.binary_type,)):
            # using "FileField() = file/string" notation
            grid_file = instance._data.get(self.name)
            # If a file already exists, delete it
            if grid_file:
                try:
                    grid_file.delete()
                except:
                    pass
                # Create a new file with the new data
                grid_file.put(value)
            else:
                # Create a new proxy object as we don't already have one
                instance._data[key] = self.proxy_class(
                    key=key,
                    instance=instance,
                    collection_name=self.collection_name)
                instance._data[key].put(value)
        else:
            instance._data[key] = value

        instance._mark_as_changed(key)

    def to_mongo(self, value):
        # Store the GridFS file id in MongoDB
        if isinstance(value, self.proxy_class) and value.grid_id is not None:
            return value.grid_id
        return None

    def to_python(self, value):
        if value is not None:
            return self.proxy_class(value,
                                    collection_name=self.collection_name,
                                    db_alias=self.db_alias)

    def validate(self, value):
        if value.grid_id is not None:
            if not isinstance(value, self.proxy_class):
                self.error('FileField only accepts GridFSProxy values')
            if not isinstance(value.grid_id, ObjectId):
                self.error('Invalid GridFSProxy value')


class ImageGridFsProxy(GridFSProxy):
    """
    Proxy for ImageField

    versionadded: 0.6
    """
    def put(self, file_obj, **kwargs):
        """
        Insert a image in database
        applying field properties (size, thumbnail_size)
        """
        field = self.instance._fields[self.key]

        try:
            img = Image.open(file_obj)
        except:
            raise ValidationError('Invalid image')

        if (field.size and (img.size[0] > field.size['width'] or
                            img.size[1] > field.size['height'])):
            size = field.size

            if size['force']:
                img = ImageOps.fit(img,
                                   (size['width'],
                                    size['height']),
                                   Image.ANTIALIAS)
            else:
                img.thumbnail((size['width'],
                               size['height']),
                              Image.ANTIALIAS)

        thumbnail = None
        if field.thumbnail_size:
            size = field.thumbnail_size

            if size['force']:
                thumbnail = ImageOps.fit(
                    img, (size['width'], size['height']), Image.ANTIALIAS)
            else:
                thumbnail = img.copy()
                thumbnail.thumbnail((size['width'],
                                     size['height']),
                                    Image.ANTIALIAS)

        if thumbnail:
            thumb_id = self._put_thumbnail(thumbnail, img.format)
        else:
            thumb_id = None

        w, h = img.size

        io = six.BytesIO()
        img.save(io, img.format)
        io.seek(0)

        return super(ImageGridFsProxy, self).put(io,
                                                 width=w,
                                                 height=h,
                                                 format=img.format,
                                                 thumbnail_id=thumb_id,
                                                 **kwargs)

    def delete(self, *args, **kwargs):
        # deletes thumbnail
        out = self.get()
        if out and out.thumbnail_id:
            self.fs.delete(out.thumbnail_id)

        return super(ImageGridFsProxy, self).delete(*args, **kwargs)

    def _put_thumbnail(self, thumbnail, format, **kwargs):
        w, h = thumbnail.size

        io = six.BytesIO()
        thumbnail.save(io, format)
        io.seek(0)

        return self.fs.put(io, width=w,
                           height=h,
                           format=format,
                           **kwargs)

    @property
    def size(self):
        """
        return a width, height of image
        """
        out = self.get()
        if out:
            return out.width, out.height

    @property
    def format(self):
        """
        return format of image
        ex: PNG, JPEG, GIF, etc
        """
        out = self.get()
        if out:
            return out.format

    @property
    def thumbnail(self):
        """
        return a gridfs.grid_file.GridOut
        representing a thumbnail of Image
        """
        out = self.get()
        if out and out.thumbnail_id:
            return self.fs.get(out.thumbnail_id)

    def write(self, *args, **kwargs):
        raise RuntimeError("Please use \"put\" method instead")

    def writelines(self, *args, **kwargs):
        raise RuntimeError("Please use \"put\" method instead")


class ImproperlyConfigured(Exception):
    pass


class ImageField(FileField):
    """
    A Image File storage field.

    @size (width, height, force):
        max size to store images, if larger will be automatically resized
        ex: size=(800, 600, True)

    @thumbnail (width, height, force):
        size to generate a thumbnail

    .. versionadded:: 0.6
    """
    proxy_class = ImageGridFsProxy

    def __init__(self, size=None, thumbnail_size=None,
                 collection_name='images', **kwargs):
        if not Image:
            raise ImproperlyConfigured("PIL library was not found")

        params_size = ('width', 'height', 'force')
        extra_args = dict(size=size, thumbnail_size=thumbnail_size)
        for att_name, att in extra_args.items():
            if att and (isinstance(att, tuple) or isinstance(att, list)):
                setattr(self, att_name, dict(
                        six.moves.zip_longest(params_size, att)))
            else:
                setattr(self, att_name, None)

        super(ImageField, self).__init__(
            collection_name=collection_name,
            **kwargs)


class GeoPointField(BaseField):
    """A list storing a latitude and longitude.

    .. versionadded:: 0.4
    """

    _geo_index = True

    def validate(self, value):
        """Make sure that a geo-value is of type (x, y)
        """
        if not isinstance(value, (list, tuple)):
            self.error('GeoPointField can only accept tuples or lists '
                       'of (x, y)')

        if not len(value) == 2:
            self.error('Value must be a two-dimensional point')
        if (not isinstance(value[0], (float, int)) and
                not isinstance(value[1], (float, int))):
            self.error('Both values in point must be float or int')


class SequenceField(IntField):
    """Provides a sequental counter (see http://www.mongodb.org/display/DOCS/Object+IDs#ObjectIDs-SequenceNumbers)  # noqa

    .. note::

             Although traditional databases often use increasing sequence
             numbers for primary keys. In MongoDB, the preferred approach is to
             use Object IDs instead.  The concept is that in a very large
             cluster of machines, it is easier to create an object ID than have
             global, uniformly increasing sequence numbers.

    .. versionadded:: 0.5
    """
    def __init__(self, collection_name=None, db_alias=None, *args, **kwargs):
        self.collection_name = collection_name or 'mongoengine.counters'
        self.db_alias = db_alias or DEFAULT_CONNECTION_NAME
        return super(SequenceField, self).__init__(*args, **kwargs)

    def generate_new_value(self):
        """
        Generate and Increment the counter
        """
        sequence_id = "{0}.{1}".format(
            self.owner_document._get_collection_name(), self.name)
        collection = get_db(alias=self.db_alias)[self.collection_name]
        counter = collection.find_and_modify(query={"_id": sequence_id},
                                             update={"$inc": {"next": 1}},
                                             new=True,
                                             upsert=True)
        return counter['next']

    def __get__(self, instance, owner):

        if instance is None:
            return self

        if not instance._data:
            return

        value = instance._data.get(self.name)

        if not value and instance._initialised:
            value = self.generate_new_value()
            instance._data[self.name] = value
            instance._mark_as_changed(self.name)

        return value

    def __set__(self, instance, value):

        if value is None and instance._initialised:
            value = self.generate_new_value()

        return super(SequenceField, self).__set__(instance, value)

    def to_python(self, value):
        if value is None:
            value = self.generate_new_value()
        return value


class UUIDField(BaseField):
    """A UUID field.

    .. versionadded:: 0.6
    """

    def __init__(self, **kwargs):
        super(UUIDField, self).__init__(**kwargs)

    def to_python(self, value):
        if not isinstance(value, six.string_types):
            value = six.text_type(value)
        return uuid.UUID(value)

    def to_mongo(self, value):
        return six.text_type(value)

    def validate(self, value):
        if not isinstance(value, uuid.UUID):
            if not isinstance(value, six.string_types):
                value = six.text_type(value)
            try:
                value = uuid.UUID(value)
            except Exception as exc:
                self.error('Could not convert to UUID: %s' % exc)
