import unittest

if __name__ == '__main__':
    suite = unittest.TestSuite()
    for test in ['connection', 'fields', 'queryset', 'dereference',
                 'document', 'dynamic_document', 'signals',
                 'django_compatibility']:
        suite.addTest(unittest.defaultTestLoader.loadTestsFromName(test))
    unittest.TextTestRunner().run(suite)
