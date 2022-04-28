from __future__ import absolute_import, division, print_function

from glue.external.echo import (CallbackProperty, SelectionCallbackProperty, keep_in_sync)
from glue.viewers.common.state import LayerState

from glue.core.data_combo_helper import ComponentIDComboHelper

__all__ = ['OpenSpaceLayerState']


class OpenSpaceLayerState(LayerState):

    layer = CallbackProperty()
    color = CallbackProperty()
    size = CallbackProperty()
    alpha = CallbackProperty()

    size_mode = SelectionCallbackProperty(default_index=0)

    # color_mode = SelectionCallbackProperty(default_index=0)
    cmap_mode = SelectionCallbackProperty(docstring="Whether to use color to encode an attribute")
    cmap_att = SelectionCallbackProperty(docstring="The attribute to use for the color")
    
    # cmap_vmin = SelectionCallbackProperty(docstring="The lower level for the colormap")
    # cmap_vmax = SelectionCallbackProperty(docstring="The upper level for the colormap")


    def __init__(self, layer=None, **kwargs):

        self._sync_markersize = None

        super(OpenSpaceLayerState, self).__init__(layer=layer)

        self._sync_color = keep_in_sync(self, 'color', self.layer.style, 'color')
        self._sync_alpha = keep_in_sync(self, 'alpha', self.layer.style, 'alpha')
        self._sync_size = keep_in_sync(self, 'size', self.layer.style, 'markersize')

        self.color = self.layer.style.color
        self.size = self.layer.style.markersize
        self.alpha = self.layer.style.alpha

        OpenSpaceLayerState.cmap_mode.set_choices(self, ['Fixed', 'Linear'])
        OpenSpaceLayerState.size_mode.set_choices(self, ['Fixed'])

        self.cmap_att_helper = ComponentIDComboHelper(self, 'cmap_att',
                                                     numeric=True,
                                                     categorical=False,
                                                     world_coord=True,
                                                     pixel_coord=False)
        # self.limits_cache = {}
        # self.cmap_lim_helper = ComponentIDComboHelper(self, attribute='cmap_att',
        #                                                   lower='cmap_vmin', 
        #                                                   upper='cmap_vmax',
        #                                                   limits_cache=self.limits_cache)

        
        self.add_callback('layer', self._on_layer_change)
        if layer is not None:
            self._on_layer_change()

        self.update_from_dict(kwargs)

    def _layer_changed(self):

        super(OpenSpaceLayerState, self)._layer_changed()

        if self._sync_markersize is not None:
            self._sync_markersize.stop_syncing()

        if self.layer is not None:
            self.size = self.layer.style.markersize
            self._sync_markersize = keep_in_sync(self, 'size', self.layer.style, 'markersize')

    # loads the columns into the cmap attributes 
    def _on_layer_change(self, layer=None):
        # with delay_callback(self, 'cmap_vmin', 'cmap_vmax'):
        if self.layer is None:
            self.cmap_att_helper.set_multiple_data([])
        else:
            self.cmap_att_helper.set_multiple_data([self.layer])