import os

from qtpy.QtWidgets import QWidget

from echo.qt import autoconnect_callbacks_to_qt
from glue.utils.qt import load_ui

__all__ = ['OpenSpaceViewerStateWidget']

class OpenSpaceViewerStateWidget(QWidget):

    def __init__(self, viewer_state=None, session=None):

        super(OpenSpaceViewerStateWidget, self).__init__()

        self._viewer_state = viewer_state

        self.ui = load_ui('viewer_state_widget.ui', self,
                          directory=os.path.dirname(__file__))

        self._connect = autoconnect_callbacks_to_qt(self._viewer_state, self.ui)

        self._viewer_state.add_callback('coordinate_system', self._update_visible_options)
        self._update_visible_options()

    def _update_visible_options(self, *args, **kwargs):
        if self._viewer_state.coordinate_system == 'Cartesian':
            self.ui.coordinates_stacked_widget.setCurrentIndex(0)

        else:
            self.ui.coordinates_stacked_widget.setCurrentIndex(1)

            if self._viewer_state.coordinate_system in ['ICRS', 'FK5', 'FK4']:
                self.ui.label_lon_att.setText('Ra:')
                self.ui.label_lat_att.setText('Dec:')
            else:
                self.ui.label_lon_att.setText('Longitude:')
                self.ui.label_lat_att.setText('Latitude:')
