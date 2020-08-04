import os
import uuid
import time
import shutil
import tempfile

import numpy as np

from glue.core import Data, Subset
from glue.viewers.common.layer_artist import LayerArtist

from .layer_state import OpenSpaceLayerState
from .utils import data_to_speck, generate_openspace_message

from matplotlib.colors import ColorConverter

to_rgb = ColorConverter().to_rgb

__all__ = ['OpenSpaceLayerArtist']

TEXTURE_ORIGIN = os.path.abspath(os.path.join(os.path.dirname(__file__), 'halo.png'))
TEXTURE = tempfile.mktemp(suffix='.png')
shutil.copy(TEXTURE_ORIGIN, TEXTURE)

# Time to wait after sending websocket message
WAIT_TIME = 0.05


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
            message = ""
            renderable = self._uuid
            length_of_renderable = str(len(self._uuid))
            if "alpha" in changed:
                # PLACEHOLDER CODE - DOESN'T WORK #
                message_type = "2"
                identifier = str(to_rgb(self.state.alpha))
                length_of_identifier = str(len(identifier))
                name = "alpha"
                length_of_name = str(len(name))
                message = message_type + "1" + length_of_renderable + length_of_identifier + length_of_name + renderable + identifier + name
                # PLACEHOLDER CODE - DOESN'T WORK #
                
            elif "color" in changed:
                message_type = "1"
                identifier = str(to_rgb(self.state.color))
                length_of_identifier = str(len(identifier))
                name = "color"
                length_of_name = str(len(name))
                message = message_type + length_of_renderable + length_of_identifier + length_of_name + renderable + identifier + name

            elif "size" in changed:
                # PLACEHOLDER CODE - DOESN'T WORK #
                message_type = "2"
                identifier = str(to_rgb(self.state.size))
                length_of_identifier = str(len(identifier))
                name = "size"
                length_of_name = str(len(name))
                message = message_type + "1" + length_of_renderable + length_of_identifier + length_of_name + renderable + identifier + name
                # PLACEHOLDER CODE - DOESN'T WORK #

            if message:
                # message = generate_openspace_message("openspace.softwareintegration.updateProperties", argument)
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

        r, g, b = to_rgb(self.state.color)
        colors = [r, g, b]
        alpha = self.state.alpha
        gui_name = self._display_name
        size = self.state.size
        arguments = [self._uuid, colors, temporary_file, alpha, size, gui_name]

        # message = generate_openspace_message("openspace.softwareintegration.addRenderable", arguments)
        # self.sock.send(json.dumps(message).encode('ascii'))

        self.sock.send(b'7Hi Glue')
        time.sleep(WAIT_TIME)

    def clear(self):
        if self.sock is None:
            return
        if self._uuid is None:
            return

        # message = generate_openspace_message("openspace.softwareintegration.removeRenderable", [self._uuid])
        # self.sock.send(json.dumps(message).encode('ascii'))
        self._uuid = None

        # Wait for a short time to avoid sending too many messages in quick succession
        time.sleep(WAIT_TIME * 10)

    def update(self):
        if self.sock is None:
            return
        self._on_attribute_change(force=True)
