import os
from enum import Enum

from qtpy.QtWidgets import QWidget, QButtonGroup

from echo.qt import autoconnect_callbacks_to_qt
from glue.utils.qt import load_ui

__all__ = ['OpenSpaceViewerStateWidget']

class VelNaNRadioButtonId(int, Enum):
    Hide = 1
    Static = 2
    
class OpenSpaceViewerStateWidget(QWidget):

    def __init__(self, viewer_state=None, session=None):

        super(OpenSpaceViewerStateWidget, self).__init__()

        self._viewer_state = viewer_state

        self.ui = load_ui('viewer_state_widget.ui', self,
                          directory=os.path.dirname(__file__))

        self._connect = autoconnect_callbacks_to_qt(self._viewer_state, self.ui)

        self._viewer_state.add_callback('coordinate_system', self._update_visible_options)
        self._viewer_state.add_callback('velocity_mode', self._update_visible_options)
        self._update_visible_options()
        
        # # Taken from vispy Scatter
        # try:
        #     self._viewer_state.add_callback('*', self._update_from_state, as_kwargs=True)
        # except TypeError:  # glue-core >= 0.11
        #     self._viewer_state.add_global_callback(self._update_from_state)
        # self._update_from_state(force=True)

        # Set up vel NaN value option radio buttons
        self._init_vel_nan_modes()

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

        if self._viewer_state.velocity_mode == 'Motion':
            self.ui.velocity_stacked_widget.setCurrentIndex(1)
        else:
            self.ui.velocity_stacked_widget.setCurrentIndex(0)


    # def _update_from_state(self, force=False, **props):
    #     if force or 'vel_norm' in props:
    #         self._toggle_speed_att()

    # def _toggle_speed_att(self, *args, **kwargs):
    #     if self.ui.bool_vel_norm.isChecked():
    #         self.ui.combosel_speed_att.setEnabled(True)
    #     else:
    #         self.ui.combosel_speed_att.setEnabled(False)
    
    def _init_vel_nan_modes(self, *args):
        self._radio_vel_nan_mode = QButtonGroup()
        self._radio_vel_nan_mode.addButton(self.ui.radio_vel_nan_hide, id=VelNaNRadioButtonId.Hide)
        self._radio_vel_nan_mode.addButton(self.ui.radio_vel_nan_static, id=VelNaNRadioButtonId.Static)

        self.ui.radio_vel_nan_hide.toggled.connect(self._update_vel_nan_mode)
        self.ui.radio_vel_nan_static.toggled.connect(self._update_vel_nan_mode)

        # Set Hide button checked initially 
        self.ui.radio_vel_nan_hide.setChecked(True)
        self._update_vel_nan_mode()
        
    def _update_vel_nan_mode(self, *args):
        if self._radio_vel_nan_mode.checkedId() == VelNaNRadioButtonId.Hide:
            self._viewer_state.vel_nan_mode = 'Hide'
            self.ui.vel_nan_value_stacked_widget.setCurrentIndex(0)
            
        elif self._radio_vel_nan_mode.checkedId() == VelNaNRadioButtonId.Static:
            self._viewer_state.vel_nan_mode = 'Static'
            self.ui.vel_nan_value_stacked_widget.setCurrentIndex(1)

