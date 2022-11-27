timedelta-isoformat
===================

The `timedelta-isoformat <https://pypi.org/project/timedelta-isoformat/>`_ library provides supplemental `ISO 8601 duration <https://en.wikipedia.org/wiki/ISO_8601#Durations>`_ support to the `datetime.timedelta <https://docs.python.org/3/library/datetime.html#datetime.timedelta>`_ class.

The library is pure-Python, and does not depend upon regular expressions.

Functionality is provided in a subclass of ``datetime.timedelta`` that implements additional ``isoformat()`` and ``fromisoformat(duration_string)`` methods.

Usage
-----

.. code-block:: pycon

   >>> from timedelta_isoformat import timedelta
   >>> from datetime import datetime
   >>>
   >>> first = datetime(year=2022, month=10, day=2)
   >>> second = datetime(year=2022, month=11, day=27, hour=14)
   >>>
   >>> td = timedelta(seconds=(second - first).total_seconds())
   >>> td.isoformat()
   'P56DT14H'
   >>>
   >>> first + timedelta.fromisoformat('P56DT14H')
   datetime.datetime(2022, 11, 27, 14, 0)
