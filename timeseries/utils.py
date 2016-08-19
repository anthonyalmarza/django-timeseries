from datetime import datetime, timedelta
from django.db import models
from django.db.models import Prefetch, Max, Q, F
from django.db.models.fields.related import ManyToOneRel
from django.db.models.options import FieldDoesNotExist

try:

    from django.utils.timezone import utcnow

except ImportError:

    from django.utils.timezone import utc

    def utcnow():
        return datetime.utcnow().replace(tzinfo=utc)


class TimeSeriesQuerySet(models.QuerySet):
    """
        Adds 4 main methods to the Django QuerySet API that can be used to
        update and maintain timeseries data. These methods include:
            prefetch_latest
            filter_outdated
            last_updated
            update_timeseries
    """

    def __init__(self, *args, **kwargs):
        super(TimeSeriesQuerySet, self).__init__(*args, **kwargs)

        self.latest_registry = set()
        self._latest_included = False

    def _clone(self, **kwargs):
        # overriding _clone is required so retain the latest_registry set
        # information
        clone = super(TimeSeriesQuerySet, self)._clone(**kwargs)
        clone.latest_registry = self.latest_registry.copy()
        clone._latest_included = self._latest_included
        return clone

    def prefetch_latest(self, *related_names):
        """
            Exposes the latest associated reverse relation.

            Adds a query per related name.
        """
        prefetch_set = []
        for related_name in set(related_names):
            rev_rel = get_reverse_relation(self.model, related_name)

            field_name = rev_rel.field.name
            RelatedModel = rev_rel.field.model

            attr_name = 'latest_{}'.format(related_name)
            prefetch = Prefetch(
                related_name,
                queryset=RelatedModel.objects.filter(
                    **{field_name + '__in': self}
                ).order_by(field_name, '-created').distinct(field_name),
                to_attr=attr_name
            )
            prefetch_set.append(prefetch)
            self.latest_registry.add(attr_name)

        return self.prefetch_related(*prefetch_set)

    def parse_latest(self, res):
        """
            Checks the prefetched data and assigns either the found object or
            None to the latest_\{related_name\} attribute on the "owning"
            model instance.

            res: a model instance representing the object that owns
                 (by foreign key) the prefetched data.
        """
        # loops over the registered to_attr names to access and check the data
        for name in self.latest_registry:
            value = getattr(res, name)
            if value:
                value = value[0]
            else:
                value = None
            setattr(res, name, value)
        self._latest_included = True

    def get(self, *args, **kwargs):
        # overriding get is required so to parse any prefetched latest results
        res = super(TimeSeriesQuerySet, self).get(*args, **kwargs)
        self.parse_latest(res)
        return res

    def __iter__(self):
        # Overrides the base __iter__ functionality so to
        super_iter = super(TimeSeriesQuerySet, self).__iter__()
        if self._latest_included:
            for res in super_iter:
                yield res
        else:
            for res in super_iter:
                if isinstance(res, self.model):
                    self.parse_latest(res)
                yield res

    def last_updated(self, related_name):
        """
            Annotates the created timestamp of the latest related instance as
            given by the reverse relation's related_name.

            Usage:
                ad = Ad.objects.last_updated('rawdata').first()
                # assuming there's data related to ad
                print ad.rawdata_last_updated
                # prints the timestamp associated to when the ad's raw data was
                # last updated
        """
        return self.annotate(
            **{
                related_name + '_last_updated': Max(
                    related_name + '__created'
                )
            }
        )

    def filter_outdated(self, related_name):
        """
            Returns a queryset that will yield the model instances that have
            "outdated" data associated to reverse related model as given by
            the specified related_name
        """
        rev_rel = get_reverse_relation(self.model, related_name)
        RelatedModel = rev_rel.field.model
        is_safe_cutoff = utcnow() - get_interval(RelatedModel)
        annotated_queryset = self.last_updated(related_name)
        last_updated_query = {
            '{}_last_updated__lt'.format(related_name): is_safe_cutoff
        }
        return annotated_queryset.filter(
            Q(**last_updated_query) |
            Q(**{'{}_last_updated__isnull'.format(related_name): True})
        )

    def update_timeseries(self, related_name, collector, force=False):
        """
            Updates the queryset's related model table
            (as given by related_name) using a provider "collector" callable.

            "collector" must take a queryset of the referenced models as its
            only argument. It must also return an iterable of dictionaries
            that can be used to construct and save instances of the related
            model.

            N.B. Only instances that have outdated data will be updated unless
            explicitly forced using the "force" keyword argument.
        """
        # N.B. runs two queries as such is subject to errors resulting from
        # multitenancy race conditions.
        rev_rel = get_reverse_relation(self.model, related_name)
        RelatedModel = rev_rel.field.model
        if force:
            models = self
        else:
            models = self.filter_outdated(related_name)

        results = collector(models)
        instances = [RelatedModel(**data) for data in results]
        output = RelatedModel.objects.bulk_create(instances)
        return output


