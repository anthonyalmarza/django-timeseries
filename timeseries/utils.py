from datetime import datetime, timedelta
from django.db import models
from django.db.models.fields.related import ManyToOneRel
from django.db.models.options import FieldDoesNotExist

try:

    from django.utils.timezone import utcnow

except ImportError:

    from django.utils.timezone import utc

    def utcnow():
        return datetime.utcnow().replace(tzinfo=utc)


def get_reverse_relation(model, related_name):
    return model._meta.fields_map.get(related_name)


def check_reverse_relation(model, related_name):
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


def check_related_model(obj):
    created = obj._meta.get_field_by_name('created')
    assert isinstance(created, models.DateTimeField)


def get_interval(obj):
    interval = obj.TIMESERIES_INTERVAL
    if isinstance(interval, timedelta):
        return interval
    elif isinstance(interval, (int, float, basestring)):
        return timedelta(seconds=int(interval))
    raise ValueError(
        'TIMESERIES_INTERVAL must either be in seconds or an instance of '
        'datetime.timedelta'
    )
