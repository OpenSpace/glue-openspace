from typing import TYPE_CHECKING, Union
from matplotlib.colors import to_hex, to_rgb
from astropy.coordinates import SkyCoord
from astropy import units as ap_u

from glue.core import Data, Subset
from glue.viewers.common.layer_artist import LayerArtist
import numpy as np

from .layer_state import OpenSpaceLayerState
from .viewer_state import OpenSpaceViewerState
from .simp import simp
from .utils import (bool_to_bytes, float32_list_to_bytes, float32_to_bytes,
                    int32_to_bytes, string_to_bytes,
                    get_normalized_list_of_equal_strides) 

__all__ = ['OpenSpaceLayerArtist']

class OpenSpaceLayerArtist(LayerArtist):
    _layer_state_cls = OpenSpaceLayerState

    state: "OpenSpaceLayerState"
    _viewer_state: "OpenSpaceViewerState"

    if TYPE_CHECKING:
        from .viewer import OpenSpaceDataViewer
        _viewer: "OpenSpaceDataViewer"

    _display_name: "str"

    _removed_indices: "np.ndarray"

    _has_updated_points: "bool"

    def __init__(self, viewer, *args, **kwargs):
        super(OpenSpaceLayerArtist, self).__init__(*args, **kwargs)

        self._viewer = viewer

        self.state.add_global_callback(self.update)
        self._viewer_state.add_global_callback(self.update)

        self._display_name = None
        self._state = None

        self._has_updated_points = False

    def add_to_outgoing_data_message(self, data_key: "simp.DataKey", entry: "tuple[bytearray, int]"):
        '''
            DANGER! You need to lock outgoing message
            mutex before calling this function
        '''
        self._viewer.debug(f'Executing add_to_outgoing_data_message()', 4)
        identifier = self.get_identifier_str()
        if not identifier:
            return

        if not identifier in self._viewer._outgoing_data_message:
            self._viewer._outgoing_data_message[identifier] = {}

        self._viewer._outgoing_data_message[identifier][data_key] = entry

    def update(self, **kwargs):
        self._viewer.debug(f'Executing update()', 4)
        # Check if connected
        if self._viewer._connection_state != self._viewer.ConnectionState.Connected:
            return
        # if isinstance(self.state.layer, Data) or isinstance(self.state.layer, Subset):
        #     self._viewer.check_and_add_instance(self.state.layer)
        self._viewer.debug(f'\tConnected, we can update', 4)

        force = kwargs.get('force', False)
        try:
            if self.get_identifier_str() is None:
                gui_name = self.get_gui_name_str()
                if gui_name is None:
                    raise simp.SimpError('Cannot set GUI name')

        except simp.SimpError as exc:
            self._viewer.log(f'Exception in update: {exc.message}')
            return

        except Exception as exc:
            self._viewer.log(f'Exception in update: {exc}')
            return

        if self._viewer._socket is None:
            return

        if self.state.has_sent_initial_data:
            self._on_attribute_change(force)
        else:
            self.add_initial_data_to_message()

    def _on_attribute_change(self, force):
        self._viewer.debug(f'Executing _on_attribute_change()', 4)
        changed = self.pop_changed_properties()

        if len(changed) == 0 and not force:
            return

        self._clean_properties(changed)

        if self._viewer._socket is None:
            return

        if self._viewer_state.coordinate_system == 'Cartesian'\
        and (self._viewer_state.x_att is None or self._viewer_state.y_att is None\
        or self._viewer_state.z_att is None):
            return

        if self._viewer_state.coordinate_system == 'ICRS'\
        and (self._viewer_state.ra_att is None or self._viewer_state.dec_att is None\
        or self._viewer_state.icrs_dist_att is None):
            return
        
        # If properties update in Glue, send message to OpenSpace with new values
        if self.state.will_send_message is False:
            return

        self._viewer._outgoing_data_message_mutex.acquire()
        self._viewer._outgoing_data_message_condition.acquire()

        if 'alpha' in changed:
            self.add_to_outgoing_data_message(simp.DataKey.Alpha, self.get_opacity())

        if 'visible' in changed:
            self.add_to_outgoing_data_message(
                simp.DataKey.Visibility,
                self.is_enabled(simp.DataKey.Visibility)
            )

        self.add_color_to_outgoing_data_message(changed=changed)

        self.add_size_to_outgoing_data_message(changed=changed)

        self.add_points_to_outgoing_data_message(changed=changed)

        self.add_velocity_to_outgoing_data_message(changed=changed)

        self._viewer._outgoing_data_message_condition.notify()

        self._viewer._outgoing_data_message_mutex.release()
        self._viewer._outgoing_data_message_condition.release()

        self.redraw()

    def _clean_properties(self, changed):
        if 'alpha' in changed:
            if self.state.alpha > 1.0:
                self.state.alpha = 1.0
            elif self.state.alpha < 0.0:
                self.state.alpha = 0.0

        elif 'size' in changed:
            if self.state.size > 500.0:
                self.state.size = 500.0
            elif self.state.size < 0.0:
                self.state.size = 0.0

    def receive_message(self, message_type: "simp.MessageType", subject: "bytearray", offset: "int"):
        self.state.will_send_message = False

        if message_type == simp.MessageType.Data:
            self.receive_data_message(subject, offset)

        self.redraw()
        self.state.will_send_message = True

    def receive_data_message(self, subject: "bytearray", offset: "int"):
        color = to_rgb(self.state.color)
        new_color = list(color)
        
        while offset != len(subject):
            simp.check_offset(subject, offset)
            data_key, offset = simp.read_string(subject, offset)
            
            # Update Color
            if data_key == simp.DataKey.Red:
                new_color[0], offset = simp.read_float32(subject, offset)
            elif data_key == simp.DataKey.Green:
                new_color[1], offset = simp.read_float32(subject, offset)
            elif data_key == simp.DataKey.Blue:
                new_color[2], offset = simp.read_float32(subject, offset)
            elif data_key == simp.DataKey.Alpha:    
                self.state.alpha, offset = simp.read_float32(subject, offset)
            
            # Update Colormap Enabled
            elif data_key == simp.DataKey.ColormapEnabled:
                colormap_enabled, offset = simp.read_bool(subject, offset)
                self.state.color_mode = 'Linear' if colormap_enabled else 'Fixed'

            # # Update Colormap NaN Mode
            # elif data_key == simp.DataKey.ColormapNanMode:
            #     # TODO: change to int instead of string
            #     self.state.cmap_nan_mode, offset = simp.read_string(subject, offset)

            # Update Size
            elif data_key == simp.DataKey.FixedSize:
                self.state.size, offset = simp.read_float32(subject, offset)
            
            # Update Linear Size Enabled
            elif data_key == simp.DataKey.LinearSizeEnabled:
                linear_size_enabled, offset = simp.read_bool(subject, offset)
                self.state.size_mode = 'Linear' if linear_size_enabled else 'Fixed'

            # Update Velocity Enabled
            elif data_key == simp.DataKey.VelocityEnabled:                
                velocity_enabled, offset = simp.read_bool(subject, offset)
                self._viewer_state.velocity_mode = 'Motion' if velocity_enabled else 'Static'
            
            # # Update Velocity NaN Mode
            # elif data_key == simp.DataKey.VelocityNanMode:
            #     # TODO: change to int instead of string
            #     self._viewer_state.vel_nan_mode, offset = simp.read_string(subject, offset)
            
            # Toggle Visibility
            elif data_key == simp.DataKey.Visibility:
                self.state.visible, offset = simp.read_bool(subject, offset)
 
            else:
                raise simp.SimpError(
                    f'SIMP or the Glue-OpenSpace plugin doesn\'t '\
                    + f'support the attribute \'{data_key}\'.'
                )

        self._viewer.log(f'new_color={new_color}')
        new_color = tuple(new_color)
        if new_color[0] != color[0] or new_color[1] != color[1] or new_color[2] != color[2]:
            self.state.color = to_hex(new_color, keep_alpha=False)

    def add_points_to_outgoing_data_message(self, *, changed: "set" = {}, force: "bool" = False):
        '''
            Adds all point data to outgoing message if force is true.
            Else, check which properties has changed and add 
            relevant data to outgoing message.
        '''
        self._viewer.debug(f'Executing add_points_to_outgoing_data_message()', 4)
        coord_sys_changed = 'coordinate_system' in changed

        # ICRS, Convert ICRS -> Cartesian
        icrs_changed = 'ra_att' in changed or 'dec_att' in changed or 'icrs_dist_att' in changed
        if (force or coord_sys_changed or icrs_changed) and self._viewer_state.coordinate_system == 'ICRS':
            ra = self.state.layer[self._viewer_state.ra_att]
            dec = self.state.layer[self._viewer_state.dec_att]
            distance = self.state.layer[self._viewer_state.icrs_dist_att]
            dist_unit = self._viewer_state.icrs_dist_unit_att

            # Get cartesian coordinates on unit galactic sphere
            coordinates = SkyCoord(
                ra * ap_u.deg,
                dec * ap_u.deg,
                distance=distance * ap_u.Unit(dist_unit),
                frame='icrs'
            )
            x, y, z = coordinates.galactic.cartesian.xyz
            # self._viewer.debug(f'x[0]={x[0]}, y[0]={y[0]}, z[0]={z[0]}')
            # self._viewer.debug(f'len(x)={len(x)}, len(y)={len(y)}, len(z)={len(z)}')
            self._viewer.debug(f'Converted ICRS -> Cartesian', 2)

            self.add_to_outgoing_data_message(
                simp.DataKey.X,
                self.get_float_attribute(x.value)
            )
            self.add_to_outgoing_data_message(
                simp.DataKey.Y,
                self.get_float_attribute(y.value)
            )
            self.add_to_outgoing_data_message(
                simp.DataKey.Z,
                self.get_float_attribute(z.value)
            )

        # Cartesian
        elif self._viewer_state.coordinate_system == 'Cartesian':
            if force or coord_sys_changed or 'x_att' in changed:
                self.add_to_outgoing_data_message(
                    simp.DataKey.X,
                    self.get_float_attribute(self.state.layer[self._viewer_state.x_att])
                )
            if force or coord_sys_changed or 'y_att' in changed:
                self.add_to_outgoing_data_message(
                    simp.DataKey.Y,
                    self.get_float_attribute(self.state.layer[self._viewer_state.y_att])
                )
            if force or coord_sys_changed or 'z_att' in changed:
                self.add_to_outgoing_data_message(
                    simp.DataKey.Z,
                    self.get_float_attribute(self.state.layer[self._viewer_state.z_att])
                )

        # Distance unit
        if force or 'cartesian_unit_att' in changed\
                 or 'icrs_dist_unit_att' in changed or coord_sys_changed:
            self.add_to_outgoing_data_message(simp.DataKey.PointUnit, (self.get_position_unit(), 1))

    def add_velocity_to_outgoing_data_message(self, *, changed: "set" = {}, force: "bool" = False):
        '''
            Adds all velocity data to outgoing message if force is true.
            Else, check which properties has changed and add 
            relevant data to outgoing message.
        '''
        self._viewer.debug(f'Executing add_velocity_to_outgoing_data_message()', 4)

        if self._viewer_state.velocity_mode != 'Motion':
            return

        # If in motion mode, check which velocity data to send
        velocity_mode_changed = 'velocity_mode' in changed
        
        # TODO: if force, get all velocity data (faster?)

        if force or 'u_att' in changed or velocity_mode_changed:
            self.add_to_outgoing_data_message(
                simp.DataKey.U,
                self.get_float_attribute(self.state.layer[self._viewer_state.u_att])
            )
        if force or 'v_att' in changed or velocity_mode_changed:
            self.add_to_outgoing_data_message(
                simp.DataKey.V,
                self.get_float_attribute(self.state.layer[self._viewer_state.v_att])
            )
        if force or 'w_att' in changed or velocity_mode_changed:
            self.add_to_outgoing_data_message(
                simp.DataKey.W,
                self.get_float_attribute(self.state.layer[self._viewer_state.w_att])
            )
        if force or 'vel_distance_unit_att' in changed or velocity_mode_changed:
            self.add_to_outgoing_data_message(simp.DataKey.VelocityDistanceUnit, self.get_velocity_distance_unit())
        if force or 'vel_time_unit_att' in changed or velocity_mode_changed:
            self.add_to_outgoing_data_message(simp.DataKey.VelocityTimeUnit, self.get_velocity_time_unit())
        if force or 'vel_day_rec' in changed or velocity_mode_changed:
            self.add_to_outgoing_data_message(simp.DataKey.VelocityDayRecorded, self.get_velocity_day_rec())
        if force or 'vel_month_rec' in changed or velocity_mode_changed:
            self.add_to_outgoing_data_message(simp.DataKey.VelocityMonthRecorded, self.get_velocity_month_rec())
        if force or 'vel_year_rec' in changed or velocity_mode_changed:
            self.add_to_outgoing_data_message(simp.DataKey.VelocityYearRecorded, self.get_velocity_year_rec())
        if force or 'vel_nan_mode' in changed or velocity_mode_changed:
            self.add_to_outgoing_data_message(simp.DataKey.VelocityNanMode, self.get_velocity_nan_mode())
        # if 'vel_norm' in changed:
        # if 'speed_att' in changed:
        if force or velocity_mode_changed:
            self.add_to_outgoing_data_message(
                simp.DataKey.VelocityEnabled,
                self.is_enabled(simp.DataKey.VelocityEnabled)
            )

        return

    def add_color_to_outgoing_data_message(self, *, changed: "set" = {}, force: "bool" = False):
        '''
            Adds all color data to outgoing message if force is true.
            Else, check which properties has changed and add 
            relevant data to outgoing message.
        '''
        self._viewer.debug(f'Executing add_color_to_outgoing_data_message()', 4)
        color_mode_changed = 'color_mode' in changed

        if force or 'color' in changed or (color_mode_changed and self.state.color_mode == 'Fixed'):
            (r, g, b, _) = self.get_color()
            self.add_to_outgoing_data_message(simp.DataKey.Red, (r, 1))
            self.add_to_outgoing_data_message(simp.DataKey.Green, (g, 1))
            self.add_to_outgoing_data_message(simp.DataKey.Blue, (b, 1))
        
        if self.state.color_mode == 'Linear':
            if force or 'cmap_nan_mode' in changed or color_mode_changed:
                self.add_to_outgoing_data_message(
                    simp.DataKey.ColormapNanMode,
                    self.get_cmap_nan_mode()
                )
            
            if (
                (force or ('cmap_nan_color' in changed) or color_mode_changed or 'cmap_nan_mode' in changed)
                and self.state.cmap_nan_mode == 'FixedColor'
            ):
                (r, g, b, _) = self.get_cmap_nan_color()
                self.add_to_outgoing_data_message(simp.DataKey.ColormapNanR, (r, 1))
                self.add_to_outgoing_data_message(simp.DataKey.ColormapNanG, (g, 1))
                self.add_to_outgoing_data_message(simp.DataKey.ColormapNanB, (b, 1))

            min, max = self.get_colormap_limits()
            if force or 'cmap_vmin' in changed or color_mode_changed:
                self.add_to_outgoing_data_message(simp.DataKey.ColormapMin, (min, 1))
            if force or 'cmap_vmax' in changed or color_mode_changed:
                self.add_to_outgoing_data_message(simp.DataKey.ColormapMax, (max, 1))

            if force or 'cmap' in changed or color_mode_changed:
                (r, g, b, a, n_colors) = self.get_colormap()
                self.add_to_outgoing_data_message(simp.DataKey.ColormapRed, (r, n_colors))
                self.add_to_outgoing_data_message(simp.DataKey.ColormapGreen, (g, n_colors))
                self.add_to_outgoing_data_message(simp.DataKey.ColormapBlue, (b, n_colors))
                self.add_to_outgoing_data_message(simp.DataKey.ColormapAlpha, (a, n_colors))

            if force or 'cmap_att' in changed or color_mode_changed:
                self.add_to_outgoing_data_message(
                    simp.DataKey.ColormapAttributeData,
                    self.get_attrib_data(self.state.cmap_att)
                )
            
        if force or color_mode_changed:
            self.add_to_outgoing_data_message(
                simp.DataKey.ColormapEnabled,
                self.is_enabled(simp.DataKey.ColormapEnabled)
            )
            
        return

    def add_size_to_outgoing_data_message(self, *, changed: "set" = {}, force: "bool" = False):
        '''
            Adds all size data to outgoing message if force is true.
            Else, check which properties has changed and add 
            relevant data to outgoing message.
        '''
        self._viewer.debug(f'Executing add_size_to_outgoing_data_message()', 4)
        size_mode_changed = 'size_mode' in changed
        if force or 'size' in changed or (size_mode_changed and self.state.size_mode == 'Fixed'):
            self.add_to_outgoing_data_message(simp.DataKey.FixedSize, self.get_size())

        if self.state.size_mode == 'Linear':
            min, max = self.get_linear_size_limits()
            if force or 'size_att' in changed or size_mode_changed:
                self.add_to_outgoing_data_message(
                    simp.DataKey.LinearSizeAttributeData,
                    self.get_attrib_data(self.state.size_att)
                )
            if force or 'size_vmin' in changed or size_mode_changed:
                self.add_to_outgoing_data_message(simp.DataKey.LinearSizeMin, min)
            if force or 'size_vmax' in changed or size_mode_changed:
                self.add_to_outgoing_data_message(simp.DataKey.LinearSizeMax, max)
        
        if force or size_mode_changed:
            self.add_to_outgoing_data_message(
                simp.DataKey.LinearSizeEnabled,
                self.is_enabled(simp.DataKey.LinearSizeEnabled)
            )

    def get_subject_prefix(self) -> str:
        identifier = self.get_identifier_str()
        gui_name = self.get_gui_name_str()
        return identifier + simp.DELIM + gui_name + simp.DELIM

    def add_initial_data_to_message(self):
        self._viewer._outgoing_data_message_mutex.acquire()
        self._viewer._outgoing_data_message_condition.acquire()

        self._viewer.debug(f'Executing add_initial_data_to_message()', 4)

        # PointData
        self.add_points_to_outgoing_data_message(force=True)

        # Opacity
        self.add_to_outgoing_data_message(simp.DataKey.Alpha, self.get_opacity())
        
        # Visibility
        self.add_to_outgoing_data_message(
            simp.DataKey.Visibility,
            self.is_enabled(simp.DataKey.Visibility)
        )

        # Color
        self.add_color_to_outgoing_data_message(force=True)

        # Size
        self.add_size_to_outgoing_data_message(force=True)

        # Velocity
        self.add_velocity_to_outgoing_data_message(force=True)
        
        self._viewer._outgoing_data_message_condition.notify()

        self._viewer._outgoing_data_message_mutex.release()
        self._viewer._outgoing_data_message_condition.release()

        self.pop_changed_properties()

        # Clear properties that have been set on init or 
        # duplicate messages will be sent on next prop change 
        self.pop_changed_properties()

    # Create and send "Remove Scene Graph Node" message to OS
    def send_remove_sgn(self):
        subject = string_to_bytes(self.get_identifier_str() + simp.DELIM)
        simp.send_simp_message(self._viewer, simp.MessageType.RemoveSceneGraphNode, subject)

    def clear(self):
        if self._viewer._socket is None:
            return

        self.send_remove_sgn()
        self.redraw()

    def get_identifier_str(self) -> "Union[str, None]":
        # TODO: Dilemma!
        # Problem: This line makes send_inital_data 
        # be called on every prop change
        # Good thing: This make Subset data automatically being 
        # sent to OpenSpace on Subset creation
        # Can we set a 'has_sent_initial_data' to every dataset/subset?
        # self.state.has_sent_initial_data = False

        if isinstance(self.state.layer, Data):
            # TODO: Same dataset can be connected to multiple viewers and
            # can be controlled from each. This is a bit unclear. Two options:
            # 1. A dataset can be used in multiple viewers but are treated as different datasets
            # 2. A dataset can onlu be used in one viewer at a time. Give a prompt that says 
            #    that you can't have multiple viewers for same dataset, if user tries.
            self._viewer._main_layer_uuid = self.state.layer.uuid
            return self.state.layer.uuid
        elif isinstance(self.state.layer, Subset):
            return self._viewer._main_layer_uuid + self.state.layer.label.replace('Subset ', '')
        else:
            return

    def get_color(self, color=None) -> "tuple[bytearray, bytearray, bytearray, bytearray]":
        """
        `color` should be a list or tuple [r, g, b] or [r, g, b, a].
        If `color` isn't specified, self.state.color 
        or green will be used.
        """
        if color == None:
            color = to_rgb(self.state.color if (self.state.color != None) 
                                            else [0.0,1.0,0.0,1.0])
        else:
            if not (isinstance(color, list) or isinstance(color, tuple)):
                self._viewer.log(
                    f'The provided color must be of type list or tuple. It\'s of type {type(color)}'
                )
                return

        if len(color) < 3 or len(color) > 4:
            self._viewer.log(
                f'The provided color is not of proper length. It should be of '\
                + f'length 3 (RGB) or 4 (RGBA). It\'s of length {len(color)}')
            return

        r = float32_to_bytes(color[0])
        g = float32_to_bytes(color[1])
        b = float32_to_bytes(color[2])
        a = float32_to_bytes(color[3] if (len(color) == 4) else 1.0)

        return (r, g, b, a)

    def is_enabled(self, mode: simp.DataKey) -> "tuple[bytearray, int]":
        if mode == simp.DataKey.Visibility:
            return bool_to_bytes(bool(self.state.visible)), 1
        elif mode == simp.DataKey.VelocityEnabled:
            enabled = self._viewer_state.velocity_mode == 'Motion'
            return bool_to_bytes(enabled), 1
        elif mode == simp.DataKey.ColormapEnabled:
            enabled = self.state.color_mode == 'Linear'
            return bool_to_bytes(enabled), 1
        elif mode == simp.DataKey.LinearSizeEnabled:
            enabled = self.state.size_mode == 'Linear'
            return bool_to_bytes(enabled), 1
        else:
            raise simp.SimpError(
                f'The data key \'{mode}\' can\'t be used to set enable/disable'
            )

    def get_opacity(self) -> "tuple[bytearray, int]":
        self._viewer.debug(f'Executing get_opacity()', 4)
        return float32_to_bytes(self.state.alpha), 1

    def get_gui_name_str(self) -> "Union[str, None]":
        if isinstance(self.state.layer, Data):
            self._display_name = self.state.layer.label
        elif isinstance(self.state.layer, Subset):
            self._display_name = self.state.layer.label + ' (' + self.state.layer.data.label + ')'
        else:
            return
        
        gui_name = self._display_name
        clean_gui_name: "str" = ''

        # Escape all potential occurences of the separator character inside the gui name
        for i in range(len(gui_name)):
            if (gui_name[i] == simp.DELIM):
                clean_gui_name += '\\'
            clean_gui_name += gui_name[i]

        return clean_gui_name
        
    def get_size(self) -> "tuple[bytearray, int]":
        return (float32_to_bytes(float(self.state.size)), 1)

    def get_linear_size_limits(self) -> "tuple[tuple[bytearray, int], tuple[bytearray, int]]":
        vmin = (float32_to_bytes(float(self.state.size_vmin)), 1)
        vmax = (float32_to_bytes(float(self.state.size_vmax)), 1)
        return vmin, vmax

    def get_position_unit(self) -> "tuple[bytearray]":
        self._viewer.debug('Executing get_position_unit()')
        if self._viewer_state.coordinate_system == 'Cartesian':
            self._viewer.debug(f'get_position_unit(): Cartesian - {simp.dist_unit_astropy_to_simp(self._viewer_state.cartesian_unit_att)}')
            return (
                string_to_bytes(simp.dist_unit_astropy_to_simp(
                    self._viewer_state.cartesian_unit_att 
                ) + simp.DELIM)
            )
        elif self._viewer_state.coordinate_system == 'ICRS':
            self._viewer.debug(f'get_position_unit(): ICRS - {simp.dist_unit_astropy_to_simp(self._viewer_state.icrs_dist_unit_att)}')
            return (
                string_to_bytes(simp.dist_unit_astropy_to_simp(
                    self._viewer_state.icrs_dist_unit_att
                ) + simp.DELIM)
            )

    def get_cmap_nan_mode(self) -> "tuple[bytearray, int]":
        mode = -1
        if self.state.cmap_nan_mode == 'Hide':
            mode = 0
        elif self.state.cmap_nan_mode == 'FixedColor':
            mode = 1

        return (int32_to_bytes(mode), 1)

    def get_cmap_nan_color(self) -> "tuple[bytearray, bytearray, bytearray, bytearray]":
        return self.get_color(
            to_rgb(
                self.state.cmap_nan_color 
                if (self.state.cmap_nan_color != None) 
                else [0.0,1.0,0.0,1.0]
            )
        )
        
    def get_velocity_nan_mode(self) -> "tuple[bytearray, int]":
        mode = -1
        if self._viewer_state.vel_nan_mode == 'Hide':
            mode = 0
        elif self._viewer_state.vel_nan_mode == 'Static':
            mode = 1

        return (int32_to_bytes(mode), 1)

    def get_velocity_distance_unit(self) -> "tuple[bytearray, int]":
        return (
            string_to_bytes(simp.dist_unit_astropy_to_simp(
                self._viewer_state.vel_distance_unit_att
            ) + simp.DELIM),
            1
        )

    def get_velocity_time_unit(self) -> "tuple[bytearray, int]":
        return (
            string_to_bytes(simp.time_unit_astropy_to_simp(
                self._viewer_state.vel_time_unit_att
            ) + simp.DELIM),
            1
        )

    def get_velocity_day_rec(self) -> "tuple[bytearray, int]":
        return (int32_to_bytes(self._viewer_state.vel_day_rec), 1)

    def get_velocity_month_rec(self) -> "tuple[bytearray, int]":
        return (int32_to_bytes(self._viewer_state.vel_month_rec), 1)

    def get_velocity_year_rec(self) -> "tuple[bytearray, int]":
        return (int32_to_bytes(self._viewer_state.vel_year_rec), 1)

    def get_float_attribute(self, attr: np.ndarray) -> "tuple[bytearray, int]":
        self._viewer.debug('Executing get_float_attribute()', 4)
        attr_bytes = float32_list_to_bytes(attr.tolist())
        return (attr_bytes, len(attr))

    def get_colormap(self) -> "tuple[bytearray, bytearray, bytearray, bytearray, int]":
        formatted_colormap = None
        if hasattr(self.state.cmap, 'colors'):
            formatted_colormap = [[c[0], c[1], c[2], 1.0] for c in self.state.cmap.colors]
        else:
            # Has no underlying colors we can reach simply (according to our research)
            # Sample the color map with equal strides as many times as how many colors it's built with
            number_of_samples = self.state.cmap.N if self.state.cmap.N is not None else 256
            samples = get_normalized_list_of_equal_strides(number_of_samples)
            formatted_colormap = [
                [ch for ch in self.state.cmap(x)] for x in samples
            ]

        r = bytearray()
        g = bytearray()
        b = bytearray()
        a = bytearray()
        for _color in formatted_colormap:
            color = self.get_color(_color)
            r += color[0]
            g += color[1]
            b += color[2]
            a += color[3]

        return (r, g, b, a, len(formatted_colormap))

    def get_colormap_limits(self) -> "tuple[bytearray, bytearray]":
        vmin = float32_to_bytes(float(self.state.cmap_vmin))
        vmax = float32_to_bytes(float(self.state.cmap_vmax))
        return (vmin, vmax)

    def get_attrib_data(self, attribute) -> "tuple[bytearray, int]":
        attrib_data = self.state.layer[attribute]

        result = bytearray()

        for value in attrib_data:
            result += float32_to_bytes(float(value))

        return result, len(attrib_data)

