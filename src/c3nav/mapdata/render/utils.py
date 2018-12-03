from itertools import chain

from c3nav.mapdata.render.renderdata import LevelRenderData


def get_min_altitude(levels, default):
    min_altitude = min(chain(*(tuple(area.altitude for area in geoms.altitudeareas)
                               for geoms in levels)),
                       default=None)
    if min_altitude is None:
        min_altitude = min(tuple(geoms.base_altitude for geoms in levels),
                           default=default)
    return min_altitude


def get_full_levels(level_render_data):
    levels = tuple(chain(*(
        tuple(sublevel for sublevel in LevelRenderData.get(level.pk).levels
              if sublevel.pk == level.pk or sublevel.on_top_of_id == level.pk)
        for level in level_render_data.levels if level.on_top_of_id is None
    )))
    return levels
