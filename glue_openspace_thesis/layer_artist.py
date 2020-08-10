import os
import uuid
import time
import shutil
import tempfile

import numpy as np

from glue.core import Data, Subset
from glue.viewers.common.layer_artist import LayerArtist

from .layer_state import OpenSpaceLayerState
from .utils import data_to_speck

from matplotlib.colors import ColorConverter

to_rgb = ColorConverter().to_rgb

__all__ = ['OpenSpaceLayerArtist', 'protocol_version']

TEXTURE_ORIGIN = os.path.abspath(os.path.join(os.path.dirname(__file__), 'halo.png'))
TEXTURE = tempfile.mktemp(suffix='.png')
shutil.copy(TEXTURE_ORIGIN, TEXTURE)

# Time to wait after sending websocket message
WAIT_TIME = 0.05

protocol_version = "1"


class OpenSpaceLayerArtist(LayerArtist):
    _layer_state_cls = OpenSpaceLayerState

    def __init__(self, viewer, *args, **kwargs):

        super(OpenSpaceLayerArtist, self).__init__(*args, **kwargs)

        self._viewer = viewer

        self.state.add_global_callback(self._on_attribute_change)
        self._viewer_state.add_global_callback(self._on_attribute_change)

        self._uuid = None
        self._display_name = None

    @property
    def sock(self):
        return self._viewer.socket

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
                length_of_subject = str(format(len(subject), "04"))
                
            elif "color" in changed:
                message_type = "UPCO"
                value = str(to_rgb(self.state.color))
                length_of_value = str(len(value))
                subject = length_of_identifier + identifier + length_of_value + value
                length_of_subject = str(format(len(subject), "04"))

            elif "size" in changed:
                message_type = "UPSI"
                value = str(self.state.size)
                length_of_value = str(len(value))
                subject = length_of_identifier + identifier + length_of_value + value
                length_of_subject = str(format(len(subject), "04"))

            if subject:
                # message = generate_openspace_message("openspace.softwareintegration.updateProperties", argument)
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

        if isinstance(self.state.layer, Subset) and np.sum(self.state.layer.to_mask()) == 0:
            return

        self._uuid = str(uuid.uuid4())
        if isinstance(self.state.layer, Data):
            self._display_name = self.state.layer.label
        else:
            self._display_name = self.state.layer.label + ' (' + self.state.layer.data.label + ')'

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
        length_of_subject = str(format(len(subject), "04"))

        # message = generate_openspace_message("openspace.softwareintegration.addRenderable", arguments)

        message = protocol_version + message_type + length_of_subject + subject
        self.sock.send(bytes(message, 'utf-8'))
        time.sleep(WAIT_TIME)

    def clear(self):
        if self.sock is None:
            return
        if self._uuid is None:
            return

        message_type = "RSGN"
        identifier = self._uuid
        length_of_identifier = str(len(identifier))

        # message = generate_openspace_message("openspace.softwareintegration.removeRenderable", [self._uuid])
        message = protocol_version + message_type + length_of_identifier + identifier
        self.sock.send(bytes(message, 'utf-8'))
        self._uuid = None

        # Wait for a short time to avoid sending too many messages in quick succession
        time.sleep(WAIT_TIME * 10)

    def update(self):
        if self.sock is None:
            return
        self._on_attribute_change(force=True)
