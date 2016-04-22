from .utils import utcnow, get_reverse_relation, get_interval
from django.db import models
from django.db.models import Prefetch, Max, Q, F


class TimeSeriesQuerySet(models.QuerySet):
    """
    """

    def __init__(self, *args, **kwargs):
        super(TimeSeriesQuerySet, self).__init__(*args, **kwargs)
        self.latest_registry = set()
        self._latest_included = False

    def _clone(self, **kwargs):
        clone = super(TimeSeriesQuerySet, self)._clone(**kwargs)
        clone.latest_registry = self.latest_registry.copy()
        clone._latest_included = self._latest_included
        return clone

    def reverse_relation(self, related_name):
        """
        """
        return get_reverse_relation(self.model, related_name)

    def prefetch_latest(self, *related_names):
        """
        """
        prefetch_set = []
        for related_name in set(related_names):
            rev_rel = self.reverse_relation(related_name)

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

    def include_latest(self, res):
        for name in self.latest_registry:
            value = getattr(res, name)
            if value:
                value = value[0]
            else:
                value = None
            setattr(res, name, value)
        self._latest_included = True

    def get(self, *args, **kwargs):
        res = super(TimeSeriesQuerySet, self).get(*args, **kwargs)
        self.include_latest(res)
        return res

    def __iter__(self):
        """
        """
        super_iter = super(TimeSeriesQuerySet, self).__iter__()
        if self._latest_included:
            for res in super_iter:
                yield res
        else:
            for res in super_iter:
                self.include_latest(res)
                yield res

    def annotate_last_updated(self, related_name):
        """
        """
        return self.annotate(
            **{
                related_name + '_last_updated': Max(
                    related_name + '__created'
                )
            }
        )

    def requiring_update(self, related_name):
        """
        """
        rev_rel = self.reverse_relation(related_name)
        RelatedModel = rev_rel.field.model
        is_safe_cutoff = utcnow() - get_interval(RelatedModel)
        annotated_queryset = self.annotate_last_updated(related_name)
        last_updated_query = {
            '{}_last_updated__lt'.format(related_name): is_safe_cutoff
        }
        return annotated_queryset.filter(
            Q(**last_updated_query) |
            Q(**{'{}_last_updated__isnull'.format(related_name): True})
        )

    def update_timeseries(self, related_name, collector, force=False):
        """
        """
        rev_rel = self.reverse_relation(related_name)
        RelatedModel = rev_rel.field.model
        if force:
            models = self
        else:
            models = self.requiring_update(related_name)

        results = collector(models)
        instances = [RelatedModel(**data) for data in results]
        output = RelatedModel.objects.bulk_create(instances)
        return output


class TimeSeriesManager(models.Manager.from_queryset(TimeSeriesQuerySet)):
    """
    """
    pass


class TimeSeriesModel(models.Model):
    """
    """

    created = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        abstract = True
        ordering = ('-created', )
        get_latest_by = 'created'


def LatestQ(related_name, **kwargs):
    parsed_kwargs = {
        related_name + "__created": F(related_name + '_last_updated')
    }
    for key, value in kwargs.iteritems():
        parsed_kwargs[related_name + '__' + key] = value
    return Q(**parsed_kwargs)


def q_factory(related_name, q_func=LatestQ):
    """
        Usage:

        LatestRawDataQ = q_factory('rawdata')

        Ad.objects.annotate_last_updated('rawdata').filter(
            LatestRawDataQ(views__gt=1000)
        )

    """
    def wrapper(**kwargs):
        return q_func(related_name, **kwargs)
    return wrapper
