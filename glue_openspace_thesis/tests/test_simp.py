import pytest
import struct

import astropy.units as units

from glue_openspace_thesis.utils import bool_to_bytes, float32_to_bytes, int32_to_bytes

from ..simp import simp

class MockSocket:
    def sendall(self):
        pass

class MockViewer:
    def __init__(self):
        self._lost_connection = False
        self._socket = MockSocket()
    
    def log(self):
        pass

def test_send_simp_message(mocker):
    mock_sendall = mocker.patch.object(MockSocket, 'sendall')
    viewer = MockViewer()
    simp.send_simp_message(viewer, simp.MessageType.Data, bytearray())

    assert mock_sendall.call_count == 1
    assert viewer._lost_connection == False

def test_parse_message(mocker):
    mock_log = mocker.patch.object(MockViewer, 'log')
    viewer = MockViewer()
    
    sent_header = f'{str(simp.protocol_version)}CONN000000000000000'
    message = bytearray(sent_header, 'utf-8')
    message_type, subject = simp.parse_message(viewer, message)
    assert len(subject) == 0
    assert message_type == 'CONN'
    assert mock_log.call_count == 0

    # Should log and throw if mismatch in protocol version
    sent_header = f'0.0.1CONN000000000000004'
    sent_subject = "Glue"
    message = bytearray(sent_header + sent_subject, 'utf-8')
    with pytest.raises(simp.DisconnectionException):
        message_type, subject = simp.parse_message(viewer, message)
    assert mock_log.call_count == 1

    # Works with subject
    sent_header = f'{str(simp.protocol_version)}CONN000000000000004'
    sent_subject = "Glue"
    message = bytearray(sent_header + sent_subject, 'utf-8')
    message_type, subject = simp.parse_message(viewer, message)
    assert len(subject) == 4
    assert str(subject, 'utf-8') == sent_subject
    assert message_type == 'CONN'

def test_check_offset():
    value = 2.0123456
    message = bytearray(struct.pack("f", value))
    offset = len(message) + 1

    # Check offset > len(message)
    with pytest.raises(simp.SimpError):
        simp.check_offset(message, [offset])

    # Check offset <= 0
    offset = -1
    with pytest.raises(simp.SimpError):
        simp.check_offset(message, [offset])

def test_read_float32():
    value = 2.0123456
    message = float32_to_bytes(value)
    offset = 0
    return_value, return_offset = simp.read_float32(message, offset)
    
    assert return_value == pytest.approx(value)
    assert return_offset == len(message)

def test_read_int32():
    value = 3689
    message = int32_to_bytes(value)
    offset = 0
    return_value, offset = simp.read_int32(message, offset)
    
    assert return_value == value
    assert offset == len(message)

def test_read_bool():
    value = True
    message = bool_to_bytes(value)
    offset = 0
    return_value, offset = simp.read_bool(message, offset)
    
    assert return_value == value
    assert offset == len(message)

def test_read_string():
    # Use raw strings in order to escape delimiter
    str1 = r"This is an awesome test\; And we must;"
    str2 = r" prevail;"
    str3 = r" ;"
    str4 = r"\n\; yes;"
    message = bytearray(str1 + str2 + str3 + str4, 'utf-8')
    offset = 0

    return_str, offset = simp.read_string(message, offset)
    assert return_str == r"This is an awesome test\; And we must"
    assert offset == len(str1)

    return_str, offset = simp.read_string(message, offset)
    assert return_str == r" prevail"
    assert offset == len(str1) + len(str2)

    return_str, offset = simp.read_string(message, offset)
    assert return_str == ' '
    assert offset == len(str1) + len(str2) + len(str3)

    return_str, offset = simp.read_string(message, offset)
    assert return_str == r"\n\; yes"
    assert offset == len(str1) + len(str2) + len(str3) + len(str4)

    with pytest.raises(simp.SimpError):
        return_str, offset = simp.read_string(message, offset)

def test_dist_unit_astropy_to_simp():
    assert simp.dist_unit_astropy_to_simp(units.m.to_string()) == simp.DistanceUnit.Meter
    assert simp.dist_unit_astropy_to_simp(units.km.to_string()) == simp.DistanceUnit.Kilometer
    assert simp.dist_unit_astropy_to_simp(units.AU.to_string()) == simp.DistanceUnit.AU
    assert simp.dist_unit_astropy_to_simp(units.lyr.to_string()) == simp.DistanceUnit.LightYears
    assert simp.dist_unit_astropy_to_simp(units.pc.to_string()) == simp.DistanceUnit.Parsec
    assert simp.dist_unit_astropy_to_simp(units.kpc.to_string()) == simp.DistanceUnit.Kiloparsec
    assert simp.dist_unit_astropy_to_simp(units.Mpc.to_string()) == simp.DistanceUnit.Megaparsec
    
    # Check if string
    with pytest.raises(simp.SimpError):
        simp.dist_unit_astropy_to_simp(units.m)

    # Check error
    with pytest.raises(simp.SimpError):
        simp.dist_unit_astropy_to_simp(units.hour.to_string())

def test_time_unit_astropy_to_simp():
    assert simp.time_unit_astropy_to_simp(units.s.to_string()) == simp.TimeUnit.Second
    assert simp.time_unit_astropy_to_simp(units.min.to_string()) == simp.TimeUnit.Minute
    assert simp.time_unit_astropy_to_simp(units.h.to_string()) == simp.TimeUnit.Hour
    assert simp.time_unit_astropy_to_simp(units.yr.to_string()) == simp.TimeUnit.Year
    
    # Check if string
    with pytest.raises(simp.SimpError):
        simp.time_unit_astropy_to_simp(units.hour)

    # Check error
    with pytest.raises(simp.SimpError):
        simp.time_unit_astropy_to_simp(units.m.to_string())
