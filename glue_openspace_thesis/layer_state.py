from __future__ import absolute_import, division, print_function

from glue.config import colormaps
from glue.external.echo import (CallbackProperty, SelectionCallbackProperty, keep_in_sync, delay_callback)
from glue.viewers.common.state import LayerState

from glue.core.data_combo_helper import ComponentIDComboHelper
from glue.core.state_objects import StateAttributeLimitsHelper
from glue.viewers.matplotlib.state import (DeferredDrawCallbackProperty as DDCProperty,
                                           DeferredDrawSelectionCallbackProperty as DDSCProperty)
# from glue.config import ColormapRegistry as colormaps

__all__ = ['OpenSpaceLayerState']


class OpenSpaceLayerState(LayerState):

    layer = CallbackProperty()
    color = CallbackProperty()
    size = CallbackProperty()
    alpha = CallbackProperty()

    size_mode = SelectionCallbackProperty(default_index=0)

    # Color
    # (notice the diff classes 'DDCProperty' and 'DDSCProperty')
    cmap_mode = DDSCProperty(docstring="Whether to use color to encode an attribute")
    cmap_att = DDSCProperty(docstring="The attribute to use for the color")
    cmap_vmin = DDCProperty(docstring="The lower level for the colormap")
    cmap_vmax = DDCProperty(docstring="The upper level for the colormap")
    cmap = DDCProperty(docstring="The colormap to use (when in colormap mode)")

    def __init__(self, layer=None, **kwargs):

        self._sync_markersize = None

        super(OpenSpaceLayerState, self).__init__(layer=layer)

        self._sync_color = keep_in_sync(self, 'color', self.layer.style, 'color')
        self._sync_alpha = keep_in_sync(self, 'alpha', self.layer.style, 'alpha')
        self._sync_size = keep_in_sync(self, 'size', self.layer.style, 'markersize')

        self.color = self.layer.style.color
        self.size = self.layer.style.markersize
        self.alpha = self.layer.style.alpha

        # ====== NEW ======
        # self._sync_cmap = keep_in_sync(self, 'cmap', self.layer.style, 'cmap')
        # self.cmap = self.layer.style.cmap

        self.cmap_att_helper = ComponentIDComboHelper(self, 'cmap_att',
                                                     numeric=True,
                                                     categorical=False,
                                                     world_coord=True,
                                                     pixel_coord=False)
        self.limits_cache = {}
        self.cmap_lim_helper = StateAttributeLimitsHelper(self, attribute='cmap_att',
                                                          lower='cmap_vmin', 
                                                          upper='cmap_vmax',
                                                          limits_cache=self.limits_cache)

        OpenSpaceLayerState.cmap_mode.set_choices(self, ['Fixed', 'Linear'])
        OpenSpaceLayerState.size_mode.set_choices(self, ['Fixed'])

        
        self.add_callback('layer', self._on_layer_change)
        if layer is not None:
            self._on_layer_change()

        self.cmap = colormaps.members[0][1] # Set to first colormap

        self.update_from_dict(kwargs)

    def _layer_changed(self):

        super(OpenSpaceLayerState, self)._layer_changed()

        if self._sync_markersize is not None:
            self._sync_markersize.stop_syncing()

        if self.layer is not None:
            self.size = self.layer.style.markersize
            self._sync_markersize = keep_in_sync(self, 'size', self.layer.style, 'markersize')

    # Loads the columns into the cmap attributes 
    def _on_layer_change(self, layer=None):
        with delay_callback(self, 'cmap_vmin', 'cmap_vmax'):
            if self.layer is None:
                self.cmap_att_helper.set_multiple_data([])
            else:
                self.cmap_att_helper.set_multiple_data([self.layer])

    # def flip_cmap(self):
    #     """
    #     Flip the cmap_vmin/cmap_vmax limits.
    #     """
    #     self.cmap_lim_helper.flip_limits()

    @property
    def cmap_name(self):
        return colormaps.name_from_cmap(self.cmap)