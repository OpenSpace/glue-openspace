from __future__ import absolute_import, division, print_function
from typing import Literal, Union

from glue.config import colormaps
from echo import (CallbackProperty, keep_in_sync, delay_callback)
from glue.viewers.common.state import LayerState

from glue.core.data_combo_helper import ComponentIDComboHelper
from glue.core.state_objects import StateAttributeLimitsHelper
from glue.viewers.matplotlib.state import (DeferredDrawCallbackProperty as DDCProperty,
                                           DeferredDrawSelectionCallbackProperty as DDSCProperty)
# from glue.config import ColormapRegistry as colormaps
from glue.core import Subset

COLOR_TYPES = ['Fixed', 'Linear']
SIZE_TYPES = ['Fixed', 'Linear']
CMAP_NAN_MODES = ['Hide', 'FixedColor']

__all__ = ['OpenSpaceLayerState']

class OpenSpaceLayerState(LayerState):
    has_sent_initial_data: "bool"
    will_send_message: "bool"

    layer = CallbackProperty()
    color = CallbackProperty()
    alpha = CallbackProperty()

    size = CallbackProperty()
    size_mode: "Union[Literal['Fixed'], Literal['Linear']]" = DDSCProperty(docstring='Which size mode to use', default_index=0)
    size_att = DDSCProperty(docstring='The attribute to use for the size')
    size_vmin = DDCProperty(docstring='The lower level for the size')
    size_vmax = DDCProperty(docstring='The upper level for the size')

    # Color
    # (notice the diff classes 'DDCProperty' and 'DDSCProperty')
    color_mode: "Union[Literal['Fixed'], Literal['Linear']]" = DDSCProperty(docstring='Which color mode to use', default_index=0)
    cmap_att = DDSCProperty(docstring='The attribute to use for the color')
    cmap_vmin = DDCProperty(docstring='The lower level for the colormap')
    cmap_vmax = DDCProperty(docstring='The upper level for the colormap')
    cmap = DDCProperty(docstring='The colormap to use (when in colormap mode)')
    cmap_nan_mode: "Union[Literal['Hide'], Literal['FixedColor']]" = DDSCProperty(docstring='Which colormap attribute NaN value mode to use', default_index=0)
    cmap_nan_color = CallbackProperty('#fcba03', docstring='The colormap attribute NaN value color')

    def __init__(self, layer=None, **kwargs):
        self.has_sent_initial_data = False
        self.will_send_message = True

        self.limits_cache = {}

        self._sync_markersize = None

        super(OpenSpaceLayerState, self).__init__(layer=layer)

        self._sync_color = keep_in_sync(self, 'color', self.layer.style, 'color')
        self._sync_alpha = keep_in_sync(self, 'alpha', self.layer.style, 'alpha')
        self._sync_size = keep_in_sync(self, 'size', self.layer.style, 'markersize')

        self.color = self.layer.style.color
        self.alpha = self.layer.style.alpha
        self.size = self.layer.style.markersize
        self.cmap = colormaps.members[0][1] # Set to first colormap

        OpenSpaceLayerState.color_mode.set_choices(self, COLOR_TYPES)
        OpenSpaceLayerState.size_mode.set_choices(self, SIZE_TYPES)
        OpenSpaceLayerState.cmap_nan_mode.set_choices(self, CMAP_NAN_MODES)

        self.size_att_helper = ComponentIDComboHelper(self, 'size_att',
                                                     numeric=True,
                                                     categorical=False,
                                                     world_coord=True,
                                                     pixel_coord=False)
        self.size_lim_helper = StateAttributeLimitsHelper(self, attribute='size_att',
                                                          lower='size_vmin', 
                                                          upper='size_vmax',
                                                          limits_cache=self.limits_cache)

        self.cmap_att_helper = ComponentIDComboHelper(self, 'cmap_att',
                                                     numeric=True,
                                                     categorical=False,
                                                     world_coord=True,
                                                     pixel_coord=False)
        self.cmap_lim_helper = StateAttributeLimitsHelper(self, attribute='cmap_att',
                                                          lower='cmap_vmin', 
                                                          upper='cmap_vmax',
                                                          limits_cache=self.limits_cache)

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

        

    # Loads the columns into the cmap attributes
    def _on_layer_change(self, layer=None):
        with delay_callback(self, 'cmap_vmin', 'cmap_vmax', 'size_vmin', 'size_vmax'):
            helpers = [self.size_att_helper, self.cmap_att_helper]
            if self.layer is None:
                for helper in helpers:
                    helper.set_multiple_data([])
            else:
                for helper in helpers:
                    helper.set_multiple_data([self.layer])

    def flip_cmap(self):
        """
        Flip the cmap_vmin/cmap_vmax limits.
        """
        self.cmap_lim_helper.flip_limits()

    def flip_size(self):
        """
        Flip the size_vmin/size_vmax limits.
        """
        self.size_lim_helper.flip_limits()

    @property
    def cmap_name(self):
        return colormaps.name_from_cmap(self.cmap)
    

    def get_data(self): 
        if isinstance(self.layer, Subset):
            layer = self.layer.data
            subset_state = self.layer.subset_state
            # data = layer.new_subset(subset_state, label='testlabel')
        else:
            layer = self.layer
            subset_state = None
            data = None

        print('Data got from get_data in layer-state', layer)
        print('Subset state from get_data in layer-state', subset_state)
        print('Data from get_data in layer-state', data)