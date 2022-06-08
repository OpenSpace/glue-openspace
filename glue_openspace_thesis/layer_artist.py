from typing import TYPE_CHECKING, Any, Union
from matplotlib.colors import to_hex, to_rgb
from astropy import units
from astropy.coordinates import SkyCoord, Distance, BaseCoordinateFrame

from glue.core import Data, Subset
from glue.viewers.common.layer_artist import LayerArtist
import numpy as np

from .layer_state import OpenSpaceLayerState
from .viewer_state import OpenSpaceViewerState
from .simp import simp
from .utils import (
    get_normalized_list_of_equal_strides, float_to_hex,
    filter_lon_lat, filter_cartesian
)

__all__ = ['OpenSpaceLayerArtist']

POINT_DATA_PROPERTIES = set([
    "x_att",
    "y_att",
    "z_att",
    "cartesian_unit_att",
    "lon_att",
    "lat_att",
    "lum_att",
    "vel_att",
    "alt_att",
    "alt_unit"
])

FIXED_COLOR_PROPERTIES = set(['color_mode', 'color'])
CMAP_PROPERTIES = set(['color_mode', 'cmap_vmin', 'cmap_vmax', 'cmap', 'cmap_nan_mode', 'cmap_nan_color'])
CMAP_ATTR_PROPERTIES = set(['color_mode', 'cmap_att'])

FIXED_SIZE_PROPERTIES = set(['size_mode', 'size'])
SIZE_PROPERTIES = set(['size_mode', 'size', 'size_vmin', 'size_vmax'])
SIZE_ATTR_PROPERTIES = set(['size_mode', 'size_att'])

