import struct
import numpy as np
import typing

__all__ = [
    'WAIT_TIME', 'POLL_RETRIES', 'get_normalized_list_of_equal_strides', 
    'float_to_hex', 'hex_to_float',
    'filter_lon_lat', 'filter_cartesian', 'print_attr_of_object_recursive'
]

WAIT_TIME = 0.5 # Time to wait before next poll
POLL_RETRIES = 10 # Amount of retries in sending a message to OpenSpace

# # DOESN'T WORK! USED FOR TESTING FOR FUTURE WORK
# def get_luminosity_data(data, luminosity_attribute):
#     luminosity_data = ""

#     luminosity_values = data[luminosity_attribute]

#     for i in range(len(luminosity_values)):
#         luminosity_data += (str(luminosity_values[i]) + ",")

#     length_luminosity_data = str(format(len(luminosity_data), "09"))

#     luminosity_data_string = length_luminosity_data + luminosity_data
#     return luminosity_data_string

# # DOESN'T WORK! USED FOR TESTING FOR FUTURE WORK
# def get_velocity_data(data, velocity_attribute):
#     velocity_data = ""

#     velocity_values = data[velocity_attribute]

#     for i in range(len(velocity_values)):
#         velocity_data += (str(velocity_values[i]) + ",")

#     length_velocity_data = str(format(len(velocity_data), "09"))

#     velocity_data_string = length_velocity_data + velocity_data
#      return velocity_data_string

def get_normalized_list_of_equal_strides(amount = 256):
    return [i/amount for i in range(amount)]

def float_to_hex(f):
    return hex(struct.unpack('<I', struct.pack('<f', f))[0])

def hex_to_float(f):
    as_bytes = bytearray.fromhex(f.lstrip('0x').rstrip('L'))
    return struct.unpack('>f', as_bytes)[0]

def filter_cartesian(_x: np.ndarray, _y: np.ndarray, _z: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    x = []
    y = []
    z = []
    removed_indices = []
    
    for i in range(len(_x)):
        if np.any(np.isnan(np.array([ _x[i], _y[i], _z[i] ]))):
            removed_indices.append(i)
        else:
            x.append(_x[i])
            y.append(_y[i])
            z.append(_z[i])

    removed_indices = np.unique(np.array(removed_indices))

    return np.array(x), np.array(y), np.array(z), removed_indices

def filter_lon_lat(_lon: np.ndarray, _lat: np.ndarray, _dist: typing.Optional[np.ndarray] = None) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    lon = []
    lat = []
    dist = None if _dist is None else []
    removed_indices = []

    for i in range(len(_lon)):
        if np.any(np.isnan(np.array([ _lon[i], _lat[i], 0 if _dist is None else _dist[i] ]))):
            removed_indices.append(i)
        else:
            lon.append(_lon[i])
            lat.append(_lat[i])
            if dist is not None:
                dist.append(_dist[i])

    removed_indices = np.unique(np.array(removed_indices))

    return lon, lat, dist, removed_indices

def print_attr_of_object_recursive(obj, depth = 2):
    if depth == 0:
        return

    print(f"type = {type(obj)}, obj =")
    for attrStr in dir(obj):
        if attrStr.startswith('__') or attrStr.count('byte')\
        or attrStr.count('string') or attrStr.count('dump'):
            continue

        attribute = getattr(obj, attrStr)
        print(f'{attrStr} = {attribute}')

        if callable(attribute):
            try:
                funcReturn = attribute()
                print('\t' + f'calling {attrStr} returns:')
                print_attr_of_object_recursive(funcReturn, depth - 1)
                continue
            except:
                continue

        if not isinstance(attribute, int) and not isinstance(attribute, float) and not isinstance(attribute, list)\
        and not isinstance(attribute, str) and not isinstance(attribute, dict) and not isinstance(attribute, set):
            print_attr_of_object_recursive(attribute, depth - 1)
