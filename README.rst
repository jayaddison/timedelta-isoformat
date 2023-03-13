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

Design decisions
----------------

A variety of ISO 8601 duration parsers exist across a range of programming languages, and many of them have made slightly different design decisions.

Some of the significant design decisions made within this library are:

* Values in parsed duration strings must be zero-or-greater (``PT1H`` is considered valid; ``P-2D`` is not)
* Empty time segments at the end of duration strings are allowed (``P1DT`` is considered valid)
* Measurement limits are checked within date/time segments (``PT20:59:01`` is within limits; ``PT20:60:01`` is not)
* Measurement values are parsed into floating-point values (at the time of writing, precise procedural algorithms to parse base-ten strings into integers for large inputs are not practical -- or not widely known)
* When inputs are reliably known to be of correct type and format, assertions should be safe to remove (for example, by including the `-O command-line flag when invoking the Python interpreter <https://docs.python.org/3/using/cmdline.html#cmdoption-O>`_) to improve runtime performance