class OpenSpaceLayerArtist(LayerArtist):
    _layer_state_cls = OpenSpaceLayerState

    state: OpenSpaceLayerState
    _viewer_state: OpenSpaceViewerState

    if TYPE_CHECKING:
        from .viewer import OpenSpaceDataViewer
        _viewer: OpenSpaceDataViewer

    _display_name: str

    _removed_indices: np.ndarray

    has_updated_points: bool

    def __init__(self, viewer, *args, **kwargs):
        super(OpenSpaceLayerArtist, self).__init__(*args, **kwargs)

        self._viewer = viewer

        self.state.add_global_callback(self.update)
        self._viewer_state.add_global_callback(self.update)

        self._display_name = None
        self._state = None

        self.has_updated_points = False

    def _on_attribute_change(self, force):
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

        if self._viewer_state.coordinate_system != 'Cartesian'\
        and (self._viewer_state.lon_att is None or self._viewer_state.lat_att is None):
            return
        
        # If properties update in Glue, send message to OpenSpace with new values
        if self.state.will_send_message is False:
            return

        point_data_changed = any(prop in changed for prop in POINT_DATA_PROPERTIES)

        has_changed_fixed_color = any(prop in changed for prop in FIXED_COLOR_PROPERTIES) and self.state.color_mode == 'Fixed'
        has_changed_color_map = any(prop in changed for prop in CMAP_PROPERTIES) and self.state.color_mode == 'Linear'
        has_changed_color_map_att = any(prop in changed for prop in CMAP_ATTR_PROPERTIES) and self.state.color_mode == 'Linear'

        has_changed_fixed_size = any(prop in changed for prop in FIXED_SIZE_PROPERTIES) and self.state.size_mode == 'Fixed'
        has_changed_linear_size = any(prop in changed for prop in SIZE_PROPERTIES) and self.state.size_mode == 'Linear'
        has_changed_linear_size_att = any(prop in changed for prop in SIZE_ATTR_PROPERTIES) and self.state.size_mode == 'Linear'

        print(f'has_changed_linear_size_att={has_changed_linear_size_att}')

        if 'alpha' in changed:
            self.send_opacity()

        if has_changed_fixed_color:
            self.send_fixed_color()

        if has_changed_color_map:
            self.send_color_map()

        if has_changed_color_map_att:
            self.send_color_map_attrib_data()

        if has_changed_fixed_size:
            self.send_fixed_size()
            
        if has_changed_linear_size:
            self.send_linear_size()

        if has_changed_linear_size_att:
            self.send_linear_size_attrib_data()

        if 'visible' in changed:
            self.send_visibility()

        if point_data_changed:
            self.send_point_data()

            if self.has_updated_points:
                self.send_color_map_attrib_data()
                self.has_updated_points = False

        # # On reselect of subset data, remove old scene graph node and resend data
        # if isinstance(self.state.layer, Subset):
        #     state = self.state.layer.subset_state
        #     if state is not self._state:
        #         self._state = state
        #         # self.send_remove_sgn() # Should not be needed anymore
        #         self.send_point_data()
        #         self.redraw()
        #     return

        # # Store state of subset to track changes from reselection of subset
        # if isinstance(self.state.layer, Subset):
        #     self._state = self.state.layer.subset_state

        # Send the correct message to OpenSpace
        # if send_update_message:
        #     simp.send_simp_message(self._viewer, message_type, subject)
        # else:
        #     self.send_point_data()

        self.redraw()

    def _clean_properties(self, changed):
        if "alpha" in changed:
            if self.state.alpha > 1.0:
                self.state.alpha = 1.0
            elif self.state.alpha < 0.0:
                self.state.alpha = 0.0

        elif "size" in changed:
            if self.state.size > 500.0:
                self.state.size = 500.0
            elif self.state.size < 0.0:
                self.state.size = 0.0

    def receive_message(self, message_type: simp.SIMPMessageType, subject: str, offset: int):
        # Update Color
        if message_type == simp.SIMPMessageType.Color:
            color, offset = simp.read_color(subject, offset)
            color_value = to_hex(color, keep_alpha=False)

            self.state.will_send_message = False
            self.state.color = color_value

        # Update Opacity
        elif message_type == simp.SIMPMessageType.Opacity:
            opacity_value, offset = simp.read_float(subject, offset)

            self.state.will_send_message = False
            self.state.alpha = opacity_value

        # Update Size
        elif message_type == simp.SIMPMessageType.FixedSize:
            size_value, offset = simp.read_float(subject, offset)
            
            self.state.will_send_message = False
            self.state.size = size_value

        # Toggle Visibility
        elif message_type == simp.SIMPMessageType.Visibility:
            visibility_value, offset = simp.read_string(subject, offset)
            self.state.will_send_message = False

            self.state.visible = visibility_value == "T"

        # Change Colormap
        elif message_type == simp.SIMPMessageType.ColorMap:
            v_min, offset = simp.read_float(subject, offset)
            v_max, offset = simp.read_float(subject, offset)

            self.state.cmap_vmin = v_min
            self.state.cmap_vmax = v_max
            # self.state.will_send_message = False

        self.state.will_send_message = True
        self.redraw()

    def send_opacity(self):
        subject = self.get_subject_prefix() + self.get_opacity_str() + simp.SEP
        simp.send_simp_message(self._viewer, simp.SIMPMessageType.Opacity, subject)

    def send_fixed_color(self):
        subject = self.get_subject_prefix() + self.get_color_str() + simp.SEP
        simp.send_simp_message(self._viewer, simp.SIMPMessageType.Color, subject)

    def send_color_map(self):
        vmin_str, vmax_str = self.get_color_map_limits_str()
        color_map_str, n_colors_str = self.get_color_map_str()
        cmap_nan_color = list(
            to_rgb(self.state.cmap_nan_color 
                    if (self.state.cmap_nan_color != None) 
                    else [0.0,1.0,0.0,1.0])
        )
        cmap_nan_color_str = self.get_color_str(cmap_nan_color) + simp.SEP if self.state.cmap_nan_mode == 'Color' else ''

        subject = (
            self.get_subject_prefix() +
            vmin_str + simp.SEP +
            vmax_str + simp.SEP +
            self.state.cmap_nan_mode + simp.SEP +
            cmap_nan_color_str + 
            n_colors_str + simp.SEP +
            color_map_str + simp.SEP
        )
        simp.send_simp_message(self._viewer, simp.SIMPMessageType.ColorMap, subject)

    def send_color_map_attrib_data(self):
        color_map_attrib_data_str, n_attrib_data_str = self.get_attrib_data_str(self.state.cmap_att)
        subject = (
            self.get_subject_prefix() +
            "ColormapAttributeData" + simp.SEP +
            n_attrib_data_str + simp.SEP +
            color_map_attrib_data_str + simp.SEP
        )
        simp.send_simp_message(self._viewer, simp.SIMPMessageType.AttributeData, subject)

    def send_fixed_size(self):
        subject = self.get_subject_prefix() + self.get_size_str() + simp.SEP
        simp.send_simp_message(self._viewer, simp.SIMPMessageType.FixedSize, subject)

    def send_linear_size(self):
        vmin_str, vmax_str = self.get_linear_size_limits_str()

        subject = (
            self.get_subject_prefix() +
            self.get_size_str() + simp.SEP +
            vmin_str + simp.SEP +
            vmax_str + simp.SEP
        )
        simp.send_simp_message(self._viewer, simp.SIMPMessageType.LinearSize, subject)

    def send_linear_size_attrib_data(self):
        linear_size_attrib_data_str, n_attrib_data_str = self.get_attrib_data_str(self.state.size_att)
        subject = (
            self.get_subject_prefix() +
            "LinearSizeAttributeData" + simp.SEP +
            n_attrib_data_str + simp.SEP +
            linear_size_attrib_data_str + simp.SEP
        )
        simp.send_simp_message(self._viewer, simp.SIMPMessageType.AttributeData, subject)

    def send_visibility(self):
        visible_str = 'T' if self.state.visible else 'F'
        subject = self.get_subject_prefix() + visible_str + simp.SEP
        simp.send_simp_message(self._viewer, simp.SIMPMessageType.Visibility, subject)

    # Create and send a message including the point data to OpenSpace
    def send_point_data(self):
        # Create string with coordinates for point data
        try:
            point_data_str, n_points_str = self.get_coordinates_str()
            self._viewer.log(f'Sending {n_points_str} points to OpenSpace')
            subject = (
                self.get_subject_prefix() +
                n_points_str + simp.SEP +
                str(3) + simp.SEP +
                point_data_str + simp.SEP
            )
            simp.send_simp_message(self._viewer, simp.SIMPMessageType.PointData, subject)

        except Exception as exc:
            self._viewer.log(f'Exception in send_point_data: {str(exc)}')

    def get_subject_prefix(self) -> str:
        identifier = self.get_identifier_str()
        gui_name = self.get_gui_name_str()
        return identifier + simp.SEP + gui_name + simp.SEP

    def send_initial_data(self):
        self.send_point_data()
        self.send_opacity()
        self.send_visibility()

        if self.state.color_mode == 'Linear':
            # If in color map mode, send color map messages
            self.send_color_map()
            self.send_color_map_attrib_data()
        else:
            self.send_fixed_color()

        if self.state.size_mode == 'Linear':
            # If in color map mode, send color map messages
            self.send_linear_size()
            self.send_linear_size_attrib_data()
        else:
            self.send_fixed_size()

        self.state.has_sent_initial_data = True

    # Create and send "Remove Scene Graph Node" message to OS
    def send_remove_sgn(self):
        message_type = simp.SIMPMessageType.RemoveSceneGraphNode
        subject = self.get_identifier_str() + simp.SEP
        simp.send_simp_message(self._viewer, message_type, subject)

    def clear(self):
        if self._viewer._socket is None:
            return

        self.send_remove_sgn()
        self.redraw()

    def update(self, **kwargs):
        # if isinstance(self.state.layer, Data) or isinstance(self.state.layer, Subset):
        #     self._viewer.check_and_add_instance(self.state.layer)

        force = kwargs.get('force', False)
        try:
            if self.get_identifier_str() is None:
                gui_name = self.get_gui_name_str()
                if gui_name is None:
                    raise simp.SimpError("Cannot set GUI name")

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
            self.send_initial_data()

    def get_identifier_str(self) -> Union[str, None]:
        self.state.has_sent_initial_data = False

        if isinstance(self.state.layer, Data):
            self._viewer._main_layer_uuid = self.state.layer.uuid
            return self.state.layer.uuid
        elif isinstance(self.state.layer, Subset):
            return self._viewer._main_layer_uuid + self.state.layer.label.replace('Subset ', '')
        else:
            return

    def get_color_str(self, color=None) -> str:
        """
        `color` should be [r, g, b] or [r, g, b, a].
        If `color` isn't specified, self.state.color 
        or green will be used.
        """
        if color == None:
            color = to_rgb(self.state.color if (self.state.color != None) 
                                            else [0.0,1.0,0.0,1.0])
        else:
            if not isinstance(color, list):
                self._viewer.log('The provided color is not of type list...')
                return

        r = float_to_hex(color[0])
        g = float_to_hex(color[1])
        b = float_to_hex(color[2])
        a = float_to_hex(color[3] if (len(color) == 4) else 1.0)

        return '[' + r + simp.SEP + g + simp.SEP + b + simp.SEP + a + simp.SEP + ']'

    def get_opacity_str(self) -> str:
        opacity = float_to_hex(self.state.alpha)
        return opacity

    def get_gui_name_str(self) -> Union[str, None]:
        if isinstance(self.state.layer, Data):
            self._display_name = self.state.layer.label
        elif isinstance(self.state.layer, Subset):
            self._display_name = self.state.layer.label + ' (' + self.state.layer.data.label + ')'
        else:
            return
        
        gui_name = self._display_name
        clean_gui_name: str = ''

        # Escape all potential occurences of the separator character inside the gui name
        for i in range(len(gui_name)):
            if (gui_name[i] == simp.SEP):
                clean_gui_name += '\\'
            clean_gui_name += gui_name[i]

        return clean_gui_name
        
    def get_size_str(self) -> str:
        size = float_to_hex(self.state.size)
        return size

    def get_linear_size_limits_str(self) -> tuple[str, str]:
        vmin = float_to_hex(float(self.state.size_vmin))
        vmax = float_to_hex(float(self.state.size_vmax))
        return vmin, vmax

    def get_coordinates_str(self) -> tuple[str, str]:
        if self._viewer_state.coordinate_system == 'Cartesian':
            self.has_updated_points = True
            x, y, z, self._removed_indices = filter_cartesian(
                self.state.layer[self._viewer_state.x_att],
                self.state.layer[self._viewer_state.y_att],
                self.state.layer[self._viewer_state.z_att]
            )

            if self._viewer_state.cartesian_unit_att is not None and self._viewer_state.cartesian_unit_att != 'pc':
                # Get the unit from the gui
                unit = units.Unit(self._viewer_state.cartesian_unit_att)
                # Convert to parsec, since that's what OpenSpace wants
                x = (x * unit).to_value(units.pc)
                y = (y * unit).to_value(units.pc)
                z = (z * unit).to_value(units.pc)
            
        else:
            frame = self._viewer_state.coordinate_system.lower()
            unit = units.Unit(self._viewer_state.alt_unit)

            if self._viewer_state.alt_att is None or unit is None:
                self.has_updated_points = True
                longitude, latitude, _, self._removed_indices = filter_lon_lat(
                    self.state.layer[self._viewer_state.lon_att],
                    self.state.layer[self._viewer_state.lat_att]
                )

                # Get cartesian coordinates on unit galactic sphere
                coordinates = SkyCoord(longitude, latitude, unit='deg', frame=frame)
                x, y, z = coordinates.galactic.cartesian.xyz

                # Convert to be on a sphere of radius 100pc
                radius = 100 * units.pc
                x *= radius
                y *= radius
                z *= radius

            else:
                self.has_updated_points = True
                longitude, latitude, distance, self._removed_indices = filter_lon_lat(
                    self.state.layer[self._viewer_state.lon_att],
                    self.state.layer[self._viewer_state.lat_att],
                    self.state.layer[self._viewer_state.alt_att]
                )
                
                # Get cartesian coordinates on unit galactic sphere
                coordinates = SkyCoord(
                    longitude * units.deg,
                    latitude * units.deg,
                    distance=distance * units.Unit(unit),
                    frame=frame
                )
                x, y, z = coordinates.galactic.cartesian.xyz

                # print(type(x), [str(_x) for _x in x])

                # Convert coordinates to parsec
                x = x.to_value(units.pc)
                y = y.to_value(units.pc)
                z = z.to_value(units.pc)

        coordinates_string = ''
        n_points_str = str(len(x))

        for i in range(len(x)):
            coordinates_string += "["\
                + float_to_hex(float(x[i])) + simp.SEP\
                + float_to_hex(float(y[i])) + simp.SEP\
                + float_to_hex(float(z[i])) + simp.SEP + "]"

        return coordinates_string, n_points_str
    
    def get_color_map_str(self) -> tuple[str, str]:
        formatted_color_map = None
        if hasattr(self.state.cmap, 'colors'):
            formatted_color_map = [[c[0], c[1], c[2], 1.0] for c in self.state.cmap.colors]
        else:
            # Has no underlying colors we can reach simply (according to our research)
            # Sample the color map with equal strides as many times as how many colors it's built with
            number_of_samples = self.state.cmap.N if self.state.cmap.N is not None else 256
            samples = get_normalized_list_of_equal_strides(number_of_samples)
            formatted_color_map = [
                [ch for ch in self.state.cmap(x)] for x in samples
            ]

        n_colors_str = str(len(formatted_color_map))
        color_map_str = ''.join([self.get_color_str(color) for color in formatted_color_map])

        return color_map_str, n_colors_str

    def get_color_map_limits_str(self) -> tuple[str, str]:
        vmin = float_to_hex(float(self.state.cmap_vmin))
        vmax = float_to_hex(float(self.state.cmap_vmax))
        return vmin, vmax

    def get_attrib_data_str(self, attribute) -> tuple[str, str]:
        attrib_data = self.state.layer[attribute]

        # Filter away removed indices from list and convert to simp string
        attrib_data = [
            float_to_hex(float(x)) # if not np.isnan(x) else 1.0
            for i, x in enumerate(attrib_data)
            if i not in self._removed_indices
        ]

        return str(simp.SEP).join(attrib_data), str(len(attrib_data))

