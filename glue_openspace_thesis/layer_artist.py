import os
import json
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
    def websocket(self):
        return self._viewer.websocket

    def _on_attribute_change(self, **kwargs):

        force = kwargs.get('force', False)

        if self.websocket is None:
            return

        if self._viewer_state.lon_att is None or self._viewer_state.lat_att is None:
            return

        changed = self.pop_changed_properties()

        if len(changed) == 0 and not force:
            return

        if self._uuid:
            arguments = []
            if "color" in changed:
                arguments = ['Scene.' + self._uuid + '.Renderable.Color', to_rgb(self.state.color)]
            elif "alpha" in changed:
                arguments = ['Scene.' + self._uuid + '.Renderable.Opacity', self.state.alpha]
            elif ("size" in changed) or ("size_scaling" in changed):
                arguments = ['Scene.' + self._uuid + '.Renderable.Size',
                             (5 * self.state.size * self.state.size_scaling)]

            if arguments:
                message = generate_openspace_message("openspace.setPropertyValueSingle", arguments)
                self.websocket.send(json.dumps(message).encode('ascii'))
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
        arguments = [{"Identifier": self._uuid,
                      "Parent": "Root",
                      "Renderable": {"Type": "RenderablePointsCloud",
                                     "Color": colors,
                                     "File": temporary_file,
                                     "Size": (5 * self.state.size * self.state.size_scaling)},
                      "GUI": {
                          "Path": "/glue-viz",
                          "Name": self._display_name
                      }
                      }]

        message = generate_openspace_message("openspace.addSceneGraphNode", arguments)
        self.websocket.send(json.dumps(message).encode('ascii'))
        time.sleep(WAIT_TIME)

    def clear(self):
        if self.websocket is None:
            return
        if self._uuid is None:
            return
        message = {"topic": 4,
                   "type": "luascript",
                   "payload": {"function": "openspace.removeSceneGraphNode",
                               "arguments": [self._uuid],
                               "return": False}}

        self.websocket.send(json.dumps(message).encode('ascii'))
        self._uuid = None

        # Wait for a short time to avoid sending too many messages in quick succession
        time.sleep(WAIT_TIME * 10)

    def update(self):
        if self.websocket is None:
            return
        self._on_attribute_change(force=True)
