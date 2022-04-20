from enum import Enum
import os
from threading import Thread
import socket
import uuid
import time
import shutil
import tempfile
import matplotlib
from matplotlib.colors import ColorConverter

from glue.core import Data, Subset
from glue.viewers.common.layer_artist import LayerArtist
from glue.utils.qt import messagebox_on_error

from .layer_state import OpenSpaceLayerState
from .utils import get_point_data, WAIT_TIME, send_simp_message


to_rgb = ColorConverter.to_rgb
to_hex = matplotlib.colors.to_hex

__all__ = ['OpenSpaceLayerArtist']

# TODO move this to later
# TODO make this image selectable by user
TEXTURE_ORIGIN = os.path.abspath(os.path.join(os.path.dirname(__file__), 'halo.png'))
TEXTURE = tempfile.mktemp(suffix='.png')
shutil.copy(TEXTURE_ORIGIN, TEXTURE)

# TODO: Change these to private
will_send_message = True
has_luminosity_data = False
has_velocity_data = False

class MessageType(str, Enum):
    CONN = 'CONN'
    DISC = 'DISC'
    PDAT = 'PDAT'
    RSGN = 'RSGN'
    UPCO = 'UPCO'
    UPOP = 'UPOP'
    UPSI = 'UPSI'
    TOVI = 'TOVI'

