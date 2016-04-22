# TimeSeries

[![Build Status](https://travis-ci.org/anthonyalmarza/timeseries.svg?branch=master)](https://travis-ci.org/anthonyalmarza/timeseries)

`timeseries` is a set django application tools designed to facilitate the
collation and maintenance of timeseries data.

## Requirements

Django v1.8+ are supported for projects running on PostgreSQL.

## Installation

`pip install django-timeseries`

## Usage

```python
from datetime import timedelta
from django.db import models
from timeseries.models import TimeSeriesModel, TimeSeriesManager


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

```
