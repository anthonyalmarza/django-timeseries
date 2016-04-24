TimeSeries
==========

|Build Status|

|Coverage Status|

``timeseries`` is a set django application tools designed to facilitate
the collation and maintenance of timeseries data.

Requirements
------------

Django versions 1.8+ are supported for projects running on PostgreSQL.

Installation
------------

``pip install django-timeseries``

Usage
-----

.. code:: python

    from datetime import timedelta
    from django.db import models
    from timeseries.utils import TimeSeriesModel, TimeSeriesManager


    class Ad(models.Model):

        objects = TimeSeriesManager()


    class RawAdData(TimeSeriesModel):

        TIMESERIES_INTERVAL = timedelta(days=1)  # update daily N.B integers in seconds also work

        NOT_AVAILABLE = -1

        ad = models.ForeignKey(Ad, related_name='rawdata')

        views = models.BigIntegerField(default=NOT_AVAILABLE)
        clicks = models.BigIntegerField(default=NOT_AVAILABLE)


    class MonthlyAdReport(TimeSeriesModel):

        TIMESERIES_INTERVAL = timedelta(days=28)

        ad = models.ForeignKey(Ad, related_name='monthlyreports')

        avg_view_growth = models.FloatField()
        avg_click_growth = models.FloatField()


    def ad_data_collector(queryset):
        """
            should return an iterable that yields dictionaries of data
            needed to successfully create a RawAdData instance
        """
        return ...


    def report_data_collector(queryset):
        """
            should return an iterable that yields dictionaries of data
            needed to successfully create a MonthlyAdReport instance
        """
        return ...


    # in a shell
    >>> Ad.objects.update_timeseries('rawdata', ad_data_collector)
    # this return the results of a bulk_create call from the RawAdData manager
    # for ads that hadn't been updated in the last day

    >>> Ad.objects.update_timeseries('monthlyreports', report_data_collector)
    # this return the results of a bulk_create call from the MonthlyAdReport
    # manager for ads that hadn't had a report generated in the last 28 days

    >>> ad = Ad.objects.prefetch_latest('rawdata', 'monthlyreports').first()
    >>> print ad.latest_rawaddata, ad.latest_monthlyreports

TimeSeries QuerySet Methods
---------------------------

``timeseries.utils.TimeSeriesQuerySet``

Adds 4 main methods to the Django QuerySet API that can be used to
update and maintain timeseries data. These methods include:

-  prefetch\_latest
-  filter\_outdated
-  last\_updated
-  update\_timeseries

``update_timeseries``
~~~~~~~~~~~~~~~~~~~~~

Inputs: ``related_name``, ``collector``, optional ``force``

Returns: list of instatiated related models.

Updates the queryset's related model table (as given by related\_name)
using a provider "collector" callable.

"collector" must take a queryset of the referenced models as its only
argument. It must also return an iterable of dictionaries that can be
used to construct and save instances of the related model.

N.B. Only instances that have outdated data will be updated unless
explicitly forced using the "force" keyword argument.

``filter_outdated``
~~~~~~~~~~~~~~~~~~~

Inputs: ``*related_names``

Returns: queryset

Returns a queryset that will yield the model instances that have
"outdated" data associated to reverse related model as given by the
specified related\_name.

``last_updated``
~~~~~~~~~~~~~~~~

Inputs: ``*related_names``

Returns: queryset

Annotates the created timestamp of the latest related instance as given
by the reverse relation's related\_name.

Usage:

.. code:: python

        ad = Ad.objects.last_updated('rawdata').first()
        # assuming there's data related to ad
        print ad.rawdata_last_updated
        # this will print the timestamp of when the associated data was
        # last updated

``prefetch_latest``
~~~~~~~~~~~~~~~~~~~

Inputs: ``*related_names``

Returns: queryset

Exposes the latest associated reverse relation.

Usage:

.. code:: python

        ad = Ad.objects.prefetch_latest('rawdata', 'monthlyreports').first()
        print ad.latest_rawaddata, ad.latest_monthlyreports
        # this will print the reprs of the latest associated data
        # instances

Other Utilities
---------------

``LatestQ``
~~~~~~~~~~~

``timeseries.utils``

Inputs: ``related_name``, ``**kwargs``

Returns: django.db.models.Q instance

Constructs a django.db.models.Q instance that allows queries to be
executed against the latest associated reverse relation.

N.B. this method is designed to be used in conjunction with
timeseries.utils.TimeSeriesQuerySet.last\_updated.

Usage:

.. code:: python

    Ad.objects.last_updated('rawdata').filter(
        LatestQ('rawdata', views__gt=1000)
    )

.. |Build Status| image:: https://travis-ci.org/anthonyalmarza/timeseries.svg?branch=master
   :target: https://travis-ci.org/anthonyalmarza/timeseries
.. |Coverage Status| image:: https://coveralls.io/repos/github/anthonyalmarza/timeseries/badge.svg?branch=master
   :target: https://coveralls.io/github/anthonyalmarza/timeseries?branch=master
