import os
import uuid
import time
import shutil
import tempfile
import matplotlib

import numpy as np
from glue.core import Data, Subset

from glue.viewers.common.layer_artist import LayerArtist

from .layer_state import OpenSpaceLayerState
from .utils import get_point_data, get_luminosity_data, get_velocity_data

from threading import Thread
from matplotlib.colors import ColorConverter

to_rgb = ColorConverter.to_rgb
to_hex = matplotlib.colors.to_hex

__all__ = ['OpenSpaceLayerArtist', 'protocol_version']

# TODO move this to later
# TODO make this image selectable by user
TEXTURE_ORIGIN = os.path.abspath(os.path.join(os.path.dirname(__file__), 'halo.png'))
TEXTURE = tempfile.mktemp(suffix='.png')
shutil.copy(TEXTURE_ORIGIN, TEXTURE)

# Time to wait after sending websocket message
WAIT_TIME = 0.01

protocol_version = "1"
continue_listening = True
will_send_message = True


class OpenSpaceLayerArtist(LayerArtist):
    _layer_state_cls = OpenSpaceLayerState

    def __init__(self, viewer, *args, **kwargs):

        super(OpenSpaceLayerArtist, self).__init__(*args, **kwargs)

        self._viewer = viewer

        self.state.add_global_callback(self._on_attribute_change)
        self._viewer_state.add_global_callback(self._on_attribute_change)

        self._uuid = None
        self._display_name = None

        self.threadCommsRx = Thread(target=self.request_listen)
        self.threadCommsRx.daemon = True
        self.threadCommsRx.start()

    @property
    def sock(self):
        return self._viewer.socket

    # def _on_visible_change(self, value=None):
    #     self.artist.set_visible(self.state.visible)
    #     self.redraw()
    #
    # def _on_zorder_change(self, value=None):
    #     self.artist.set_zorder(self.state.zorder)
    #     self.redraw()

    def _on_attribute_change(self, **kwargs):

        force = kwargs.get('force', False)
        global will_send_message

        if self.sock is None:
            return

        if self._viewer_state.lon_att is None or self._viewer_state.lat_att is None:
            return

        changed = self.pop_changed_properties()

        if len(changed) == 0 and not force:
            return

        # If properties update in Glue, send message to OS with new values
        if self._uuid:
            if will_send_message is False:
                will_send_message = True
                return

            message_type = ""
            subject = ""
            length_of_subject = ""
            identifier = self._uuid
            length_of_identifier = str(len(identifier))

            if "alpha" in changed:
                message_type = "UPOP"
                value = str(round(self.state.alpha, 4))
                length_of_value = str(len(value))
                subject = length_of_identifier + identifier + length_of_value + value
                length_of_subject = str(format(len(subject), "09"))

            elif "color" in changed:
                message_type = "UPCO"
                value = str(to_rgb(self.state.color))
                length_of_value = str(len(value))
                subject = length_of_identifier + identifier + length_of_value + value
                length_of_subject = str(format(len(subject), "09"))

            elif "size" in changed:
                message_type = "UPSI"
                value = str(self.state.size)
                length_of_value = str(len(value))
                subject = length_of_identifier + identifier + length_of_value + value
                length_of_subject = str(format(len(subject), "09"))

            elif "visible" in changed:
                message_type = "TOVI"
                if self.state.visible is False:
                    value = "F"
                elif self.state.visible is True:
                    value = "T"
                else:
                    return
                subject = length_of_identifier + identifier + value
                length_of_subject = str(format(len(subject), "09"))

            if subject:
                message = protocol_version + message_type + length_of_subject + subject
                self.sock.send(bytes(message, 'utf-8'))
                print('Messaged sent: ', message)
                for layer in self._viewer.layers:
                    print(layer)
                time.sleep(WAIT_TIME)
            return

        self.clear()

        if not self.state.visible:
            return

        # Create string with coordinates for point data
        try:
            point_data = get_point_data(self.state.layer,
                                        self._viewer_state.lon_att,
                                        self._viewer_state.lat_att,
                                        alternative_attribute=self._viewer_state.alt_att,
                                        alternative_unit=self._viewer_state.alt_unit,
                                        frame=self._viewer_state.frame)
        except Exception as exc:
            print(str(exc))
            return

        if isinstance(self.state.layer, Subset) and np.sum(self.state.layer.to_mask()) == 0:
            return

        # Create and send a message to OS including the point data
        DATA_message_type = "DATA"
        DATA_subject = point_data
        DATA_length_of_subject = str(format(len(DATA_subject), "09"))
        DATA_message = protocol_version + DATA_message_type + DATA_length_of_subject + DATA_subject
        self.sock.send(bytes(DATA_message, 'utf-8'))
        time.sleep(WAIT_TIME)

        # If the point data has associated luminosity data set - send it to OS
        if self._viewer_state.lum_att is not None:
            try:
                luminosity_data = get_luminosity_data(self.state.layer, self._viewer_state.lum_att)
                LUMI_message_type = "LUMI"
                LUMI_subject = luminosity_data
                LUMI_length_of_subject = str(format(len(LUMI_subject), "09"))
                LUMI_message = protocol_version + LUMI_message_type + LUMI_length_of_subject + LUMI_subject
                self.sock.send(bytes(LUMI_message, 'utf-8'))
                time.sleep(WAIT_TIME)
            except Exception as exc:
                print(str(exc))
                return

        # If the point data has associated velocity data set - send it to OS
        if self._viewer_state.vel_att is not None:
            try:
                velocity_data = get_velocity_data(self.state.layer, self._viewer_state.vel_att)
                VELO_message_type = "VELO"
                VELO_subject = velocity_data
                VELO_length_of_subject = str(format(len(VELO_subject), "09"))
                VELO_message = protocol_version + VELO_message_type + VELO_length_of_subject + VELO_subject
                self.sock.send(bytes(VELO_message, 'utf-8'))
                time.sleep(WAIT_TIME)
            except Exception as exc:
                print(str(exc))
                return

        # Create a random identifier
        self._uuid = str(uuid.uuid4())
        if isinstance(self.state.layer, Data):
            self._display_name = self.state.layer.label
        else:
            self._display_name = self.state.layer.label + ' (' + self.state.layer.data.label + ')'

        # Create an "Add Scene Graph Message" and send it to OS
        ASGN_message_type = "ASGN"
        ASGN_identifier = self._uuid
        ASGN_length_of_identifier = str(len(ASGN_identifier))
        ASGN_color = str(to_rgb(self.state.color))
        ASGN_length_of_color = str(len(ASGN_color))
        ASGN_opacity = str(round(self.state.alpha, 4))
        ASGN_length_of_opacity = str(len(ASGN_opacity))
        ASGN_gui_name = self._display_name
        ASGN_length_of_gui = str(len(ASGN_gui_name))
        ASGN_size = str(self.state.size)
        ASGN_length_of_size = str(len(ASGN_size))
        ASGN_subject = ASGN_length_of_identifier + ASGN_identifier + ASGN_length_of_color + ASGN_color + ASGN_length_of_opacity + ASGN_opacity + ASGN_length_of_size + ASGN_size + ASGN_length_of_gui + ASGN_gui_name
        ASGN_length_of_subject = str(format(len(ASGN_subject), "09"))

        ASGN_message = protocol_version + ASGN_message_type + ASGN_length_of_subject + ASGN_subject
        self.sock.send(bytes(ASGN_message, 'utf-8'))
        print('Messaged sent: ', ASGN_message)
        time.sleep(WAIT_TIME)

    def request_listen(self):
        while continue_listening:
            if not self.receive_message():
                return
            self.receive_message()

    def receive_message(self):
        if self.sock is None:
            return

        global will_send_message

        message_received = self.sock.recv(4096).decode('ascii')
        print('Received message from socket: ', message_received)

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
        if message_type == "UPCO":
            end += 2
        else:
            end += 1

        for layer in self._viewer.layers:
            if layer._uuid == identifier:

                if message_type == "UPCO":
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

                if message_type == "UPOP":
                    length_of_value = int(subject[start:end])
                    start = end
                    end += length_of_value

                    UPOP_value = float(subject[start:end])

                    will_send_message = False
                    layer.state.alpha = UPOP_value
                    break

                if message_type == "UPSI":
                    length_of_value = int(subject[start:end])
                    start = end
                    end += length_of_value

                    UPSI_value = float(subject[start:end])

                    will_send_message = False
                    layer.state.size = UPSI_value
                    break

                if message_type == "TOVI":
                    TOVI_value = subject[start]
                    will_send_message = False

                    if TOVI_value == "F":
                        layer.state.visible = False
                    else:
                        layer.state.visible = True
                    break

                break

    def clear(self):
        if self.sock is None:
            return
        if self._uuid is None:
            return

        # Create and send "Remove Scene Graph Node" message to OS
        message_type = "RSGN"
        subject = self._uuid
        length_of_subject = str(format(len(subject), "09"))

        message = protocol_version + message_type + length_of_subject + subject
        self.sock.send(bytes(message, 'utf-8'))
        self._uuid = None

        # Wait for a short time to avoid sending too many messages in quick succession
        time.sleep(WAIT_TIME)

    def update(self):
        if self.sock is None:
            return
        self._on_attribute_change(force=True)
        self.receive_message()

