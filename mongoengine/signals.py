# -*- coding: utf-8 -*-
from blinker import Namespace

__all__ = ['pre_connect', 'post_connect', 'pre_init', 'post_init',
           'pre_save', 'post_save', 'pre_delete', 'post_delete']

signals_available = True

# the namespace for code signals.  If you are not mongoengine code, do
# not put signals in here.  Create your own namespace instead.
_signals = Namespace()

pre_connect = _signals.signal('pre_connect')
post_connect = _signals.signal('post_connect')
pre_init = _signals.signal('pre_init')
post_init = _signals.signal('post_init')
pre_save = _signals.signal('pre_save')
post_save = _signals.signal('post_save')
pre_delete = _signals.signal('pre_delete')
post_delete = _signals.signal('post_delete')
pre_bulk_insert = _signals.signal('pre_bulk_insert')
post_bulk_insert = _signals.signal('post_bulk_insert')
