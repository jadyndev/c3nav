import json
import time
from functools import wraps
from typing import Optional

from django.conf import settings
from django.core.cache import cache
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Prefetch
from django.utils.cache import get_conditional_response
from django.utils.http import quote_etag
from django.utils.translation import get_language
from ninja.decorators import decorate_view

from c3nav.mapdata.models import AccessRestriction, Building, Door, LocationGroup, MapUpdate, Space
from c3nav.mapdata.models.access import AccessPermission
from c3nav.mapdata.models.geometry.base import GeometryMixin
from c3nav.mapdata.models.locations import SpecificLocation
from c3nav.mapdata.utils.cache.local import LocalCacheProxy
from c3nav.mapdata.utils.cache.stats import increment_cache_key

request_cache = LocalCacheProxy(maxsize=settings.CACHE_SIZE_API)


def api_etag(permissions=True, quests=False, etag_func=AccessPermission.etag_func, base_mapdata=False,
             etag_add_key: Optional[tuple[str, str]] = None):

    def outer_wrapper(func):
        @wraps(func)
        def outer_wrapped_func(request, *args, **kwargs):
            response = func(request, *args, **kwargs)
            if response.status_code == 200:
                if request._target_etag:
                    response['ETag'] = request._target_etag
                response['Cache-Control'] = 'no-cache'
                if request._target_cache_key:
                    request_cache.set(request._target_cache_key, response, 900)
            return response
        return outer_wrapped_func

    def inner_wrapper(func):
        @wraps(func)
        def inner_wrapped_func(request, *args, **kwargs):
            # calculate the ETag
            response_format = "json"
            raw_etag = '%s:%s:%s' % (response_format, get_language(),
                                     (etag_func(request) if permissions else MapUpdate.current_cache_key()))
            if quests:
                raw_etag += 'all' if request.user.is_superuser else f':{','.join(request.user_permissions.quests)}'
            if base_mapdata:
                raw_etag += ':%d' % request.user_permissions.can_access_base_mapdata

            if etag_add_key:
                etag_add_cache_key = (
                    f'mapdata:etag_add:{etag_add_key[1]}:{getattr(kwargs[etag_add_key[0]], etag_add_key[1])}'
                )
                etag_add = cache.get(etag_add_cache_key, None)
                if etag_add is None:
                    etag_add = int(time.time())
                    cache.set(etag_add_cache_key, etag_add, 300)
                raw_etag += ':%d' % etag_add


            etag = quote_etag(raw_etag)

            response = get_conditional_response(request, etag)
            if response:
                return response

            request._target_etag = etag

            # calculate the cache key
            data = {}
            for name, value in kwargs.items():
                try:
                    model_dump = value.model_dump
                except AttributeError:
                    pass
                else:
                    value = model_dump()
                data[name] = value

            cache_key = 'mapdata:api:%s:%s:%s' % (
                request.resolver_match.route.replace('/', '-').strip('-'),
                raw_etag,
                json.dumps(data, separators=(',', ':'), sort_keys=True, cls=DjangoJSONEncoder),
            )

            request._target_cache_key = cache_key

            response = request_cache.get(cache_key)
            if response is not None:
                return response

            with GeometryMixin.dont_keep_originals():
                return func(request, *args, **kwargs)

        return decorate_view(outer_wrapper)(inner_wrapped_func)
    return inner_wrapper


def api_stats(stat_name):
    if settings.METRICS:
        from c3nav.mapdata.metrics import APIStatsCollector
        APIStatsCollector.add_stat(stat_name, ['by', 'query'])
    def wrapper(func):
        @wraps(func)
        def wrapped_func(request, *args, **kwargs):
            response = func(request, *args, **kwargs)
            if response.status_code < 400 and kwargs:
                name, value = next(iter(kwargs.items()))
                for value in api_stats_clean_location_value(value):
                    increment_cache_key('apistats__%s__%s__%s' % (stat_name, name, value))
            return response
        return wrapped_func
    return decorate_view(wrapper)


def optimize_query(qs):
    if issubclass(qs.model, SpecificLocation):
        base_qs = LocationGroup.objects.select_related('category')
        qs = qs.prefetch_related(Prefetch('groups', queryset=base_qs))
    if issubclass(qs.model, AccessRestriction):
        qs = qs.prefetch_related('groups')
    return qs


def api_stats_clean_location_value(value):
    if isinstance(value, str) and value.startswith('c:'):
        value = value.split(':')
        value = 'c:%s:%d:%d' % (value[1], int(float(value[2]) / 3) * 3, int(float(value[3]) / 3) * 3)
        return (value, 'c:anywhere')
    return (value, )


def can_access_geometry(request, obj):
    if isinstance(obj, Space):
        return obj.base_mapdata_accessible or request.user_permissions.can_access_base_mapdata
    elif isinstance(obj, (Building, Door)):
        return request.user_permissions.can_access_base_mapdata
    return True
