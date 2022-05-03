import os

from qtpy.QtCore import Qt
from qtpy.QtGui import QImage, QPixmap
from qtpy.QtWidgets import QLabel, QLineEdit, QHBoxLayout, QVBoxLayout, QPushButton, QWidget

from glue.utils.qt import messagebox_on_error
from glue.viewers.common.qt.data_viewer import DataViewer

from .viewer_state import OpenSpaceViewerState
from .layer_artist import OpenSpaceLayerArtist
from .viewer_state_widget import OpenSpaceViewerStateWidget
from .layer_state_widget import OpenSpaceLayerStateWidget

__all__ = ['OpenSpaceDataViewer']

LOGO = os.path.abspath(os.path.join(os.path.dirname(__file__), 'logo.png'))

class OpenSpaceDataViewer(DataViewer):

    LABEL = 'OpenSpace Viewer'
    _state_cls = OpenSpaceViewerState
    _data_artist_cls = OpenSpaceLayerArtist
    _subset_artist_cls = OpenSpaceLayerArtist
   
    # Additional attributes for Qt viewers
    _options_cls = OpenSpaceViewerStateWidget
    _layer_style_widget_cls = OpenSpaceLayerStateWidget

    def __init__(self, *args, **kwargs):
        super(OpenSpaceDataViewer, self).__init__(*args, **kwargs)

        # Set up Qt UI
        self._image = QPixmap.fromImage(QImage(LOGO))

        self._logo = QLabel()
        self._logo.setPixmap(self._image)
        self._logo.setAlignment(Qt.AlignCenter)

        self._ip = QLineEdit()
        self._ip.setText('http://localhost:4700/')
        self._ip.setEnabled(False)
        # self._ip.displayText() # How to get _ip's text

        self._conn_disc_button = QPushButton('Connect')
        
        self._layout = QVBoxLayout()
        self._layout.addWidget(self._logo)

        self._horizontal = QHBoxLayout(self)
        self._horizontal.addWidget(self._ip)
        self._horizontal.addWidget(self._conn_disc_button)
        
        self._layout.addLayout(self._horizontal)
       
        self._main = QWidget()
        self._main.setLayout(self._layout)

        self.setCentralWidget(self._main)

        self.close_event_action = None
        
    # Functionality of button is set in layer_artist
    def set_conn_disc_button(self, buttonFunc):
        self._conn_disc_button.clicked.connect(buttonFunc)
    
    # Close event actions are set in layer_artist
    def set_close_event_action(self, close_event_func):
        self.close_event_action = close_event_func
    
    def get_layer_artist(self, cls, layer=None, layer_state=None):
        return cls(self, self.state, layer=layer, layer_state=layer_state)

    # Overridden Qt function
    def closeEvent(self, event):
        self.close_event_action()
        