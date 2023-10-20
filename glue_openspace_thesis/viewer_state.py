from __future__ import absolute_import, division, print_function
from typing import Literal, Union

from astropy import units as u

from glue.core.data_combo_helper import ComponentIDComboHelper
from echo import (ListCallbackProperty, SelectionCallbackProperty, delay_callback)
from glue.viewers.common.state import ViewerState
from glue.viewers.matplotlib.state import (DeferredDrawCallbackProperty as DDCProperty,
                                           DeferredDrawSelectionCallbackProperty as DDSCProperty)

COORDINATE_SYSTEMS = ['Cartesian', 'ICRS']
DISTANCE_UNITS = [u.m, u.km, u.AU, u.lyr, u.pc, u.kpc, u.Mpc]
TIME_UNITS = [u.s, u.min, u.h, u.day, u.yr]
VELOCITY_MODES = ['Static', 'Motion']
VELOCITY_NAN_MODES = ['Hide', 'Static']

#Common header names to automatically fill the viewer settings on startup.
PX_CHOICES = ['x', 'px', 'posx', 'pos_x', 'positionx', 'position_x']
PY_CHOICES = ['y', 'py', 'posy', 'pos_y', 'positiony', 'position_y']
PZ_CHOICES = ['z', 'pz', 'posz', 'pos_z', 'positionz', 'position_z']
U_CHOICES = ['u', 'vx', 'velx', 'vel_x', 'velocityx', 'velocity_x']
V_CHOICES = ['v', 'vy', 'vely', 'vel_y', 'velocityy', 'velocity_y']
W_CHOICES = ['w', 'vz', 'velz', 'vel_z', 'velocityz', 'velocity_z']
RA_CHOCIES = ['ra', ]
DEC_CHOICES = ['dec', ]
DIST_CHOICES = ['dist', 'distance', 'distpc']

__all__ = ['OpenSpaceViewerState']

