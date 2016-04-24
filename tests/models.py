from datetime import timedelta
from django.db import models
from timeseries.utils import TimeSeriesModel, TimeSeriesQuerySet


class AdQuerySet(TimeSeriesQuerySet):

    def update_rawdata(self, force=False):
        return self.update_timeseries(
            'rawdata', ad_data_collector, force=force
        )

    def update_reports(self, force=False):
        return self.update_timeseries(
            'monthlyreports', report_data_collector, force=force
        )


class AdManager(models.Manager.from_queryset(AdQuerySet)):
    pass


class Ad(models.Model):

    objects = AdManager()


class RawAdData(TimeSeriesModel):

    # update daily N.B integers in seconds also work
    TIMESERIES_INTERVAL = timedelta(days=1)

    NOT_AVAILABLE = -1

    ad = models.ForeignKey(Ad, related_name='rawdata')

    views = models.BigIntegerField(default=NOT_AVAILABLE)
    clicks = models.BigIntegerField(default=NOT_AVAILABLE)


class MonthlyAdReport(TimeSeriesModel):

    TIMESERIES_INTERVAL = timedelta(days=28)

    ad = models.ForeignKey(Ad, related_name='monthlyreports')

    avg_views = models.FloatField()
    avg_clicks = models.FloatField()


def fake_data(obj):
    return {
        'views': obj.id,
        'clicks': obj.id,
        'ad': obj
    }


def fake_report(obj):
    return {
        'avg_views': obj.id,
        'avg_clicks': obj.id,
        'ad': obj
    }


def ad_data_collector(queryset):
    """
        should return an iterable that yields dictionaries of data
        needed to successfully create a RawAdData instance
    """
    for ad in queryset:
        yield fake_data(ad)


def report_data_collector(queryset):
    """
        should return an iterable that yields dictionaries of data
        needed to successfully create a MonthlyAdReport instance
    """
    for ad in queryset:
        yield fake_report(ad)
