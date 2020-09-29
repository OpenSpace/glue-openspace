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
from .utils import data_to_speck, data_to_binary

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
WAIT_TIME = 0.05

protocol_version = "1"
continueListening = True


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

        if self.sock is None:
            return

        if self._viewer_state.lon_att is None or self._viewer_state.lat_att is None:
            return

        changed = self.pop_changed_properties()

        if len(changed) == 0 and not force:
            return

        if self._uuid:
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
                time.sleep(WAIT_TIME)
            return

        self.clear()

        if not self.state.visible:
            return

        try:
            temporary_file = data_to_speck(self.state.layer,
                                           self._viewer_state.lon_att,
                                           self._viewer_state.lat_att,
                                           alternative_attribute=self._viewer_state.alt_att,
                                           alternative_unit=self._viewer_state.alt_unit,
                                           frame=self._viewer_state.frame)
        except Exception as exc:
            print(str(exc))
            return

        try:
            binary_data = data_to_binary(self.state.layer,
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

        self._uuid = str(uuid.uuid4())
        if isinstance(self.state.layer, Data):
            self._display_name = self.state.layer.label
        else:
            self._display_name = self.state.layer.label + ' (' + self.state.layer.data.label + ')'

        message_type = "DATA"
        subject = binary_data
        length_of_subject = str(format(len(subject), "09"))
        message = protocol_version + message_type + length_of_subject + subject
        self.sock.send(bytes(message, 'utf-8'))
        time.sleep(WAIT_TIME)
        message_type = "ASGN"
        length_of_file_path = str(len(temporary_file))
        identifier = self._uuid
        length_of_identifier = str(len(identifier))
        color = str(to_rgb(self.state.color))
        length_of_color = str(len(color))
        opacity = str(round(self.state.alpha, 4))
        length_of_opacity = str(len(opacity))
        gui_name = self._display_name
        length_of_gui = str(len(gui_name))
        size = str(self.state.size)
        length_of_size = str(len(size))
        subject = length_of_identifier + identifier + length_of_color + color + length_of_file_path + temporary_file + length_of_opacity + opacity + length_of_size + size + length_of_gui + gui_name
        length_of_subject = str(format(len(subject), "09"))

        message = protocol_version + message_type + length_of_subject + subject
        self.sock.send(bytes(message, 'utf-8'))
        time.sleep(WAIT_TIME)

    def request_listen(self):
        while continueListening:
            self.receive_message()
            time.sleep(WAIT_TIME)

    def receive_message(self):
        if self.sock is None:
            return

        message_received = self.sock.recv(4096).decode('ascii')
        print('Received message from socket: ', message_received)

        start = 0
        end = 4
        message_type = message_received[start:end]
        start += 4
        end += 4

        if "UPCO" in message_type:
            length_of_subject = int(message_received[start: end])
            start += 4
            end += length_of_subject
            subject = message_received[start:end]

            # Starting from subject
            start = 0
            end = 2
            length_of_identifier = int(subject[start:end])
            start += 2
            end += length_of_identifier
            identifier = subject[start:end]
            start += length_of_identifier
            end += 2
            length_of_value = int(subject[start:end])
            start = end
            end += length_of_value

            # Value is sent in this format: (redValue, greenValue, blueValue)
            string_value = subject[start + 1:end - 1]  # Don't include ( and )
            len_string_value = len(string_value)

            x = 0
            red = ""
            while string_value[x] is not ",":  # first value in string is before first ","
                red += string_value[x]
                x += 1
            r = float(red)

            x += 1
            green = ""
            while string_value[x] is not ",":  # second value in string is before second ","
                green += string_value[x]
                x += 1
            g = float(green)

            x += 1
            blue = ""
            for y in range(x, len_string_value):  # third value in string
                blue += string_value[y]
                y += 1
            b = float(blue)

            if self._uuid == identifier:
                self.state.color = to_hex([r, g, b])

        if "UPOP" in message_type:
            length_of_subject = int(message_received[start: end])
            start += 4
            end += length_of_subject
            subject = message_received[start:end]

            # Starting from subject
            start = 0
            end = 2
            length_of_identifier = int(subject[start:end])
            start += 2
            end += length_of_identifier
            identifier = subject[start:end]
            start += length_of_identifier
            end += 1
            length_of_value = int(subject[start:end])
            start = end
            end += length_of_value
            value = float(subject[start:end])

            self._uuid = identifier
            self._uuid.alpha = value

        if "UPSI" in message_type:
            length_of_subject = int(message_received[start: end])
            start += 4
            end += length_of_subject
            subject = message_received[start:end]

            # Starting from subject
            start = 0
            end = 2
            length_of_identifier = int(subject[start:end])
            start += 2
            end += length_of_identifier
            identifier = subject[start:end]
            start += length_of_identifier
            end += 1
            length_of_value = int(subject[start:end])
            start = end
            end += length_of_value
            value = float(subject[start:end])

            self._uuid = identifier
            self._uuid.size = value

        if "TOVI" in message_type:
            length_of_subject = int(message_received[start: end])
            start += 4
            end += length_of_subject
            subject = message_received[start:end]

            # Starting from subject
            start = 0
            end = 2
            length_of_identifier = int(subject[start:end])
            start += 2
            end += length_of_identifier
            identifier = subject[start:end]
            start += length_of_identifier
            value = subject[start]

            self._uuid = identifier
            if value is "F":
                self._uuid.visible = False
            else:
                self._uuid.visible = True

    def clear(self):
        if self.sock is None:
            return
        if self._uuid is None:
            return

        message_type = "RSGN"
        subject = self._uuid
        length_of_subject = str(format(len(subject), "09"))

        message = protocol_version + message_type + length_of_subject + subject
        self.sock.send(bytes(message, 'utf-8'))
        self._uuid = None

        # Wait for a short time to avoid sending too many messages in quick succession
        time.sleep(WAIT_TIME * 10)

    def update(self):
        if self.sock is None:
            return
        self._on_attribute_change(force=True)
