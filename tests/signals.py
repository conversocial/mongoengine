# -*- coding: utf-8 -*-
import unittest

from mongoengine import connect, Document, StringField
from mongoengine import signals
from mongoengine.connection import register_db, disconnect

signal_output = []


class BaseSignalTests(unittest.TestCase):

    maxDiff = None

    def get_signal_output(self, fn, *args, **kwargs):
        # Flush any existing signal output
        global signal_output
        signal_output = []
        fn(*args, **kwargs)
        return signal_output


class ConnectSignalTests(BaseSignalTests):
    """
    Testing signals before/after connecting.
    """

    def setUp(self):
        # Save up the number of connected signals so that we can check at
        # the end that all the signals we register get properly unregistered
        self.pre_signals = (
            len(signals.pre_connect.receivers),
            len(signals.post_connect.receivers),
        )

        self.pre_connect = lambda sender, settings: signal_output.append(
            'pre_connect: sender={sender} settings={settings!r}'.format(
                sender=sender,
                settings=sorted(settings.keys()),
            )
        )
        self.post_connect = lambda sender, settings, connection: signal_output.append(
            'post_connect: sender={sender} settings={settings!r} connection={connection!r}'.format(
                sender=sender,
                settings=sorted(settings.keys()),
                connection=type(connection),
            )
        )
        signals.pre_connect.connect(self.pre_connect)
        signals.post_connect.connect(self.post_connect)

        # make sure we're not connected already
        disconnect()
        disconnect('nondefault')

    def tearDown(self):
        signals.pre_connect.disconnect(self.pre_connect)
        signals.post_connect.disconnect(self.post_connect)
        # Check that all our signals got disconnected properly.
        post_signals = (
            len(signals.pre_connect.receivers),
            len(signals.post_connect.receivers),
        )
        self.assertEqual(self.pre_signals, post_signals)

    def test_new_connection(self):
        """ Call to connect() should fire the pre/post signals. """
        self.assertEqual(self.get_signal_output(connect), [
            "pre_connect: sender=default settings=['host', 'port', 'read_preference']",
            "post_connect: sender=default settings=['host', 'port', 'read_preference'] connection=<class 'pymongo.mongo_client.MongoClient'>",
        ])
        self.assertEqual(self.get_signal_output(connect, 'nondefault'), [
            "pre_connect: sender=nondefault settings=['host', 'port', 'read_preference']",
            "post_connect: sender=nondefault settings=['host', 'port', 'read_preference'] connection=<class 'pymongo.mongo_client.MongoClient'>",
        ])

    def test_unknown_alias_connection(self):
        """ Call to connect() should not fire the pre/post signals for unknown db alias. """

    def test_already_connected(self):
        """ Repeat call to connect() should not fire the pre/post signals. """
        connect()
        self.assertEqual(self.get_signal_output(connect), [])


