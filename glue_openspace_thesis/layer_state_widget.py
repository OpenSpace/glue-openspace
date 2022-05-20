from __future__ import absolute_import, division, print_function

import os

from qtpy.QtWidgets import QWidget

from echo.qt import autoconnect_callbacks_to_qt
from glue.utils.qt import load_ui, fix_tab_widget_fontsize

__all__ = ['OpenSpaceLayerStateWidget']

class OpenSpaceLayerStateWidget(QWidget):

    def __init__(self, layer_artist):

        super(OpenSpaceLayerStateWidget, self).__init__()

        self.ui = load_ui('layer_state_widget.ui', self, directory=os.path.dirname(__file__))

        fix_tab_widget_fontsize(self.ui.tab_widget)

        self.state = layer_artist.state
        self.layer_artist = layer_artist
        self.layer = layer_artist.layer

        connect_kwargs = {'value_size_scaling': dict(value_range=(0.1, 10), log=True)}
        self._connect = autoconnect_callbacks_to_qt(self.state, self.ui, connect_kwargs)

        # Set initial values
        self._update_size_mode()
        self._update_color_mode()

        self.state.add_callback('color_mode', self._update_color_mode)
        self.state.add_callback('size_mode', self._update_size_mode)

        self._viewer_state = layer_artist._viewer_state

        # self.ui.button_center.setVisible(False) # Never used

    def _update_size_mode(self, *args):
        # self.state.size = 10

        if self.state.size_mode == 'Fixed':
            self.ui.size_map_attributes.hide()
            self.ui.size_size.show()
        elif self.state.size_mode == 'Linear':
            self.ui.size_map_attributes.show()
            self.ui.size_size.hide()

    def _update_color_mode(self, *args):
        # self.state.color = '#00ff0s0'

        if self.state.color_mode == 'Fixed':
            self.ui.cmap_attributes.hide()
            self.ui.color_color.show()
        elif self.state.color_mode == 'Linear':
            self.ui.cmap_attributes.show()
            self.ui.color_color.hide()
