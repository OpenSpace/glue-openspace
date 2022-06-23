import struct
import numpy as np
import typing

__all__ = [
    'WAIT_TIME', 'POLL_RETRIES', 'get_normalized_list_of_equal_strides', 
    'float32_to_bytes', 'bytes_to_float32', 'int32_to_bytes', 'bytes_to_int32',
    'bool_to_bytes', 'bytes_to_bool', 'Version', 'print_attr_of_object_recursive'
]

WAIT_TIME = 0.5 # Time to wait before next poll
POLL_RETRIES = 10 # Amount of retries in sending a message to OpenSpace

class Version:
    major: int
    minor: int
    patch: int

    def __init__(self, major: int, minor: int, patch: int):
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
def int32_to_bytes(i: int) -> bytearray:
    byte_array_int = bytearray(struct.pack('!i', i))
    print(f'\tByte length of converted int={len(byte_array_int)}')
    return byte_array_int

def bool_to_bytes(b: bool) -> bytearray:
    return bytearray(struct.pack('!?', b))

def float32_to_bytes(f: float) -> bytearray:
    return bytearray(struct.pack('!f', f))

def float32_list_to_bytes(fl: list[float]) -> bytearray:
    return struct.pack(f'!{len(fl)}f', *fl)

def string_to_bytes(s: str) -> bytearray:
    return bytearray(s, 'utf-8')

def bytes_to_int32(i: bytearray) -> int:
    return int(struct.unpack('!i', i)[0])

def bytes_to_bool(b: bytearray) -> bool:
    return bool(struct.unpack('!?', b)[0])

def bytes_to_float32(f: bytearray) -> float:
    return float(struct.unpack('!f', f)[0])

def print_attr_of_object_recursive(obj, depth = 2, call_callables = False):
    initial_depth = depth

    print('\nPrinting Object:\n')

    def recursive_func(obj, depth):
        if depth == 0:
            return

        indent = initial_depth - depth

        print(''.join(['\t'] * indent) + f"type = {type(obj)}, obj =")
        for attrStr in dir(obj):
            if attrStr.startswith('__') or attrStr.count('byte')\
            or attrStr.count('string') or attrStr.count('dump'):
                continue

            attribute = getattr(obj, attrStr)
            print(''.join(['\t'] * (indent + 1)) + f'{attrStr} = {attribute}')

            if callable(attribute) and call_callables:
                try:
                    funcReturn = attribute()
                    print('\t' + f'calling {attrStr} returns:')
                    recursive_func(funcReturn, depth - 1)
                    continue
                except:
                    continue

            if not isinstance(attribute, int) and not isinstance(attribute, float) and not isinstance(attribute, list)\
            and not isinstance(attribute, str) and not isinstance(attribute, dict) and not isinstance(attribute, set):
                recursive_func(attribute, depth - 1)

    recursive_func(obj, depth)