class DocumentSignalTests(BaseSignalTests):
    """
    Testing signals before/after saving and deleting.
    """

    def setUp(self):
        connect()
        register_db('mongoenginetest')

        class Author(Document):
            name = StringField()

            def __unicode__(self):
                return self.name

            @classmethod
            def pre_init(cls, sender, document, *args, **kwargs):
                signal_output.append('pre_init signal, %s' % cls.__name__)
                signal_output.append(str(kwargs['values']))

            @classmethod
            def post_init(cls, sender, document, **kwargs):
                signal_output.append('post_init signal, %s' % document)

            @classmethod
            def pre_save(cls, sender, document, **kwargs):
                signal_output.append('pre_save signal, %s' % document)

            @classmethod
            def post_save(cls, sender, document, **kwargs):
                signal_output.append('post_save signal, %s' % document)
                if 'created' in kwargs:
                    if kwargs['created']:
                        signal_output.append('Is created')
                    else:
                        signal_output.append('Is updated')

            @classmethod
            def pre_delete(cls, sender, document, **kwargs):
                signal_output.append('pre_delete signal, %s' % document)

            @classmethod
            def post_delete(cls, sender, document, **kwargs):
                signal_output.append('post_delete signal, %s' % document)

            @classmethod
            def pre_bulk_insert(cls, sender, documents, **kwargs):
                signal_output.append('pre_bulk_insert signal, %s' % documents)

            @classmethod
            def post_bulk_insert(cls, sender, documents, **kwargs):
                signal_output.append('post_bulk_insert signal, %s' % documents)
                if kwargs.get('loaded', False):
                    signal_output.append('Is loaded')
                else:
                    signal_output.append('Not loaded')
        self.Author = Author

        class Another(Document):
            name = StringField()

            def __unicode__(self):
                return self.name

            @classmethod
            def pre_init(cls, sender, document, **kwargs):
                signal_output.append(
                    'pre_init Another signal, %s' % cls.__name__)
                signal_output.append(str(kwargs['values']))

            @classmethod
            def post_init(cls, sender, document, **kwargs):
                signal_output.append('post_init Another signal, %s' % document)

            @classmethod
            def pre_save(cls, sender, document, **kwargs):
                signal_output.append('pre_save Another signal, %s' % document)

            @classmethod
            def post_save(cls, sender, document, **kwargs):
                signal_output.append('post_save Another signal, %s' % document)
                if 'created' in kwargs:
                    if kwargs['created']:
                        signal_output.append('Is created')
                    else:
                        signal_output.append('Is updated')

            @classmethod
            def pre_delete(cls, sender, document, **kwargs):
                signal_output.append('pre_delete Another signal, %s' % document)

            @classmethod
            def post_delete(cls, sender, document, **kwargs):
                signal_output.append(
                    'post_delete Another signal, %s' % document)

        self.Another = Another
        # Save up the number of connected signals so that we can check at
        # the end that all the signals we register get properly unregistered
        self.pre_signals = (
            len(signals.pre_init.receivers),
            len(signals.post_init.receivers),
            len(signals.pre_save.receivers),
            len(signals.post_save.receivers),
            len(signals.pre_delete.receivers),
            len(signals.post_delete.receivers),
            len(signals.pre_bulk_insert.receivers),
            len(signals.post_bulk_insert.receivers),
        )

        signals.pre_init.connect(Author.pre_init, sender=Author)
        signals.post_init.connect(Author.post_init, sender=Author)
        signals.pre_save.connect(Author.pre_save, sender=Author)
        signals.post_save.connect(Author.post_save, sender=Author)
        signals.pre_delete.connect(Author.pre_delete, sender=Author)
        signals.post_delete.connect(Author.post_delete, sender=Author)
        signals.pre_bulk_insert.connect(Author.pre_bulk_insert, sender=Author)
        signals.post_bulk_insert.connect(Author.post_bulk_insert, sender=Author)

        signals.pre_init.connect(Another.pre_init, sender=Another)
        signals.post_init.connect(Another.post_init, sender=Another)
        signals.pre_save.connect(Another.pre_save, sender=Another)
        signals.post_save.connect(Another.post_save, sender=Another)
        signals.pre_delete.connect(Another.pre_delete, sender=Another)
        signals.post_delete.connect(Another.post_delete, sender=Another)

    def tearDown(self):
        signals.pre_init.disconnect(self.Author.pre_init)
        signals.post_init.disconnect(self.Author.post_init)
        signals.post_delete.disconnect(self.Author.post_delete)
        signals.pre_delete.disconnect(self.Author.pre_delete)
        signals.post_save.disconnect(self.Author.post_save)
        signals.pre_save.disconnect(self.Author.pre_save)
        signals.pre_bulk_insert.disconnect(self.Author.pre_bulk_insert)
        signals.post_bulk_insert.disconnect(self.Author.post_bulk_insert)

        signals.pre_init.disconnect(self.Another.pre_init)
        signals.post_init.disconnect(self.Another.post_init)
        signals.post_delete.disconnect(self.Another.post_delete)
        signals.pre_delete.disconnect(self.Another.pre_delete)
        signals.post_save.disconnect(self.Another.post_save)
        signals.pre_save.disconnect(self.Another.pre_save)

        # Check that all our signals got disconnected properly.
        post_signals = (
            len(signals.pre_init.receivers),
            len(signals.post_init.receivers),
            len(signals.pre_save.receivers),
            len(signals.post_save.receivers),
            len(signals.pre_delete.receivers),
            len(signals.post_delete.receivers),
            len(signals.pre_bulk_insert.receivers),
            len(signals.post_bulk_insert.receivers),
        )

        self.assertEqual(self.pre_signals, post_signals)

    def test_model_signals(self):
        """ Model saves should throw some signals. """

        def create_author():
            self.Author(name='Bill Shakespeare')

        def bulk_create_author_with_load():
            a1 = self.Author(name='Bill Shakespeare')
            self.Author.objects.insert([a1], load_bulk=True)

        def bulk_create_author_without_load():
            a1 = self.Author(name='Bill Shakespeare')
            self.Author.objects.insert([a1], load_bulk=False)

        self.assertEqual(self.get_signal_output(create_author), [
            "pre_init signal, Author",
            "{'name': 'Bill Shakespeare'}",
            "post_init signal, Bill Shakespeare",
        ])

        a1 = self.Author(name='Bill Shakespeare')
        self.assertEqual(self.get_signal_output(a1.save), [
            "pre_save signal, Bill Shakespeare",
            "post_save signal, Bill Shakespeare",
            "Is created"
        ])

        a1.reload()
        a1.name = 'William Shakespeare'
        self.assertEqual(self.get_signal_output(a1.save), [
            "pre_save signal, William Shakespeare",
            "post_save signal, William Shakespeare",
            "Is updated"
        ])

        self.assertEqual(self.get_signal_output(a1.delete), [
            'pre_delete signal, William Shakespeare',
            'post_delete signal, William Shakespeare',
        ])

        signal_output = self.get_signal_output(bulk_create_author_with_load)

        # The output of this signal is not entirely deterministic. The reloaded
        # object will have an object ID. Hence, we only check part of the output
        self.assertEquals(
            signal_output[3],
            "pre_bulk_insert signal, [<Author: Bill Shakespeare>]")
        self.assertEquals(
            signal_output[-2:],
            ["post_bulk_insert signal, [<Author: Bill Shakespeare>]",
             "Is loaded"])

        self.assertEqual(
            self.get_signal_output(bulk_create_author_without_load),
            ["pre_init signal, Author",
             "{'name': 'Bill Shakespeare'}",
             "post_init signal, Bill Shakespeare",
             "pre_bulk_insert signal, [<Author: Bill Shakespeare>]",
             "post_bulk_insert signal, [<Author: Bill Shakespeare>]",
             "Not loaded"])

        self.Author.objects.delete()


if __name__ == '__main__':
    unittest.main()
