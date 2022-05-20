from enum import Enum
import time
from typing import TYPE_CHECKING, Any

from .utils import POLL_RETRIES, WAIT_TIME, float_to_hex, hex_to_float

if TYPE_CHECKING:
    from .viewer import OpenSpaceDataViewer
    OpenSpaceDataViewer = OpenSpaceDataViewer
else:
    OpenSpaceDataViewer = Any

__all__ = ['simp']

class Simp:
    protocol_version = '1.8'
    SEP = ';'

    class SIMPMessageType(str, Enum):
        Connection = 'CONN'
        Disconnection = 'DISC'
        PointData = 'PDAT'
        RemoveSceneGraphNode = 'RSGN'
        Color = 'FCOL'
        ColorMap = 'LCOL'
        ColorMapAttributeData = 'ATDA'
        Opacity = 'FOPA'
        Size = 'FPSI'
        Visibility = 'TOVI'

    class DisconnectionException(Exception):
        pass

    class SimpError(Exception):
        def __init__(self, message: str, *args, **kwargs):
            self.message = message

    @staticmethod
    def send_simp_message(viewer: OpenSpaceDataViewer, message_type: SIMPMessageType, subject=''):
        length_of_subject = str(format(len(subject), '015d')) # formats to a 15 character string
        message = simp.protocol_version + message_type + length_of_subject + subject

        subject_print_str = ', Subject[0:' + (length_of_subject if len(subject) < 40 else "40")
        subject_print_str += ']: ' + (subject if len(subject) < 40 else (subject[:40] + "..."))
        print_str = 'Protocol version: ' + simp.protocol_version\
                    + ', Message type: ' + message_type\
                    + subject_print_str
        viewer.log(f'Sending SIMP message: ({print_str})')
        
        send_retries = 0
        message_sent = False
        while not message_sent and send_retries < POLL_RETRIES:
            try:
                viewer._socket.sendall(bytes(message, 'utf-8'))
                message_sent = True
            except:
                send_retries += 1
                time.sleep(WAIT_TIME)

        if not message_sent:
            viewer._lost_connection = True

    @staticmethod
    def parse_message(viewer: OpenSpaceDataViewer, message: str):
        # Start and end are message offsets
        start = 0
        end = 3
        protocol_version_in = message[start:end]
        if protocol_version_in != simp.protocol_version:
            viewer.log('Mismatch in protocol versions')
            raise simp.DisconnectionException

        start = end
        end = start + 4 
        message_type = message[start:end]

        start = end
        end = start + 15
        length_of_subject = int(message[start: end])

        start = end
        end = start + length_of_subject
        subject = message[start:end]

        return message_type, subject

    @staticmethod
    def is_end_of_current_value(message: str, offset: int) -> bool:
        if offset >= len(message):
            raise simp.SimpError("Unexpectedly reached the end of the message...")

        if (len(message) > 0 and offset == len(message) - 1 and message[offset] != simp.SEP):
            raise simp.SimpError("Reached end of message before reading separator character...")

        return offset > 0 and message[offset] == simp.SEP and message[offset - 1] != '\\'

    @staticmethod
    def read_float(message: str, offset: int) -> tuple[float, int]:
        string_value = ''

        while not simp.is_end_of_current_value(message, offset):
            string_value += message[offset]
            offset += 1

        try:
            value = hex_to_float(string_value)
        except:
            raise simp.SimpError(f'Error when trying to parse the float {string_value}')

        offset += 1
        return value, offset

    @staticmethod
    def read_int(message: str, offset: int) -> tuple[int, int]:
        string_value = ''

        while not simp.is_end_of_current_value(message, offset):
            string_value += message[offset]
            offset += 1

        try:
            value = int(string_value)
        except:
            raise simp.SimpError(f'Error when trying to parse the float {string_value}')

        offset += 1
        return value, offset

    @staticmethod
    def read_single_color(message: str, offset: int) -> tuple[tuple[float, float, float, float], int]:
        color, offset = simp.read_color(message, offset)
        offset += 1
        return color, offset

    @staticmethod
    def read_color(message: str, offset: int) -> tuple[tuple[float, float, float, float], int]:
        if message[offset] != '[':
            raise simp.SimpError(f'Expected to read "[", got {message[offset]} in "readColor"')
        offset += 1

        r, offset = simp.read_float(message, offset)
        g, offset = simp.read_float(message, offset)
        b, offset = simp.read_float(message, offset)
        a, offset = simp.read_float(message, offset)

        if message[offset] != ']':
            raise simp.SimpError(f'Expected to read "]", got {message[offset]} in "readColor"')
        offset += 1

        return (r, g, b, a), offset

    @staticmethod
    def read_string(message: str, offset: int) -> tuple[str, int]:
        value: str = ''

        while not simp.is_end_of_current_value(message, offset):
            value += message[offset]
            offset += 1

        offset += 1

        return value, offset

simp = Simp()