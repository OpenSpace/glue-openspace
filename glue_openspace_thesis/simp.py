from enum import Enum
import time
from typing import TYPE_CHECKING, Any, Type, Union

from astropy import units as ap_u
from .utils import POLL_RETRIES, WAIT_TIME, bytes_to_bool, bytes_to_float32, Version, bytes_to_int32

if TYPE_CHECKING:
    from .viewer import OpenSpaceDataViewer
    OpenSpaceDataViewer = OpenSpaceDataViewer
else:
    OpenSpaceDataViewer = Any

__all__ = ['simp']

class Simp:
    protocol_version = Version(1, 9, 1)
    DELIM = ';'
    DELIM_BYTES = bytearray(DELIM, 'utf-8')

    class MessageType(str, Enum):
        Connection = 'CONN'
        Data = 'DATA'
        RemoveSceneGraphNode = 'RSGN'

    class DataKey(str, Enum):
        # Point
        X = 'pos.x'
        Y = 'pos.y'
        Z = 'pos.z'
        PointUnit = 'pos.unit'
        # Velocity
        U = 'vel.u'
        V = 'vel.v'
        W = 'vel.w'
        VelocityDistanceUnit = 'vel.unit.dist'
        VelocityTimeUnit = 'vel.unit.time'
        VelocityDayRecorded = 'vel.t0.day'
        VelocityMonthRecorded = 'vel.t0.month'
        VelocityYearRecorded = 'vel.t0.year'
        VelocityNanMode = 'vel.nan.mode'
        VelocityEnabled = 'vel.enable'
        # Color
        Red = 'col.r'
        Green = 'col.g'
        Blue = 'col.b'
        Alpha = 'col.a'
        # Colormap
        ColormapEnabled = 'cmap.enable'
        ColormapRed = 'cmap.r'
        ColormapGreen = 'cmap.g'
        ColormapBlue = 'cmap.b'
        ColormapAlpha = 'cmap.a'
        ColormapMin = 'cmap.min'
        ColormapMax = 'cmap.max'
        ColormapNanR = 'cmap.nan.r'
        ColormapNanG = 'cmap.nan.g'
        ColormapNanB = 'cmap.nan.b'
        ColormapNanA = 'cmap.nan.a'
        ColormapNanMode = 'cmap.nan.mode'
        ColormapAttributeData = 'cmap.attr'
        # Fixed size
        FixedSize = 'size.val'
        # Linear size
        LinearSizeEnabled = 'lsize.enabled'
        LinearSizeMin = 'lsize.min'
        LinearSizeMax = 'lsize.max'
        LinearSizeAttributeData = 'lsize.attr'
        # Visibility
        Visibility = 'vis.val'

    class DistanceUnit(str, Enum):
        Meter = 'meters'
        Kilometer = 'km'
        AU = 'AU'
        LightYears = 'lightyears'
        Parsec = 'parsec'
        Kiloparsec = 'kiloparsec'
        Megaparsec = 'megaparsec'

    class TimeUnit(str, Enum):
        Second = 'second'
        Minute = 'minute'
        Hour = 'hour'
        Day = 'day'
        Year = 'year'

    class DisconnectionException(Exception):
        pass

    class SimpError(Exception):
        def __init__(self, message: str, *args, **kwargs):
            self.message = message

    @staticmethod
    def send_simp_message(viewer: OpenSpaceDataViewer, message_type: MessageType, subjectBuffer = bytearray()):
        length_of_subject = str(format(len(subjectBuffer), '015d')) # formats to a 15 character string
        message = bytes(str(simp.protocol_version) + message_type + length_of_subject, 'utf-8') + subjectBuffer

        # simp.print_simp_message(viewer, message_type, subject, length_of_subject)
        
        send_retries = 0
        message_sent = False
        while not message_sent and send_retries < POLL_RETRIES:
            try:
                viewer._socket.sendall(message)
                message_sent = True
            except:
                send_retries += 1
                time.sleep(WAIT_TIME)

        if not message_sent:
            viewer._lost_connection = True
        
    @staticmethod
    def parse_message(viewer: OpenSpaceDataViewer, message: bytearray):
        header_str = message[0:24].decode('utf-8')

        protocol_version_in = header_str[0:5]
        if protocol_version_in != str(simp.protocol_version):
            viewer.log('Mismatch in protocol versions')
            raise simp.DisconnectionException

        message_type = header_str[5:9]

        length_of_subject = int(header_str[9:])

        subject = message[24:(24 + length_of_subject)]

        return message_type, subject

    @staticmethod
    def check_offset(message: bytearray, _offset: Union[int, list[int]]):
        offsets: list[int]
        if isinstance(_offset, list):
            offsets = _offset
        else:
            offsets = [_offset]

        for offset in offsets:
            if offset > len(message):
                raise simp.SimpError('Offset is larger than length of message...')

            if offset < 0:
                raise simp.SimpError(f'Offset was {offset}, has to be >= 0')

    @staticmethod
    def read_float32(message: bytearray, offset: int) -> tuple[float, int]:
        simp.check_offset(message, [offset, (offset + 4)])
        byte_buffer = message[offset:(offset + 4)]

        try:
            value = bytes_to_float32(byte_buffer)
        except:
            raise simp.SimpError(f'Error when trying to parse a float at offset={offset}')

        offset += len(byte_buffer)
        return value, offset

    @staticmethod
    def read_int32(message: bytearray, offset: int) -> tuple[int, int]:
        simp.check_offset(message, [offset, (offset + 4)])
        byte_buffer = message[offset:(offset + 4)]

        try:
            value = bytes_to_int32(byte_buffer)
        except:
            raise simp.SimpError(f'Error when trying to parse an int at offset={offset}')

        offset += len(byte_buffer)
        return value, offset

    @staticmethod
    def read_bool(message: bytearray, offset: int) -> tuple[bool, int]:
        simp.check_offset(message, [offset, (offset + 1)])
        byte_buffer = message[offset:(offset + 1)]

        try:
            value = bytes_to_bool(byte_buffer)
        except:
            raise simp.SimpError(f'Error when trying to parse a bool at offset={offset}')

        offset += len(byte_buffer)
        return value, offset

    @staticmethod
    def read_string(message: bytearray, offset: int) -> tuple[str, int]:
        value: str = ''

        delimiter_offset = message.find(simp.DELIM_BYTES, offset)
        while message.find(bytearray('\\', 'utf-8'), delimiter_offset-1, delimiter_offset) != -1:
            delimiter_offset = message.find(simp.DELIM_BYTES, delimiter_offset + 1)

        if delimiter_offset == -1:
            raise simp.SimpError(f'No delimiter found for string')

        simp.check_offset(message, [offset, delimiter_offset])

        value = str(message[offset:delimiter_offset], "utf-8")
        offset = delimiter_offset + 1

        return value, offset

    @staticmethod
    def print_simp_message(viewer: OpenSpaceDataViewer, message_type: MessageType, subject='', length_of_subject=-1):
        subject_print_str = ', Subject[0:' + (length_of_subject if len(subject) < 40 else "40")
        subject_print_str += ']: ' + (subject if len(subject) < 40 else (subject[:40] + "..."))
        print_str = 'Protocol version: ' + simp.protocol_version\
                    + ', Message type: ' + message_type\
                    + subject_print_str
        viewer.log(f'Sending SIMP message: ({print_str})')

    @staticmethod
    def dist_unit_astropy_to_simp(astropy_unit: str) -> str:
        if not isinstance(astropy_unit, str):
            raise simp.SimpError(
                f'The provided unit \'{astropy_unit}\' '\
                + f'is of type \'{type(astropy_unit)}\'. '\
                + f'It must be of type {type(str())}'
            )

        if (astropy_unit is ap_u.m.to_string()):
            return simp.DistanceUnit.Meter
        elif (astropy_unit is ap_u.km.to_string()):
            return simp.DistanceUnit.Kilometer
        elif (astropy_unit is ap_u.AU.to_string()):
            return simp.DistanceUnit.AU
        elif (astropy_unit is ap_u.lyr.to_string()):
            return simp.DistanceUnit.LightYears
        elif (astropy_unit is ap_u.pc.to_string()):
            return simp.DistanceUnit.Parsec
        elif (astropy_unit is ap_u.kpc.to_string()):
            return simp.DistanceUnit.Kiloparsec
        elif (astropy_unit is ap_u.Mpc.to_string()):
            return simp.DistanceUnit.Megaparsec
        else:
            raise simp.SimpError(
                f'SIMP doesn\'t support the distance unit \'{astropy_unit}\''
            )

    @staticmethod
    def time_unit_astropy_to_simp(astropy_unit: str) -> str:
        if not isinstance(astropy_unit, str):
            raise simp.SimpError(
                f'The provided unit \'{astropy_unit}\' '\
                + f'is of type \'{type(astropy_unit)}\'. '\
                + f'It must be of type {type(str())}'
            )
        
        if (astropy_unit is ap_u.s.to_string()):
            return simp.TimeUnit.Second
        elif (astropy_unit is ap_u.min.to_string()):
            return simp.TimeUnit.Minute
        elif (astropy_unit is ap_u.h.to_string()):
            return simp.TimeUnit.Hour
        elif (astropy_unit is ap_u.yr.to_string()):
            return simp.TimeUnit.Year
        else:
            raise simp.SimpError(
                f'SIMP doesn\'t support the time unit \'{astropy_unit}\''
            )
    
simp = Simp()