class OpenSpaceViewerState(ViewerState):
    
    # Coordinate system
    coordinate_system: Union[Literal['Cartesian'], Literal['ICRS']] = SelectionCallbackProperty(default_index=0)

    # Cartesian
    x_att = SelectionCallbackProperty(default_index=0, docstring='The attribute to use for x')
    y_att = SelectionCallbackProperty(default_index=1, docstring='The attribute to use for y')
    z_att = SelectionCallbackProperty(default_index=2, docstring='The attribute to use for z')
    cartesian_unit_att = SelectionCallbackProperty(default_index=4, docstring='The unit for cartesian coordinates')

    # ICRS
    ra_att = SelectionCallbackProperty(docstring='The attribute to use for RA')
    dec_att = SelectionCallbackProperty(docstring='The attribute to use for Dec')
    icrs_dist_att = SelectionCallbackProperty(docstring='The attribute to use for ICRS distance')
    icrs_dist_unit_att = SelectionCallbackProperty(default_index=4, docstring='The distance unit for ICRS coordinates')

    # Velocity
    velocity_mode = SelectionCallbackProperty(default_index=0, docstring='The mode for velocity')
    # TODO: Add this to set up more coordinate systems for velocity
    # velocity_system = SelectionCallbackProperty(default_index=0)
    u_att = SelectionCallbackProperty(default_index=0, docstring='The attribute to use for u')
    v_att = SelectionCallbackProperty(default_index=1, docstring='The attribute to use for v')
    w_att = SelectionCallbackProperty(default_index=2, docstring='The attribute to use for w')
    vel_distance_unit_att = SelectionCallbackProperty(default_index=1, docstring='The velocity distance unit of the current dataset')
    vel_time_unit_att = SelectionCallbackProperty(default_index=0, docstring='The velocity time unit of the current dataset')
    vel_day_rec = DDCProperty(1, docstring='The day of the date when the velocity was recorded') # CallbackProperty()
    vel_month_rec = DDCProperty(1, docstring='The month of the date when the velocity was recorded') # CallbackProperty()
    vel_year_rec = DDCProperty(2000, docstring='The year of the date when the velocity was recorded') # CallbackProperty()
    # vel_norm = CallbackProperty(docstring='Whether velocity is normalized') #, docstring='Whether or not velocity is normalized'
    # speed_att = SelectionCallbackProperty(default_index=3, docstring='The attribute to use for speed')
    vel_nan_mode: "Union[Literal['Hide'], Literal['Static']]" = DDSCProperty(docstring="Which velocity NaN value mode to use", default_index=0)

    # lum_att = SelectionCallbackProperty(docstring='The attribute to use for luminosity')

    layers = ListCallbackProperty()

    def __init__(self, **kwargs):
        super(OpenSpaceViewerState, self).__init__()

        OpenSpaceViewerState.coordinate_system.set_choices(self, COORDINATE_SYSTEMS)
        OpenSpaceViewerState.cartesian_unit_att.set_choices(self, [str(x) for x in DISTANCE_UNITS])
        OpenSpaceViewerState.icrs_dist_unit_att.set_choices(self, [str(x) for x in DISTANCE_UNITS])

        OpenSpaceViewerState.velocity_mode.set_choices(self, VELOCITY_MODES)
        OpenSpaceViewerState.vel_distance_unit_att.set_choices(self, [str(x) for x in DISTANCE_UNITS])
        OpenSpaceViewerState.vel_time_unit_att.set_choices(self, [str(x) for x in TIME_UNITS])
        OpenSpaceViewerState.vel_nan_mode.set_choices(self, VELOCITY_NAN_MODES)

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
        # self.speed_att_helper = ComponentIDComboHelper(self, 'speed_att',
        #                                              numeric=True,
        #                                              categorical=False,
        #                                              world_coord=True,
        #                                              pixel_coord=False)

        self.ra_att_helper = ComponentIDComboHelper(self, 'ra_att',
                                                     numeric=True,
                                                     categorical=False,
                                                     world_coord=True,
                                                     pixel_coord=False)
        self.dec_att_helper = ComponentIDComboHelper(self, 'dec_att',
                                                     numeric=True,
                                                     categorical=False,
                                                     world_coord=True,
                                                     pixel_coord=False)
        self.icrs_dist_att_helper = ComponentIDComboHelper(self, 'icrs_dist_att',
                                                     numeric=True,
                                                     categorical=False,
                                                     world_coord=True,
                                                     pixel_coord=False)

        # self.lum_att_helper = ComponentIDComboHelper(self, 'lum_att',
        #                                              numeric=True,
        #                                              categorical=False,
        #                                              world_coord=True,
        #                                              pixel_coord=False)

        self.add_callback('layers', self._on_layers_changed)
        self.add_callback('layers', self.initializeVariables)
        self._on_layers_changed()

        self.update_from_dict(kwargs)

    def _on_layers_changed(self, *args):
        print("Executing on layers changed from viewer state")
        with delay_callback(self, 'x_att', 'y_att', 'z_att',
                            'ra_att', 'dec_att', 'icrs_dist_att',
                            'u_att', 'v_att', 'w_att'):
            self.x_att_helper.set_multiple_data(self.layers_data)
            self.y_att_helper.set_multiple_data(self.layers_data)
            self.z_att_helper.set_multiple_data(self.layers_data)

            self.ra_att_helper.set_multiple_data(self.layers_data)
            self.dec_att_helper.set_multiple_data(self.layers_data)
            self.icrs_dist_att_helper.set_multiple_data(self.layers_data)
            
            self.u_att_helper.set_multiple_data(self.layers_data)
            self.v_att_helper.set_multiple_data(self.layers_data)
            self.w_att_helper.set_multiple_data(self.layers_data)

        # self.speed_att_helper.set_multiple_data(self.layers_data)
        # self.lum_att_helper.set_multiple_data(self.layers_data)

    def initializeVariables(self, *args):
        if(not self.layers):
            return

        #Create dictionary to map helpers and corresponding header choices by a common key.
        #Since helpers cannot be iterated over, we have to do this manually.
        headerDict = {'px': PX_CHOICES, 'py': PY_CHOICES, 'pz': PZ_CHOICES,
                      'u': U_CHOICES, 'v': V_CHOICES, 'w': W_CHOICES,
                      'ra': RA_CHOCIES, 'dec': DEC_CHOICES, 'dist': DIST_CHOICES}
        helperDict = {'px': self.x_att_helper, 'py': self.y_att_helper, 'pz': self.z_att_helper,
                      'u': self.u_att_helper, 'v': self.v_att_helper, 'w': self.w_att_helper,
                      'ra': self.ra_att_helper, 'dec': self.dec_att_helper, 'dist': self.icrs_dist_att_helper}

        #Try to automatically set settings based on available header names in layer data,
        #Otherwise it will use default set in __init__
        for key, helper in helperDict.items():
            headers = headerDict[key]
            choices = helper.choices #Available choices for this helper based on layer data.
            
            #Convert to strings to iterate over
            choicesAsStrings = [str(x) for x in choices]
            
            for header in headers:
                try:
                    index = choicesAsStrings.index(header)
                    helper.selection = helper.choices[index]
                    break
                except ValueError: # header not in choices
                    continue
        
        #We remove the callback so this only happens once per startup. 
        self.remove_callback('layers', self.initializeVariables)

    def _update_priority(self, name):
        if name == 'layers':
            return 2
        else:
            return 0