class OpenSpaceLayerArtist(LayerArtist):
    _layer_state_cls = OpenSpaceLayerState

    # socket = None

    def __init__(self, viewer, *args, **kwargs):

        super(OpenSpaceLayerArtist, self).__init__(*args, **kwargs)

        self._viewer = viewer
        self._viewer.set_conn_disc_button(self.conn_disc_button_action) # Set functionality for button
        self._viewer.set_close_event_action(self.close_actions) # Set close event actions

        self.state.add_global_callback(self._on_attribute_change)
        self._viewer_state.add_global_callback(self._on_attribute_change)

        self._uuid = None
        self._display_name = None
        self._state = None

        self._socket = None

        self._thread_running = False
        self._threadCommsRx = None

        self._is_connected = False

    def start_socket_thread(self):
        if (self._threadCommsRx == None) or (not self._threadCommsRx.is_alive()): 
            self._threadCommsRx = Thread(target=self.request_listen)
            self._thread_running = True
            self._threadCommsRx.start()

    def stop_socket_thread(self):
        self._thread_running = False
        # self._threadCommsRx.join()
        self._threadCommsRx = None

    
    def shutdown_connection(self):
        self.stop_socket_thread()
        self._socket.shutdown(socket.SHUT_RDWR)
        self._socket.close()
        self._socket = None
        self._is_connected = False
        self._uuid = None

    def close_actions(self):
        if self._is_connected:
            try:
                self.disconnect_from_openspace()
            except:
                self.shutdown_connection()

    def _on_attribute_change(self, **kwargs):

        global will_send_message
        
        force = kwargs.get('force', False)

        if self._socket is None:
            return

        if self._viewer_state.lon_att is None or self._viewer_state.lat_att is None:
            return

        changed = self.pop_changed_properties()

        if len(changed) == 0 and not force:
            return

        # If properties update in Glue, send message to OS with new values
        if self._uuid is not None:
            if will_send_message is False:
                return

            message_type = ""
            subject = ""
            identifier = self._uuid
            length_of_identifier = str(len(identifier))
            
            if "alpha" in changed:
                message_type = MessageType.UPOP #"UPOP"
                # Round up to 7 decimals to avoid length_of_value being double digits
                # since OpenSpace expects the length_of_value to be 1 byte of the subject
                value = str(round(self.state.alpha, 7))
                length_of_value = str(len(value))
                subject = length_of_identifier + identifier + length_of_value + value

            # TODO: Don't think this is ever used. A new PDAT message is called instead of updating the color
            # elif "color" in changed:
            #     message_type = MessageType.UPCO #"UPCO"
            #     print(f'message_type={message_type}, MessageType.UPCO={MessageType.UPCO}')
            #     value = str(to_rgb(self.state.color))
            #     length_of_value = str(len(value))
            #     subject = length_of_identifier + identifier + length_of_value + value

            elif "size" in changed:
                # print(f'UPDATING SIZE')
                message_type = MessageType.UPSI
                value = str(self.state.size)
                length_of_value = str(len(value))
                subject = length_of_identifier + identifier + length_of_value + value

            elif "visible" in changed:
                # print(f'UPDATING VISABILITY')
                message_type = MessageType.TOVI
                if self.state.visible is False:
                    value = "F"
                elif self.state.visible is True:
                    value = "T"
                else:
                    return
                subject = length_of_identifier + identifier + value

            # Send the correct message to OpenSpace
            if subject:
                send_simp_message(self._socket, message_type, subject)
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

        self.clear()

        # Store state of subset to track changes from reselection of subset
        if isinstance(self.state.layer, Subset):
            self._state = self.state.layer.subset_state

        self.send_point_data()
        self.redraw()

    # Create and send a message including the point data to OpenSpace
    def send_point_data(self):
        # Create string with coordinates for point data
        try:
            message_type = MessageType.PDAT

            # Create a random identifier
            self._uuid = str(uuid.uuid4())
            if isinstance(self.state.layer, Data):
                self._display_name = self.state.layer.label
            else:
                self._display_name = self.state.layer.label + ' (' + self.state.layer.data.label + ')'

            identifier = self._uuid
            length_of_identifier = str(len(identifier))

            color = str(to_rgb(self.state.color))
            length_of_color = str(len(color))

            opacity = str(round(self.state.alpha, 7))
            length_of_opacity = str(len(opacity))

            gui_name = self._display_name
            length_of_gui = str(len(gui_name))

            size = str(self.state.size)
            length_of_size = str(len(size))

            point_data = get_point_data(self.state.layer,
                                        self._viewer_state.lon_att,
                                        self._viewer_state.lat_att,
                                        alternative_attribute=self._viewer_state.alt_att,
                                        alternative_unit=self._viewer_state.alt_unit,
                                        frame=self._viewer_state.frame)

            subject = (
                length_of_identifier + identifier +
                length_of_color + color +
                length_of_opacity + opacity +
                length_of_size + size +
                length_of_gui + gui_name +
                point_data
            )
            send_simp_message(self._socket, message_type, subject)

        except Exception as exc:
            print(str(exc))
            return

    # Create and send "Remove Scene Graph Node" message to OS
    def remove_scene_graph_node(self):
        message_type = MessageType.RSGN
        subject = self._uuid
        send_simp_message(self._socket, message_type, subject)

    def request_listen(self):
        while self._thread_running:
            while self._socket is None:
                time.sleep(1.0) # TODO: Is this needed?
            self.receive_message()
            time.sleep(0.1) # TODO: Is this needed?

    def receive_message(self):

        global will_send_message
        try:
            message_received = self._socket.recv(4096).decode('ascii')
        except:
            return

        if len(message_received) < 1:
            print(f'Received message had no content. Aborted.')
            return

        # Start and end are message offsets
        start = 0
        end = 4
        message_type = message_received[start:end]
        start += 4
        end += 4
        length_of_subject = int(message_received[start: end])
        start += 4
        end += length_of_subject
        subject = message_received[start:end]

        # Resetting message offsets to read from subject
        start = 0
        end = 2
        length_of_identifier = int(subject[start:end])
        start += 2
        end += length_of_identifier
        identifier = subject[start:end]
        start += length_of_identifier
        if message_type == MessageType.UPCO: #"UPCO":
            end += 2
        else:
            end += 1

        for layer in self._viewer.layers:
            if layer._uuid == identifier:

                # Update Color
                if message_type == MessageType.UPCO: #"UPCO":"UPCO":
                    length_of_value = int(subject[start:end])
                    start = end
                    end += length_of_value

                    # Value is received in this format: (redValue, greenValue, blueValue)
                    UPCO_string_value = subject[start + 1:end - 1]  # Don't include ( and )
                    UPCO_len_string_value = len(UPCO_string_value)

                    x = 0
                    red = ""
                    while UPCO_string_value[x] != ",":  # first value in string is before first ","
                        red += UPCO_string_value[x]
                        x += 1
                    r = float(red)

                    x += 1
                    green = ""
                    while UPCO_string_value[x] != ",":  # second value in string is before second ","
                        green += UPCO_string_value[x]
                        x += 1
                    g = float(green)

                    x += 1
                    blue = ""
                    for y in range(x, UPCO_len_string_value):  # third value in string
                        blue += UPCO_string_value[y]
                        y += 1
                    b = float(blue)

                    UPCO_value = to_hex([r, g, b])

                    will_send_message = False
                    layer.state.color = UPCO_value
                    break

                # Update Opacity
                if message_type == MessageType.UPOP: #"UPOP":
                    length_of_value = int(subject[start:end])
                    start = end
                    end += length_of_value

                    UPOP_value = float(subject[start:end])

                    will_send_message = False
                    layer.state.alpha = UPOP_value
                    break

                # Update Size
                if message_type == MessageType.UPSI: #"UPSI":
                    length_of_value = int(subject[start:end])
                    start = end
                    end += length_of_value

                    UPSI_value = float(subject[start:end])

                    will_send_message = False
                    layer.state.size = UPSI_value
                    break

                # Toggle Visibility
                if message_type == MessageType.TOVI: #"TOVI":
                    TOVI_value = subject[start]
                    will_send_message = False

                    # TODO: CHANGE ORDER
                    if TOVI_value == "F":
                        layer.state.visible = False
                    else:
                        layer.state.visible = True
                    break

                break

        time.sleep(WAIT_TIME) # TODO: Is this needed?
        will_send_message = True
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
        self._is_connected = True
        # self._socket = socket.connect(('localhost', 4700))

    def conn_disc_button_action(self):
        if self._is_connected:
            self.disconnect_from_openspace()
            self._viewer._conn_disc_button.setText('Connect') # Set button text
        else:
            self.connect_to_openspace()
            self._viewer._conn_disc_button.setText('Disconnect') # Set button text


    @messagebox_on_error('An error occurred when trying to connect to OpenSpace:', sep=' ')
    def connect_to_openspace(self, *args):
        self.start_socket_thread()
        self.reset_socket()

        # Send "Connection" message to OS
        send_simp_message(self._socket, MessageType.CONN, 'Glue-Viz')
        print('Connected to OpenSpace')

        # Update layers to trigger sending of data
        for layer in self._viewer.layers:
            layer.update()
        

    @messagebox_on_error('An error occurred when trying to disconnect from OpenSpace:', sep=' ')
    def disconnect_from_openspace(self, *args):
        # Send "Disconnection" message to OS
        send_simp_message(self._socket, MessageType.DISC)
        self.shutdown_connection()
        print('Disconnected from OpenSpace')
