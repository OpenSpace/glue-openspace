from enum import Enum
import os
import shutil
import socket
import tempfile
from threading import Thread
import time
from uuid import uuid4
from typing import Union

from qtpy.QtCore import Qt
from qtpy.QtGui import QImage, QPixmap, QIcon, QCursor
from qtpy.QtWidgets import (
    QLabel, QLineEdit, QGridLayout, QPushButton,
    QWidget, QSpacerItem, QSizePolicy, QHBoxLayout,
    QScrollArea, QVBoxLayout, QMainWindow,
    QStatusBar, QMenuBar
)
from qtpy.QtWidgets import qApp

from glue.utils.qt import messagebox_on_error
from glue.viewers.common.qt.data_viewer import DataViewer
from glue.viewers.common.qt.toolbar import BasicToolbar

from .simp import simp
from .utils import WAIT_TIME

from .viewer_state import OpenSpaceViewerState
from .layer_artist import OpenSpaceLayerArtist
from .viewer_state_widget import OpenSpaceViewerStateWidget
from .layer_state_widget import OpenSpaceLayerStateWidget

__all__ = ['OpenSpaceDataViewer']

# TODO move this to later
# TODO make this image selectable by user
TEXTURE_ORIGIN = os.path.abspath(os.path.join(os.path.dirname(__file__), 'halo.png'))
TEXTURE = tempfile.mktemp(suffix='.png')
shutil.copy(TEXTURE_ORIGIN, TEXTURE)
LOGO = os.path.abspath(os.path.join(os.path.dirname(__file__), 'logo.png'))

