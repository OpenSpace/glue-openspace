from __future__ import absolute_import, division, print_function

from glue.external.echo import (CallbackProperty, SelectionCallbackProperty, keep_in_sync)
from glue.viewers.common.state import LayerState

__all__ = ['OpenSpaceLayerState']


class OpenSpaceLayerState(LayerState):

    layer = CallbackProperty()
    color = CallbackProperty()
    size = CallbackProperty()
    alpha = CallbackProperty()

    size_mode = SelectionCallbackProperty(default_index=0)
    size_scaling = CallbackProperty(1)

    color_mode = SelectionCallbackProperty(default_index=0)
    cmap_mode = color_mode

    def __init__(self, layer=None, **kwargs):

        self._sync_markersize = None

        super(OpenSpaceLayerState, self).__init__(layer=layer)

        self._sync_color = keep_in_sync(self, 'color', self.layer.style, 'color')
        self._sync_alpha = keep_in_sync(self, 'alpha', self.layer.style, 'alpha')
        self._sync_size = keep_in_sync(self, 'size', self.layer.style, 'markersize')

        self.color = self.layer.style.color
        self.size = self.layer.style.markersize
        self.alpha = self.layer.style.alpha

        OpenSpaceLayerState.color_mode.set_choices(self, ['Fixed'])
        OpenSpaceLayerState.size_mode.set_choices(self, ['Fixed'])

        self.update_from_dict(kwargs)

    def _layer_changed(self):

        super(OpenSpaceLayerState, self)._layer_changed()

        if self._sync_markersize is not None:
            self._sync_markersize.stop_syncing()

        if self.layer is not None:
            self.size = self.layer.style.markersize
            self._sync_markersize = keep_in_sync(self, 'size', self.layer.style, 'markersize')
