from __future__ import absolute_import, division, print_function
import uuid

from astropy import units as u

from glue.core.data_combo_helper import ComponentIDComboHelper
from echo import (ListCallbackProperty, SelectionCallbackProperty)
from glue.viewers.common.state import ViewerState

ALTERNATIVE_UNITS = [u.m, u.km, u.AU, u.lyr, u.pc, u.kpc, u.Mpc]

ALTERNATIVE_TYPES = ['Distance']

COORDINATE_SYSTEMS = ['Cartesian', 'ICRS', 'FK5', 'FK4', 'Galactic']

__all__ = ['OpenSpaceViewerState']

class OpenSpaceViewerState(ViewerState):
    coordinate_system = SelectionCallbackProperty(default_index=0)

    x_att = SelectionCallbackProperty(docstring='The attribute to use for x')
    y_att = SelectionCallbackProperty(docstring='The attribute to use for y')
    z_att = SelectionCallbackProperty(docstring='The attribute to use for z')
    cartesian_unit_att = SelectionCallbackProperty(default_index=4, docstring='The unit of the current dataset')

    lon_att = SelectionCallbackProperty(docstring='The attribute to use for ra/longitude')
    lat_att = SelectionCallbackProperty(docstring='The attribute to use for dec/latitude')
    lum_att = SelectionCallbackProperty(docstring='The attribute to use for luminosity')
    vel_att = SelectionCallbackProperty(docstring='The attribute to use for velocity')
    alt_att = SelectionCallbackProperty()
    alt_unit = SelectionCallbackProperty(default_index=4, docstring='The unit of the current dataset')
    # alt_type = SelectionCallbackProperty(default_index=0)

    layers = ListCallbackProperty()

    def __init__(self, **kwargs):
        super(OpenSpaceViewerState, self).__init__()

        OpenSpaceViewerState.coordinate_system.set_choices(self, COORDINATE_SYSTEMS)
        OpenSpaceViewerState.alt_unit.set_choices(self, [str(x) for x in ALTERNATIVE_UNITS])
        OpenSpaceViewerState.cartesian_unit_att.set_choices(self, [str(x) for x in ALTERNATIVE_UNITS])
        # OpenSpaceViewerState.alt_type.set_choices(self, ALTERNATIVE_TYPES)

        self.x_att_helper = ComponentIDComboHelper(self, 'x_att',
                                                     numeric=True,
                                                     categorical=False,
                                                     world_coord=True,
                                                     pixel_coord=False)
        self.y_att_helper = ComponentIDComboHelper(self, 'y_att',
                                                     numeric=True,
                                                     categorical=False,
                                                     world_coord=True,
                                                     pixel_coord=False)
        self.z_att_helper = ComponentIDComboHelper(self, 'z_att',
                                                     numeric=True,
                                                     categorical=False,
                                                     world_coord=True,
                                                     pixel_coord=False)

        self.lon_att_helper = ComponentIDComboHelper(self, 'lon_att',
                                                     numeric=True,
                                                     categorical=False,
                                                     world_coord=True,
                                                     pixel_coord=False)

        self.lat_att_helper = ComponentIDComboHelper(self, 'lat_att',
                                                     numeric=True,
                                                     categorical=False,
                                                     world_coord=True,
                                                     pixel_coord=False)

        self.lum_att_helper = ComponentIDComboHelper(self, 'lum_att',
                                                     numeric=True,
                                                     categorical=False,
                                                     world_coord=True,
                                                     pixel_coord=False)

        self.vel_att_helper = ComponentIDComboHelper(self, 'vel_att',
                                                     numeric=True,
                                                     categorical=False,
                                                     world_coord=True,
                                                     pixel_coord=False)

        self.alt_att_helper = ComponentIDComboHelper(self, 'alt_att',
                                                     numeric=True,
                                                     categorical=False,
                                                     world_coord=True,
                                                     pixel_coord=False)

        self.add_callback('layers', self._on_layers_changed)
        self._on_layers_changed()

        self.update_from_dict(kwargs)

    def _on_layers_changed(self, *args):
        self.x_att_helper.set_multiple_data(self.layers_data)
        self.y_att_helper.set_multiple_data(self.layers_data)
        self.z_att_helper.set_multiple_data(self.layers_data)

        self.lon_att_helper.set_multiple_data(self.layers_data)
        self.lat_att_helper.set_multiple_data(self.layers_data)
        self.lum_att_helper.set_multiple_data(self.layers_data)
        self.vel_att_helper.set_multiple_data(self.layers_data)
        self.alt_att_helper.set_multiple_data(self.layers_data)

    def _update_priority(self, name):
        if name == 'layers':
            return 2
        else:
            return 0
