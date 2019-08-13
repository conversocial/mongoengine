# -*- coding: utf-8 -*-

import unittest
from distutils.version import StrictVersion

from mongoengine import connect, Q, IntField, StringField, Document
from mongoengine.connection import register_db
from mongoengine.django.shortcuts import get_document_or_404

from django.http import Http404
from django.template import Context, Template
from django.conf import settings
from django.core.paginator import Paginator
from django import get_version

if StrictVersion(get_version()) > StrictVersion('1.6'):
    from django.core.wsgi import get_wsgi_application

    TEMPLATES = [
        {
            'BACKEND': 'django.template.backends.django.DjangoTemplates',
            'DIRS': [],
            'APP_DIRS': True,
            'OPTIONS': {
                # ... some options here ...
            },
        },
    ]
    settings.configure(TEMPLATES=TEMPLATES)
    get_wsgi_application()
else:
    settings.configure()


class QuerySetTest(unittest.TestCase):
    def setUp(self):
        connect(alias='default', host='mongo')
        register_db('mongoenginetest')

        class Person(Document):
            name = StringField()
            age = IntField()
        self.Person = Person

    def test_order_by_in_django_template(self):
        """Ensure that QuerySets are properly ordered in Django template.
        """
        self.Person.drop_collection()

        self.Person(name="A", age=20).save()
        self.Person(name="D", age=10).save()
        self.Person(name="B", age=40).save()
        self.Person(name="C", age=30).save()

        t = Template("{% for o in ol %}{{ o.name }}-{{ o.age }}:{% endfor %}")

        d = {"ol": self.Person.objects.order_by('-name')}
        self.assertEqual(t.render(Context(d)), u'D-10:C-30:B-40:A-20:')
        d = {"ol": self.Person.objects.order_by('+name')}
        self.assertEqual(t.render(Context(d)), u'A-20:B-40:C-30:D-10:')
        d = {"ol": self.Person.objects.order_by('-age')}
        self.assertEqual(t.render(Context(d)), u'B-40:C-30:A-20:D-10:')
        d = {"ol": self.Person.objects.order_by('+age')}
        self.assertEqual(t.render(Context(d)), u'D-10:A-20:C-30:B-40:')

        self.Person.drop_collection()

    def test_q_object_filter_in_template(self):

        self.Person.drop_collection()

        self.Person(name="A", age=20).save()
        self.Person(name="D", age=10).save()
        self.Person(name="B", age=40).save()
        self.Person(name="C", age=30).save()

        t = Template("{% for o in ol %}{{ o.name }}-{{ o.age }}:{% endfor %}")

        d = {"ol": self.Person.objects.filter(Q(age=10) | Q(name="C"))}
        self.assertEqual(t.render(Context(d)), 'D-10:C-30:')

        # Check double rendering doesn't throw an error
        self.assertEqual(t.render(Context(d)), 'D-10:C-30:')

    def test_get_document_or_404(self):
        p = self.Person(name="G404")
        p.save()

        self.assertRaises(Http404, get_document_or_404, self.Person, pk='1234')
        self.assertEqual(p, get_document_or_404(self.Person, pk=p.pk))

    def test_pagination(self):
        """Ensure that Pagination works as expected
        """
        class Page(Document):
            name = StringField()

        Page.drop_collection()

        for i in range(1, 11):
            Page(name=str(i)).save()

        paginator = Paginator(Page.objects.all(), 2)

        t = Template("{% for i in page.object_list  %}{{ i.name }}:{% endfor %}")  # noqa
        for p in paginator.page_range:
            d = {"page": paginator.page(p)}
            end = p * 2
            start = end - 1
            self.assertEqual(t.render(Context(d)), u'%d:%d:' % (start, end))


if __name__ == '__main__':
    unittest.main()
