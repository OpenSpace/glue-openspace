import os
from threading import Thread
import socket
import uuid
import time
import shutil
import tempfile
from matplotlib.colors import to_hex, to_rgb, LinearSegmentedColormap, ListedColormap

from glue.core import Data, Subset
from glue.viewers.common.layer_artist import LayerArtist
from glue.utils.qt import messagebox_on_error
from glue.utils import ensure_numerical

from .layer_state import OpenSpaceLayerState
from .utils import (get_point_data, protocol_version, WAIT_TIME, SIMPMessageType,
                    color_string_to_hex, get_eight_bit_list, float_to_hex, 
                    hex_to_float, int_to_hex, hex_to_int, SEP)

__all__ = ['OpenSpaceLayerArtist']

# TODO move this to later
# TODO make this image selectable by user
TEXTURE_ORIGIN = os.path.abspath(os.path.join(os.path.dirname(__file__), 'halo.png'))
TEXTURE = tempfile.mktemp(suffix='.png')
shutil.copy(TEXTURE_ORIGIN, TEXTURE)
CMAP_PROPERTIES = set(['cmap_mode', 'cmap_att', 'cmap_vmin', 'cmap_vmax', 'cmap'])

class DisconnectionException(Exception):
    pass

class SocketDataEmptyException(Exception):
    pass

