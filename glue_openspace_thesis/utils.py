import struct
import numpy as np
import typing

__all__ = [
    'WAIT_TIME', 'POLL_RETRIES', 'get_normalized_list_of_equal_strides', 
    'float32_to_bytes', 'bytes_to_float32', 'int32_to_bytes', 'bytes_to_int32',
    'bool_to_bytes', 'bytes_to_bool', 'Version'
]

WAIT_TIME = 0.5 # Time to wait before next poll
POLL_RETRIES = 10 # Amount of retries in sending a message to OpenSpace

class Version:
    major: "int"
    minor: "int"
    patch: "int"

    def __init__(self, major: "int", minor: "int", patch: "int"):
        self.major = major
        self.minor = minor
        self.patch = patch

    def __repr__(self):
        return f'{self.major}.{self.minor}.{self.patch}'

    def __format__(self):
        return self.__repr__()

def get_normalized_list_of_equal_strides(amount = 256):
    return [i/amount for i in range(amount)]

# Convert to network byte order (big-endian)
def int32_to_bytes(i: "int") -> "bytearray":
    byte_array_int = bytearray(struct.pack('!i', i))
    print(f'\tByte length of converted int={len(byte_array_int)}')
    return byte_array_int

def bool_to_bytes(b: "bool") -> "bytearray":
    return bytearray(struct.pack('!?', b))

def float32_to_bytes(f: "float") -> "bytearray":
    return bytearray(struct.pack('!f', f))

def float32_list_to_bytes(fl: "list[float]") -> "bytearray":
    return struct.pack(f'!{len(fl)}f', *fl)

def string_to_bytes(s: "str") -> "bytearray":
    return bytearray(s, 'utf-8')

def bytes_to_int32(i: "bytearray") -> int:
    return int(struct.unpack('@i', i)[0])

def bytes_to_bool(b: "bytearray") -> "bool":
    return bool(struct.unpack('@?', b)[0])

def bytes_to_float32(f: "bytearray") -> "float":
    return float(struct.unpack('@f', f)[0])