class TimeSeriesManager(models.Manager.from_queryset(TimeSeriesQuerySet)):
    pass


class TimeSeriesModel(models.Model):
    """
        Abstract model that can be inherited from to facilitate building out
        your timeseries data framework.

        N.B. TimeSeries models should have a ForeignKey reference to an
        "owning" model and TIMESERIES_INTERVAL timedelta instance.
    """

    created = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        abstract = True
        ordering = ('-created', )
        get_latest_by = 'created'


def LatestQ(related_name, **kwargs):
    """
        Constructs a django.db.models.Q instance that allows queries to be
        executed against the latest associated reverse relation.

        N.B. this method is designed to be used in conjunction with
        timeseries.utils.TimeSeriesQuerySet.last_updated.

        Usage:
        Ad.objects.last_updated('rawdata').filter(
            LatestQ('rawdata', views__gt=1000)
        )
    """
    parsed_kwargs = {
        related_name + "__created": F(related_name + '_last_updated')
    }
    for key, value in kwargs.iteritems():
        parsed_kwargs[related_name + '__' + key] = value
    return Q(**parsed_kwargs)


def q_factory(related_name, q_func=LatestQ):
    """
        Helper function that wraps LatestQ

        Usage:

        LatestRawDataQ = q_factory('rawdata')

        Ad.objects.last_updated('rawdata').filter(
            LatestRawDataQ(views__gt=1000)
        )

    """
    def wrapper(**kwargs):
        return q_func(related_name, **kwargs)
    return wrapper


def get_reverse_relation(model, related_name):
    """
        Helper function that returns a reverse relation instance for a
        given model and the related_name for the reverse relation.

        model: subclass of django.db.models.Model
        related_name: str
    """
    return model._meta.fields_map.get(related_name)


def check_reverse_relation(model, related_name):
    """
        Helper method to check if a given model related_name pair return a
        reverse relation instance that is associated by a ForeignKey.

        model: subclass of django.db.models.Model
        related_name: str
    """
    rel = get_reverse_relation(model, related_name)
    if rel is None:
        raise NotImplementedError(
            '{} does not have a reverse relation by the name "{}"'.format(
                model.__name__, related_name
            )
        )
    elif not isinstance(rel, ManyToOneRel):
        raise TypeError(
            'The reverse relation "{}" on {}.{} is not a ForeignKey.'
            'Timeseries only works with ForeignKey reverse relations.'.format(
                related_name, rel.field.model.__name__, rel.field.name
            )
        )

    return rel


def check_created_field(model):
    """
        Helper method to check if a given model has a created field.

        model must me a class that inherits from django.db.models.Model
    """
    try:
        created = model._meta.get_field_by_name('created')
        assert isinstance(created, models.DateTimeField)
    except FieldDoesNotExist as err:
        raise FieldDoesNotExist(
            'Reverse related model {} must have a created field.\n'.format(
                model.__name__
            ) + str(err)
        )
    except AssertionError:
        raise TypeError(
            '{}.created field must be a DateTimeField'.format(model.__name__)
        )


def get_interval(model):
    """
        Helper method to facilitate the retrieval of TIMESERIES_INTERVAL.

        model must be a Django model class.
    """
    interval = model.TIMESERIES_INTERVAL
    if isinstance(interval, timedelta):
        return interval
    elif isinstance(interval, (int, float, basestring)):
        return timedelta(seconds=int(interval))
    raise ValueError(
        'TIMESERIES_INTERVAL must either be in seconds or an instance of '
        'datetime.timedelta'
    )
