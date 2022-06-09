from __future__ import absolute_import, division, print_function

from astropy import units as u

from glue.core.data_combo_helper import ComponentIDComboHelper
from echo import (ListCallbackProperty, SelectionCallbackProperty, CallbackProperty)
from glue.viewers.common.state import ViewerState

ALTERNATIVE_UNITS = [u.m, u.km, u.AU, u.lyr, u.pc, u.kpc, u.Mpc]

ALTERNATIVE_TYPES = ['Distance']

COORDINATE_SYSTEMS = ['Cartesian', 'ICRS', 'FK5', 'FK4', 'Galactic']

VELOCITY_MODES = ['Static', 'Motion']

__all__ = ['OpenSpaceViewerState']

class OpenSpaceViewerState(ViewerState):
    
    # Coordinate system
    coordinate_system = SelectionCallbackProperty(default_index=0)

    x_att = SelectionCallbackProperty(docstring='The attribute to use for x')
    y_att = SelectionCallbackProperty(docstring='The attribute to use for y')
    z_att = SelectionCallbackProperty(docstring='The attribute to use for z')
    cartesian_unit_att = SelectionCallbackProperty(default_index=4, docstring='The unit of the current dataset')

    # Velocity
    # velocity_system = SelectionCallbackProperty(default_index=0)
    velocity_mode = SelectionCallbackProperty(default_index=0)
    # color_mode: Union[Literal['Fixed'], Literal['Linear']] = DDSCProperty(docstring="Which color mode to use", default_index=0)
    # send_velocity = CallbackProperty(docstring='Whether to send velocity to OpenSpace') #, docstring='Whether or not velocity is normalized'
    u_att = SelectionCallbackProperty(default_index=0, docstring='The attribute to use for u')
    v_att = SelectionCallbackProperty(default_index=1, docstring='The attribute to use for v')
    w_att = SelectionCallbackProperty(default_index=2, docstring='The attribute to use for w')
    vel_unit_att = SelectionCallbackProperty(default_index=4, docstring='The velocity unit of the current dataset')
    vel_norm = CallbackProperty(docstring='Whether velocity is normalized') #, docstring='Whether or not velocity is normalized'
    speed_att = SelectionCallbackProperty(default_index=3, docstring='The attribute to use for speed')

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
        OpenSpaceViewerState.velocity_mode.set_choices(self, VELOCITY_MODES)
        OpenSpaceViewerState.alt_unit.set_choices(self, [str(x) for x in ALTERNATIVE_UNITS])
        OpenSpaceViewerState.cartesian_unit_att.set_choices(self, [str(x) for x in ALTERNATIVE_UNITS])
        OpenSpaceViewerState.vel_unit_att.set_choices(self, [str(x) for x in ALTERNATIVE_UNITS])
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

        self.u_att_helper = ComponentIDComboHelper(self, 'u_att',
                                                     numeric=True,
                                                     categorical=False,
                                                     world_coord=True,
                                                     pixel_coord=False)
        self.v_att_helper = ComponentIDComboHelper(self, 'v_att',
                                                     numeric=True,
                                                     categorical=False,
                                                     world_coord=True,
                                                     pixel_coord=False)
        self.w_att_helper = ComponentIDComboHelper(self, 'w_att',
                                                     numeric=True,
                                                     categorical=False,
                                                     world_coord=True,
                                                     pixel_coord=False)
        self.speed_att_helper = ComponentIDComboHelper(self, 'speed_att',
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
        
        self.u_att_helper.set_multiple_data(self.layers_data)
        self.v_att_helper.set_multiple_data(self.layers_data)
        self.w_att_helper.set_multiple_data(self.layers_data)
        self.speed_att_helper.set_multiple_data(self.layers_data)

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
