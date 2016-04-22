from .models import Ad, RawAdData, MonthlyAdReport

from datetime import timedelta
from django.test import TestCase
from timeseries.utils import utcnow

import django
import mock


def time_machine(_time):
    return mock.patch('timeseries.models.utcnow', return_value=_time)


class TimeSeriesTests(TestCase):

    def setUp(self):
        if django.VERSION[:2] < (1, 9):
            for _ in range(10):
                Ad.objects.create()
        else:
            ads = [Ad() for _ in range(10)]
            Ad.objects.bulk_create(ads)

    def test_setup(self):
        self.assertEqual(Ad.objects.count(), 10)

    def test_update_timeseries(self):
        just_before = utcnow()

        output = Ad.objects.update_rawdata()
        self.assertEqual(RawAdData.objects.count(), 10)
        self.assertIsInstance(output, (list, tuple))

        output = Ad.objects.update_reports()
        self.assertEqual(MonthlyAdReport.objects.count(), 10)
        self.assertIsInstance(output, (list, tuple))

        just_after = utcnow()

        # calling update_raw data should not create more RawAdData instances
        Ad.objects.update_rawdata()
        self.assertEqual(RawAdData.objects.count(), 10)

        # calling update_raw data should not create more RawAdData instances
        Ad.objects.update_reports()
        self.assertEqual(MonthlyAdReport.objects.count(), 10)

        tomorrow = just_after + RawAdData.TIMESERIES_INTERVAL
        almost_tomorrow = just_before + RawAdData.TIMESERIES_INTERVAL
        next_week = just_after + timedelta(days=7)
        next_month = just_after + MonthlyAdReport.TIMESERIES_INTERVAL
        almost_next_month = just_before + MonthlyAdReport.TIMESERIES_INTERVAL

        with time_machine(almost_tomorrow):
            Ad.objects.update_rawdata()
            self.assertEqual(RawAdData.objects.count(), 10)

            Ad.objects.update_reports()
            self.assertEqual(MonthlyAdReport.objects.count(), 10)

        with time_machine(tomorrow):
            Ad.objects.update_rawdata()
            self.assertEqual(RawAdData.objects.count(), 20)

            Ad.objects.update_reports()
            self.assertEqual(MonthlyAdReport.objects.count(), 10)

        with time_machine(next_week):
            Ad.objects.update_reports()
            self.assertEqual(MonthlyAdReport.objects.count(), 10)

        with time_machine(almost_next_month):
            Ad.objects.update_reports()
            self.assertEqual(MonthlyAdReport.objects.count(), 10)

        with time_machine(next_month):
            Ad.objects.update_reports()
            self.assertEqual(MonthlyAdReport.objects.count(), 20)

    def test_prefetch_latest_filter(self):
        just_before = utcnow()
        for _ in range(10):
            diff = RawAdData.TIMESERIES_INTERVAL + timedelta(seconds=0.1)
            with time_machine(just_before + diff):
                Ad.objects.update_rawdata()

        for _ in range(10):
            diff = MonthlyAdReport.TIMESERIES_INTERVAL + timedelta(seconds=0.1)
            with time_machine(just_before + diff):
                Ad.objects.update_reports()

        queryset = Ad.objects.prefetch_latest('rawdata', 'monthlyreports')
        self.assertTrue(hasattr(queryset, 'latest_registry'))
        attr_names = (
            'latest_rawdata', 'latest_monthlyreports'
        )
        for name in attr_names:
            self.assertTrue(
                name in queryset.latest_registry
            )

        self.check_prefetch_latest_queryset(queryset, 3)

        # test it on a slice
        self.check_prefetch_latest_queryset(queryset[:3], 0)

        # test it where there's a few clones involved
        self.check_prefetch_latest_queryset(
            Ad.objects.prefetch_latest(
                'rawdata', 'monthlyreports'
            ).filter(
                id__in=Ad.objects.all().order_by('id')[:5]
            ).exclude(
                id__in=Ad.objects.all().order_by('id')[:2]
            ), 3
        )

        # try prefetching twice
        with self.assertRaises(ValueError):
            # this ValueError is default django functionality
            self.check_prefetch_latest_queryset(
                queryset.filter(
                    id__in=Ad.objects.all().order_by('id')[:5]
                ).prefetch_latest('rawdata', 'monthlyreports'),

                None
            )

    def check_prefetch_latest_queryset(self, queryset, num_quiries=None):
        if num_quiries is not None:
            with self.assertNumQueries(num_quiries):
                list(queryset)

        for ad in queryset:
            self.assertTrue(hasattr(ad, 'latest_rawdata'))
            self.assertTrue(hasattr(ad, 'latest_monthlyreports'))

            self.assertEqual(
                ad.latest_rawdata,
                ad.rawdata.latest()
            )
            self.assertEqual(
                ad.latest_monthlyreports,
                ad.monthlyreports.latest()
            )

    def test_prefetch_lastest_get(self):
        Ad.objects.update_rawdata()
        ad = Ad.objects.prefetch_latest('rawdata', 'monthlyreports').get(id=1)
        self.assertTrue(hasattr(ad, 'latest_rawdata'))
        self.assertTrue(hasattr(ad, 'latest_monthlyreports'))

        self.assertEqual(
            ad.latest_rawdata,
            ad.rawdata.latest()
        )
        self.assertIsNone(ad.latest_monthlyreports)
