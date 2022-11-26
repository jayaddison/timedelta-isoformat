timedelta-isoformat
===================

The `timedelta-isoformat <https://pypi.org/project/timedelta-isoformat`_ library provides supplemental `ISO 8601 duration <https://en.wikipedia.org/wiki/ISO_8601#Durations`_ support to the `datetime.timedelta <https://docs.python.org/3/library/datetime.html#datetime.timedelta>` class.

The library is pure-Python, and does not depend upon regular expressions.

Functionality is provided in a subclass of ``datetime.timedelta`` that implements additional ``isoformat()`` and ``fromisoformat(duration_string)`` methods.

Usage
-----

.. code-block:: pycon

   >>> from timedelta_isoformat import timedelta
   >>> from datetime import datetime
   >>>
   >>> epoch = datetime(year=2022, month=10, day=2)
   >>> now = datetime.utcnow()
   >>>
   >>> td = timedelta(seconds=(now - epoch).total_seconds())
   >>> td.isoformat()
   'P55DT17H28M51S'
   >>>
   >>> epoch + timedelta.fromisoformat('P55DT17H28M51S')
   datetime.datetime(2022, 11, 26, 17, 28, 51)