class OpenSpaceDataViewer(DataViewer):
    LABEL = 'OpenSpace Viewer'
    _state_cls = OpenSpaceViewerState
    _data_artist_cls = OpenSpaceLayerArtist
    _subset_artist_cls = OpenSpaceLayerArtist
   
    # Additional attributes for Qt viewers
    _options_cls = OpenSpaceViewerStateWidget
    _layer_style_widget_cls = OpenSpaceLayerStateWidget

    _toolbar_cls = BasicToolbar
    tools = []

    _thread_running: bool
    _threadCommsRx: Union[Thread, None]

    _is_connected: bool
    _is_connecting: bool
    _lost_connection: bool
    _has_been_connected: bool

    _failed_socket_read_retries: int
    
    _socket: Union[socket.socket, None]
    layers: list[OpenSpaceLayerArtist]

    ui: QWidget
    connection_button = QPushButton
    ip_textfield: QLineEdit

    _log_shown: bool
    _logs: list[str]

    _has_resized: bool

    state: OpenSpaceViewerState

    layer_identifiers = []

    _main_layer_uuid: str

    class ConnectionState(Enum):
        Disconnected = 0,
        Connected = 1,
        Connecting = 2,

    # @classmethod
    # @messagebox_on_error("Failed to open viewer. Another OpenSpace viewer already contains that layer.")
    # def check_and_add_instance(cls, data):
    #     print(cls.layer_identifiers)
    #     if any(saved_identifiers == data.uuid for saved_identifiers in cls.layer_identifiers):
    #         return False
    #     else:
    #         cls.layer_identifiers.append(data.uuid)
    #         return True

    # @classmethod
    # def remove_instance(cls, instance):
    #     cls.layer_identifiers = [i for i in cls.layer_identifiers if i not in [layer.state.layer.uuid for layer in instance.layers]]
    #     print(f'{cls.layer_identifiers}, to be removed: {[layer.state.layer.uuid for layer in instance.layers]}')

    # @classmethod
    # def remove_layer(cls, data):
    #     cls.layer_identifiers.remove(data.uuid)
    #     print(f'{cls.layer_identifiers}, to be removed: {data}')

    def __init__(self, *args, **kwargs):
        super(OpenSpaceDataViewer, self).__init__(*args, **kwargs)

        self._socket = None

        self._thread_running = False
        self._threadCommsRx = None

        self._has_been_connected = False
        self._is_connected = False
        self._is_connecting = False
        self._lost_connection = False

        self._log_shown = False
        self._logs = []

        self._has_resized = False

        self._viewer_identifier = str(uuid4())
        self._main_layer_uuid = ''

        # Set up Qt UI
        self.init_ui()

        self.allow_duplicate_data = False
        self.allow_duplicate_subset = False
        self.large_data_size = 1000000

    def init_ui(self):
        grid_layout = QGridLayout()
        
        logo = QLabel()
        pixmap = QPixmap(LOGO)
        pixmap = pixmap.scaledToHeight(100)
        logo.setPixmap(pixmap)
        logo.setFixedSize(pixmap.width(), pixmap.height())
        logo.setAlignment(Qt.AlignCenter)
        logo.setFixedHeight(100)
        grid_layout.addWidget(logo, 0, 0, 1, 4, Qt.AlignCenter)

        horizontal_layout = QHBoxLayout()
        horizontal_layout.setContentsMargins(0, 10, 0, 0)

        uri_label = QLabel()
        uri_label.setText('IP address:')
        horizontal_layout.addStretch()
        horizontal_layout.addWidget(uri_label)

        self.ip_textfield = QLineEdit()
        self.ip_textfield.setText('localhost:4700')
        self.ip_textfield.setEnabled(False)
        self.ip_textfield.setProperty('name', 'valuetext_uri')
        self.ip_textfield.setMinimumWidth(200)
        horizontal_layout.addWidget(self.ip_textfield)
        horizontal_layout.addStretch()

        horizontal_widget = QWidget()
        horizontal_widget.setLayout(horizontal_layout)
        grid_layout.addWidget(horizontal_widget, 1, 0, 1, 4, Qt.AlignCenter)

        self.connection_button = QPushButton('Connect')
        self.connection_button.setProperty('name', 'connection_button')
        self.connection_button.clicked.connect(self.connection_button_action)
        self.connection_button.setStyleSheet(
            "font-size: 25px; font-weight: 600;"
            "padding-left: 50px; padding-right: 50px;"
            "padding-top: 15px; padding-bottom: 15px;"
        )
        # self.connection_button.setStyleSheet(
        #     "font-size: 25px; font-weight: 600;"
        #     "background-color: #7AD1C9; color: #F1FAF9;"
        #     "padding-left: 50px; padding-right: 50px;"
        #     "padding-top: 10px; padding-bottom: 10px;"
        #     "border-width: 0px; border-radius: 20px;"
        # )
        self.connection_button.setCursor(QCursor(Qt.PointingHandCursor))
        grid_layout.addWidget(self.connection_button, 2, 0, 1, 4, Qt.AlignCenter)

        # self.show_log_button = QPushButton('Show log')
        # self.show_log_button.setCheckable(True)
        # self.show_log_button.clicked.connect(self.toggle_show_log)
        # self.show_log_button.setStyleSheet(
        #     "font-size: 17px; border-radius: 10px;"
        #     "padding-left: 20px; padding-right: 20px;"
        #     "padding-top: 10px; padding-bottom: 10px;"
        # )
        # self.show_log_button.setCursor(QCursor(Qt.PointingHandCursor))
        # grid_layout.addWidget(self.show_log_button, 3, 0, 1, 1, Qt.AlignLeft)

        # self.log_widget = QVBoxLayout()
        # self.log_widget.addStretch(1)
        # log = QWidget()
        # log.setLayout(self.log_widget)
        # log.setAutoFillBackground(True)
        # log.setMinimumWidth(400)
        # self.log_scroll = QScrollArea()
        # self.log_scroll.hide()
        # self.log_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        # self.log_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        # self.log_scroll.setWidget(log)
        # self.log_scroll.setMaximumHeight(500)
        # grid_layout.addWidget(self.log_scroll, 4, 0, 1, 4, Qt.AlignCenter)

        h_box = QHBoxLayout()
        h_box.addLayout(grid_layout)
        h_box.setAlignment(grid_layout, Qt.AlignCenter)
        
        self.ui = QWidget()
        self.ui.setLayout(h_box)
        self.setCentralWidget(self.ui)

        self.resize_window()

    # def toggle_show_log(self):
    #     if self._log_shown:
    #         self.log_scroll.hide()
    #         self.show_log_button.setText('Show log')
    #         self._log_shown = False

    #     else:
    #         self.log_scroll.show()
    #         self.show_log_button.setText('Hide log')
    #         self._log_shown = True

    #     self.resize_window()

    def set_connection_state(self, new_state: ConnectionState):
        # Set button enabled/disabled and button text
        if new_state == self.ConnectionState.Connected:
            self.connection_button.setText('Disconnect')
            self.connection_button.setEnabled(True)
            self._is_connected = True
            self._has_been_connected = True
            self._is_connecting = False
        
        elif new_state == self.ConnectionState.Disconnected:
            self.connection_button.setText('Connect')
            self.connection_button.setEnabled(True)
            self._is_connected = False
            self._is_connecting = False

        elif new_state == self.ConnectionState.Connecting:
            self.connection_button.setText('Connecting')
            self.connection_button.setEnabled(False)

        qApp.processEvents()

    def log(self, msg: str):
        print(f'OpenSpace Viewer ({self._viewer_identifier}): {msg}')

        if not isinstance(msg, str):
            return

        # new_msg = QLabel()
        # new_msg.setText(msg)
        # new_msg.setAlignment(Qt.AlignLeft)
        # self.log_widget.addWidget(new_msg)
        return

    def resize_window(self):
        qApp.processEvents()
        # button_size_hint = self.show_log_button.sizeHint()
        # self.show_log_button.resize(button_size_hint)
        size_hint = self.sizeHint()
        width = size_hint.width()
        height = size_hint.height() + 30

        self.resize(width, height)
        self.viewer_size = (width + 5, height + 5)

        qApp.processEvents()
        
    def start_socket_thread(self):
        if (self._threadCommsRx == None) or (not self._threadCommsRx.is_alive()): 
            self._lost_connection = False
            self._threadCommsRx = Thread(target=self.request_listen)
            self._thread_running = True
            self._threadCommsRx.start()

    def stop_socket_thread(self):
        self._thread_running = False
        self._threadCommsRx = None

    def request_listen(self):
        self.log('Socket listener running...')
        try:
            connection_check_retries = 0
            while self._thread_running:

                if self._lost_connection:
                    raise Exception('Lost connection to OpenSpace...')

                if self._is_connecting:
                    # If it takes more than 20 polls (approx 10 seconds when WAIT_TIME is 0.5s)
                    # to connect to OpenSpace: cancel the connection attempt
                    if connection_check_retries > 20:
                        time.sleep(WAIT_TIME)
                        raise Exception("Connection timeout reached. Could not establish connection to OpenSpace...")

                    connection_check_retries += 1
                    self.receive_handshake()
                    continue
                
                if not self._is_connected:
                    time.sleep(WAIT_TIME)
                    continue

                self.receive_message()

        except simp.DisconnectionException:
            pass

        except Exception as exc:
            self.log(f'Exception in request_listen: {str(exc)}')

        finally:
            self.log('Socket listener shutdown...')
            self.disconnect_from_openspace()

    def read_socket(self):
        try:
            message_received = self._socket.recv(4096).decode('ascii')
        except:
            self.log("Could not receive message. Disconnecting from OpenSpace...")
            raise simp.DisconnectionException

        if len(message_received) < 1:
            self.log(f'Received message had no content. Disconnecting from OpenSpace...')
            raise simp.DisconnectionException

        return message_received

    # Connection handshake to ensure connection is established
    def receive_handshake(self):
        message_received = self.read_socket()

        message_type, _ = simp.parse_message(self, message_received)

        if message_type != simp.SIMPMessageType.Connection:
            return

        self.set_connection_state(self.ConnectionState.Connected)
        self.log('Connected to OpenSpace')

        # Update layers to trigger sending of data
        for layer in self.layers:
            layer.update(force=True)

    def receive_message(self):
        message_received = self.read_socket()

        message_type, subject = simp.parse_message(self, message_received)

        self.log(f'Received new message: "{message_type}"')

        if message_type == simp.SIMPMessageType.Disconnection:
            raise simp.DisconnectionException

        try:
            offset = 0
            identifier, offset = simp.read_string(subject, offset)

            for layer in self.layers:
                if layer.get_identifier_str() == identifier:
                    layer.receive_message(message_type, subject, offset)

        except simp.SimpError as err:
            self.log(f'Couldn\'t read subject: {err.message}')
            return

    @messagebox_on_error('An error occurred when trying to reset socket:', sep=' ')
    def reset_socket(self):
        try:
            ip = self.ip_textfield.text().lower()
            if len(ip) < 8:
                raise simp.SimpError(f'The IP address {ip} is invalid')
                
            if ip.startswith('tcp://'):
                ip = ip[6:]

            [ip, port] = ip.split(':')

            if ip == 'localhost':
                ip = '127.0.0.1'

            ip_split = ip.split('.')
            if len(ip_split) != 4 and (
                any((not float(n).is_integer()) for n in ip_split) or (not float(port).is_integer())
            ):
                raise simp.SimpError(f'The IP address {ip} is invalid')


            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM,socket.IPPROTO_TCP)
            self._socket.settimeout(0.0)
            self._socket = socket.create_connection((ip, port if port != "" else 4700))
        
        except simp.SimpError as ex:
            self.set_connection_state(self.ConnectionState.Disconnected)
            self.log(f'Error when resetting socket: {ex.message}')
            raise Exception

        # self._socket = socket.create_connection(('localhost', 4700))
        # self._socket = socket.connect(('localhost', 4700))

    @messagebox_on_error('An error occurred when trying to connect or disconnect from OpenSpace:', sep=' ')
    def connection_button_action(self, *args):
        if self._is_connected:
            self.disconnect_from_openspace()
        else:
            self.connect_to_openspace()

    @messagebox_on_error('An error occurred when trying to connect to OpenSpace:', sep=' ')
    def connect_to_openspace(self, *args):
        self.log('Connecting to OpenSpace...')
        self.set_connection_state(self.ConnectionState.Connecting)

        self.start_socket_thread()
        self.reset_socket()

        # Send "Connection" message to OpenSpace
        subject = 'Glue' + simp.SEP
        # subject = 'Glue' + simp.SEP + self.state._software_identifier + simp.SEP
        simp.send_simp_message(self, simp.SIMPMessageType.Connection, subject)
        self._is_connecting = True

    @messagebox_on_error('An error occurred when trying to disconnect from OpenSpace:', sep=' ')
    def disconnect_from_openspace(self):
        self.stop_socket_thread()

        if self._has_been_connected:
            try:
                # Send "DISC" message to OpenSpace
                simp.send_simp_message(self, simp.SIMPMessageType.Disconnection)
            except:
                self.log("Didn't send disconnection message to OpenSpace")

        try:
            self._socket.shutdown(socket.SHUT_RDWR)
            self._socket.close()
        except:
            self.log('Couldn\'t shutdown socket to OpenSpace.')
        finally:
            self._socket = None

        # Reset _has_sent_initial_data so that layers send all data on next connection
        [setattr(layer, '_has_sent_initial_data', False) for layer in self.layers]

        self._lost_connection = False
        
        self.set_connection_state(self.ConnectionState.Disconnected)
        self.log('Disconnected from OpenSpace')
        
    def get_layer_artist(self, cls, layer=None, layer_state=None) -> OpenSpaceLayerArtist:
        return cls(self, self.state, layer=layer, layer_state=layer_state)

    # Overridden Qt function
    def closeEvent(self, event):
        # OpenSpaceDataViewer.remove_instance(self)
        if not self._is_connected or not self._is_connecting:
            return

        return self.disconnect_from_openspace()

    @messagebox_on_error("Failed to add data")
    def add_data(self, data) -> bool:
        # TODO: Here we can handle when new datasets are added, so we can send new data
        # This should be false, i.e one should not be able to add multiple datasets in one OpenSpace Viewer
        # This can be changed later on to add support for dataset "linking"
        # Return true if the dataset should be added, false if not

        # proceed = self.warn('Add large data set?', 'Data set {0:s} has {1:d} points, and '
        #                         'may render slowly.'.format(data.label, data.size),
        #                         default='Cancel', setting='show_large_data_warning')
        if len(self.layers) >= 1:
            raise Exception("Only one dataset per OpenSpace viewer")

        print(f'len(self.state.layers): {len(self.state.layers)}, len(self.layers): {len(self.layers)}')

        return super(OpenSpaceDataViewer, self).add_data(data)# and OpenSpaceDataViewer.check_and_add_instance(data)

    @messagebox_on_error("Failed to add subset")
    def add_subset(self, subset) -> bool:
        # TODO: Here we should handle to divide datasets into multiple SGNs in OpenSpace
        return super(OpenSpaceDataViewer, self).add_subset(subset) # Return true if the subset should be added, false if not

    def remove_data(self, data):
        [layer.send_remove_sgn() for layer in self.layers if layer.state.layer == data.uuid]
        # OpenSpaceDataViewer.remove_layer(data)
        super(OpenSpaceDataViewer, self).remove_data(data)

    def remove_subset(self, subset):
        [layer.send_remove_sgn() for layer in self.layers if layer.state.layer == subset.uuid]
        # OpenSpaceDataViewer.remove_layer(subset)
        super(OpenSpaceDataViewer, self).remove_subset(subset)

    @property
    def window_title(self):
        if len(self.state.layers) > 0:
            return ' OpenSpace Viewer: ' + self.state.layers[0].layer.label
        else:
            return ' OpenSpace Viewer'

    def initialize_toolbar(self):
        # The line below will add the save icon into the viewer
        # super(OpenSpaceDataViewer, self).initialize_toolbar()
        return

        