class OpenSpaceLayerArtist(LayerArtist):
    _layer_state_cls = OpenSpaceLayerState

    def __init__(self, viewer, *args, **kwargs):
        super(OpenSpaceLayerArtist, self).__init__(*args, **kwargs)

        self._viewer = viewer
        self._viewer.set_conn_disc_button(self.conn_disc_button_action) # Set functionality for button
        self._viewer.set_close_event_action(self.send_disconnect_message) # Set close event actions

        self.state.add_global_callback(self._on_attribute_change)
        self._viewer_state.add_global_callback(self._on_attribute_change)

        self._uuid = None
        self._display_name = None
        self._state = None

        self._socket = None

        self._thread_running = False
        self._threadCommsRx = None

        self._is_connected = False
        self._is_connecting = False
        self._lost_connection = False
        self.will_send_message = True
        # self.has_luminosity_data = False
        # self.has_velocity_data = False

    def start_socket_thread(self):
        if (self._threadCommsRx == None) or (not self._threadCommsRx.is_alive()): 
            self._lost_connection = False
            self._threadCommsRx = Thread(target=self.request_listen)
            self._thread_running = True
            self._threadCommsRx.start()

    def stop_socket_thread(self):
        self._thread_running = False
        self._threadCommsRx = None

    def _on_attribute_change(self, **kwargs):
        if self._socket is None:
            return

        if self._viewer_state.lon_att is None or self._viewer_state.lat_att is None:
            return
        
        # if self.state is not None:
        #     vmin = state.cmap_vmin
        #     vmax = state.cmap_vmax
        #     cmap = state.cmap

        changed = self.pop_changed_properties()
        force = kwargs.get('force', False)

        if len(changed) == 0 and not force:
            return

        # If properties update in Glue, send message to OpenSpace with new values
        if self._uuid is not None:
            if self.will_send_message is False:
                return

            message_type = ""
            subject = ""
            identifier, length_of_identifier = self.get_identifier_str()

            # TODO: Change so it only sends message on release of slider
            # Now it sends a message with every move of the slider
            if "alpha" in changed:
                message_type = SIMPMessageType.Opacity
                value, length_of_value = self.get_opacity_str()
                subject = length_of_identifier + identifier + length_of_value + value

            elif "color" in changed and self.state.cmap_mode is 'Fixed':
                message_type = SIMPMessageType.Color
                value, length_of_value = self.get_color_str()
                subject = length_of_identifier + identifier + length_of_value + value

            elif "size" in changed:
                message_type = SIMPMessageType.Size
                value, length_of_value = self.get_size_str()
                subject = length_of_identifier + identifier + length_of_value + value

            elif "visible" in changed:
                message_type = SIMPMessageType.Visibility
                if self.state.visible is False:
                    value = "F"
                elif self.state.visible is True:
                    value = "T"
                else:
                    return
                subject = length_of_identifier + identifier + value

            if any(prop in changed for prop in CMAP_PROPERTIES) \
                and self.state.cmap_mode is 'Linear':
                message_type = SIMPMessageType.ColorMap
                subject = self.get_cmap_subject(identifier)

            # TODO: Setup for GUI name change

            # print(f"message_type={message_type}, subject={subject}")
            # Send the correct message to OpenSpace
            if subject:
                self.send_simp_message(message_type, subject)
                self.redraw()
                return

            # On reselect of subset data, remove old scene graph node and resend data
            if isinstance(self.state.layer, Subset):
                state = self.state.layer.subset_state
                if state is not self._state:
                    self._state = state
                    self.remove_scene_graph_node()
                    self.send_point_data()
                    self.redraw()
                return

        self.clear() # TODO: WHY?

        # Store state of subset to track changes from reselection of subset
        if isinstance(self.state.layer, Subset):
            self._state = self.state.layer.subset_state

        self.send_point_data()
        self.redraw()

    # Create and send a message including the point data to OpenSpace
    def send_point_data(self):
        # Create string with coordinates for point data
        try:
            # Create a random identifier
            self._uuid = str(uuid.uuid4())
            if isinstance(self.state.layer, Data):
                self._display_name = self.state.layer.label
            else:
                self._display_name = self.state.layer.label + ' (' + self.state.layer.data.label + ')'

            identifier, length_of_identifier = self.get_identifier_str()
            color, length_of_color = self.get_color_str()
            opacity, length_of_opacity = self.get_opacity_str()
            gui_name, length_gui_name = self.get_gui_name_str()
            size, length_of_size = self.get_size_str()

            point_data = get_point_data(self.state.layer,
                                        self._viewer_state.lon_att,
                                        self._viewer_state.lat_att,
                                        alternative_attribute=self._viewer_state.alt_att,
                                        alternative_unit=self._viewer_state.alt_unit,
                                        frame=self._viewer_state.frame)

            print(f'len(point_data)={len(point_data)}')

            subject = (
                identifier + SEP +
                color + SEP +
                opacity + SEP +
                size + SEP +
                gui_name + SEP +
                int_to_hex(len(point_data)) + SEP +
                int_to_hex(3) + SEP +
                point_data + SEP
            )
            print(f'length_gui_name={length_gui_name}')
            self.send_simp_message(SIMPMessageType.PointData, subject)

            # If in linear cmap mode, send cmap message as well
            if self.state.cmap_mode is 'Linear':
                time.sleep(WAIT_TIME * 100) # TODO: Is there another way to make sure the renderable exists before we send a message to change it?
                self.send_simp_message(SIMPMessageType.ColorMap, self.get_cmap_subject(identifier))
            
        except Exception as exc:
            print(str(exc))
            return

    # Create and send "Remove Scene Graph Node" message to OS
    def remove_scene_graph_node(self):
        message_type = SIMPMessageType.RemoveSceneGraphNode
        subject = self._uuid
        self.send_simp_message(message_type, subject)

    def request_listen(self):
        print('Socket listener running...')
        try:
            max_connection_check_retries = 6000
            connection_check_retries = 0
            while self._thread_running:
                if self._lost_connection:
                    raise Exception('Lost connection to OpenSpace...')

                if self._is_connecting:
                    # If it takes more than 6000 (approx 60 seconds when WAIT_TIME is 0.01s)
                    # to connect to OpenSpace: cancel the connection attempt
                    if int(connection_check_retries) > int(max_connection_check_retries):
                        raise Exception("Connection timeout reached. Could not establish connection to OpenSpace...")

                    connection_check_retries += 1
                    self.receive_handshake()
                    time.sleep(WAIT_TIME)
                    continue
                
                if not self._is_connected:
                    time.sleep(WAIT_TIME * 10)
                    continue

                self.receive_message()
                time.sleep(WAIT_TIME * 10) # TODO: Is this needed?

        except DisconnectionException:
            pass

        except Exception as ex:
            print(str(ex))

        finally:
            print('Socket listener shutdown...')
            self.disconnect_from_openspace()

    def read_socket(self):
        message_received = self._socket.recv(4096).decode('ascii')

        if len(message_received) < 1:
            print(f'Received message had no content. Aborted.')
            raise SocketDataEmptyException

        return message_received

    def parse_message(self, message):
        # Start and end are message offsets
        start = 0
        end = 3
        protocol_version_in = message[start:end]
        if protocol_version_in != protocol_version:
            print('Mismatch in protocol versions')
            raise DisconnectionException

        start = end
        end = start + 4 
        message_type = message[start:end]

        start = end
        end = start + 15
        length_of_subject = int(message[start: end])

        start = end
        end = start + length_of_subject
        subject = message[start:end]

        return message_type, subject

    # Connection handshake to ensure connection is established
    def receive_handshake(self):
        try:
            message_received = self.read_socket()
        except:
            return

        message_type, _ = self.parse_message(message_received)

        print(message_type)
        if message_type != SIMPMessageType.Connection:
            return

        self._is_connected = True
        self._is_connecting = False
        self._viewer._conn_disc_button.setText('Disconnect') # Set button text
        self._viewer._conn_disc_button.setEnabled(True) # Set button enabled/disabled
        print('Connected to OpenSpace')

        # Update layers to trigger sending of data
        for layer in self._viewer.layers:
            layer.update()

    def receive_message(self):
        try:
            message_received = self.read_socket()
        except:
            return

        message_type, subject = self.parse_message(message_received)

        print(f'\tReceived new message: \'{message_type}\'')

        if message_type == SIMPMessageType.Disconnection:
            raise DisconnectionException

        # Resetting message offsets to read from subject
        start = 0
        end = 2
        length_of_identifier = int(subject[start:end])
        start += 2
        end += length_of_identifier
        identifier = subject[start:end]
        start += length_of_identifier
        if message_type == SIMPMessageType.Color:
            end += 2
        else:
            end += 1

        for layer in self._viewer.layers:
            if layer._uuid != identifier:
                continue

            # Update Color
            if message_type == SIMPMessageType.Color:
                length_of_value = int(subject[start:end])
                start = end
                end += length_of_value

                color_value, alpha = color_string_to_hex(subject[start + 1:end - 1])

                self.will_send_message = False
                layer.state.color = color_value
                break

            # Update Opacity
            elif message_type == SIMPMessageType.Opacity:
                length_of_value = int(subject[start:end])
                start = end
                end += length_of_value

                opacity_value = float(subject[start:end])

                self.will_send_message = False
                layer.state.alpha = opacity_value
                break

            # Update Size
            elif message_type == SIMPMessageType.Size:
                length_of_value = int(subject[start:end])
                start = end
                end += length_of_value

                size_value = float(subject[start:end])

                self.will_send_message = False
                layer.state.size = size_value
                break

            # Toggle Visibility
            elif message_type == SIMPMessageType.Visibility:
                visibility_value = subject[start]
                self.will_send_message = False

                layer.state.visible = visibility_value == "T"

        time.sleep(WAIT_TIME) # TODO: Is this needed?
        self.will_send_message = True
        self.redraw()

    def clear(self):
        if self._socket is None:
            return
        if self._uuid is None:
            return

        self.remove_scene_graph_node()
        self._uuid = None
        self.redraw()

    def update(self):
        if self._socket is None:
            return
        self._on_attribute_change(force=True)

    @messagebox_on_error('An error occurred when trying to reset socket:', sep=' ')
    def reset_socket(self):
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM,socket.IPPROTO_TCP)
        self._socket.settimeout(0.0)
        self._socket = socket.create_connection(('localhost', 4700))
        # self._socket = socket.connect(('localhost', 4700))

    @messagebox_on_error('An error occurred when trying to connect or disconnect from OpenSpace:', sep=' ')
    def conn_disc_button_action(self, *args):
        if self._is_connected:
            self.send_disconnect_message()
        else:
            self.connect_to_openspace()

    @messagebox_on_error('An error occurred when trying to connect to OpenSpace:', sep=' ')
    def connect_to_openspace(self, *args):
        print('Connecting to OpenSpace...')
        self._viewer._conn_disc_button.setEnabled(False) # Set button enabled/disabled
        self._viewer._conn_disc_button.setText('Connecting...') # Set button text

        self.start_socket_thread()
        self.reset_socket()

        # Send "Connection" message to OpenSpace
        self.send_simp_message(SIMPMessageType.Connection, 'Glue')
        self._is_connecting = True

    @messagebox_on_error('An error occurred when trying to send disconnection message to OpenSpace:', sep=' ')
    def send_disconnect_message(self, *args):
        # Send "DISC" message to OpenSpace
        self.send_simp_message(SIMPMessageType.Disconnection)
        
    def disconnect_from_openspace(self):
        self.stop_socket_thread()

        try:
            self._socket.shutdown(socket.SHUT_RDWR)
            self._socket.close()
        except:
            print('Couldn\'t shutdown socket to OpenSpace.')
        finally:
            self._socket = None
            self._is_connected = False
            self._uuid = None

        self._is_connected = False
        self._is_connecting = False
        self._lost_connection = False
        self._viewer._conn_disc_button.setText('Connect') # Set button text
        self._viewer._conn_disc_button.setEnabled(True) # Set button enabled/disabled
        print('Disconnected from OpenSpace')

    def get_identifier_str(self):
        identifier = self._uuid
        return identifier, str(len(identifier))

    def get_color_str(self, color=None):
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
                print('The provided color is not of type list...')
                return

        r = float_to_hex(color[0])
        g = float_to_hex(color[1])
        b = float_to_hex(color[2])
        a = float_to_hex(color[3] if (len(color) == 4) else 1.0)
        return '[' + r + SEP + g + SEP + b + SEP + a + SEP + ']', str(len(color))

    def get_opacity_str(self):
        # Round up to 7 decimals to avoid length_of_value being double digits
        # since OpenSpace expects the length_of_value to be 1 byte of the subject
        # opacity = str(round(self.state.alpha, 7))
        opacity = float_to_hex(self.state.alpha)
        return opacity, str(len(opacity))

    def get_gui_name_str(self):
        gui_name = self._display_name
        clean_gui_name = ''

        # Escape all potential occurences of the separator character inside the gui name
        for i in range(len(gui_name)):
            if (gui_name[i] == SEP):
                clean_gui_name += '\\'
            clean_gui_name += gui_name[i]

        return clean_gui_name, str(len(clean_gui_name))
        
    def get_size_str(self):
        # size = str(self.state.size)
        size = float_to_hex(self.state.size)
        return size, str(len(size))
    
    def get_rgb_from_cmap(self, scalar):
        """
        Returns a list of a 6 decimals R, G, B
        value based on the scalar value in the cmap.
        [R,G,B]
        """
        rgb = self.state.cmap(scalar)
        return [round(ch, 6) for ch in rgb]

    def get_linear_segmented_cmap_for_simp(self):
        return [self.get_rgb_from_cmap(x) for x in get_eight_bit_list()]

    def send_simp_message(self, message_type, subject=''):
        time.sleep(WAIT_TIME)
        length_of_subject = str(format(len(subject), '015d')) # formats to a 15 character string
        message = protocol_version + message_type + length_of_subject + subject

        subject_print_str = ', Subject[0:' + (length_of_subject if len(subject) < 40 else "40")
        subject_print_str += ']: ' + (subject if len(subject) < 40 else (subject[:40] + "..."))
        print_str = 'Protocol version: ' + protocol_version\
                    + ', Message type: ' + message_type\
                    + subject_print_str
        print(f'Sending SIMP message: ({print_str})')

        if self._is_connecting:
            print('Wait until plugin is connected to OpenSpace...')
            return
        
        try:
            self._socket.sendall(bytes(message, 'utf-8'))
        except:
            self._lost_connection = True

        # Wait for a short time to avoid sending too many messages in quick succession
        time.sleep(WAIT_TIME)

    def get_cmap_str_for_simp(self):
        cmap_for_simp = None
        if hasattr(self.state.cmap, 'colors'):
            cmap_for_simp = self.state.cmap.colors
            cmap_for_simp = [[c[0], c[1], c[2], 1.0] for c in cmap_for_simp]
        else:
            cmap_for_simp = self.get_linear_segmented_cmap_for_simp()

        nr_of_colors = str(len(cmap_for_simp))

        cmap_simp_hex_str = ''
        for color in cmap_for_simp:
            color_hex_str, len_color_hex_str = self.get_color_str(color)
            cmap_simp_hex_str += color_hex_str

        return cmap_simp_hex_str, nr_of_colors

    def get_cmap_subject(self, identifier):
        # scalars_for_points = ensure_numerical(self.layer[self.state.cmap_att].ravel())
        # print(f'\tscalars_for_points = {scalars_for_points}')

        cmap_simp_hex_str, nr_of_colors = self.get_cmap_str_for_simp()
        subject = identifier + SEP + cmap_simp_hex_str + SEP# + vmin + SEP + vmax + SEP + scalars_for_points + SEP
        return subject