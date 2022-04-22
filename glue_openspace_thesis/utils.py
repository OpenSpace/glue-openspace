from astropy import units as u
from astropy.coordinates import SkyCoord
import time


__all__ = ['get_point_data', 'protocol_version', 'send_simp_message', 'WAIT_TIME']
# , 'get_luminosity_data', 'get_velocity_data'


protocol_version = '1.0'
WAIT_TIME = 0.01 # Time to wait after sending websocket message

def get_point_data(data, longitude_attribute, latitude_attribute, alternative_attribute=None,
                   frame=None, alternative_unit=None):

    x_coordinates = ""
    y_coordinates = ""
    z_coordinates = ""

    longitude = data[longitude_attribute]
    latitude = data[latitude_attribute]

    if alternative_attribute is None:
        # Get cartesian coordinates on unit galactic sphere
        coordinates = SkyCoord(longitude, latitude, unit='deg', frame=frame.lower())
        x, y, z = coordinates.galactic.cartesian.xyz

        # Convert to be on a sphere of radius 100pc
        radius = 100
        x *= radius
        y *= radius
        z *= radius

    else:
        distance = data[alternative_attribute]

        # Get cartesian coordinates on unit galactic sphere
        coordinates = SkyCoord(longitude * u.deg, latitude * u.deg,
                               distance=distance * u.Unit(alternative_unit),
                               frame=frame.lower())
        x, y, z = coordinates.galactic.cartesian.xyz

        x = x.to_value(u.pc)
        y = y.to_value(u.pc)
        z = z.to_value(u.pc)

    n_points = len(x)

    for i in range(n_points):
        x_coordinates += (str(x[i]) + ",")
        y_coordinates += (str(y[i]) + ",")
        z_coordinates += (str(z[i]) + ",")

    number_of_points = str(format(n_points, "09"))

    point_data_string = number_of_points + x_coordinates + y_coordinates + z_coordinates
    return point_data_string


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

def send_simp_message(socket, message_type, subject=''):
    time.sleep(WAIT_TIME)
    length_of_subject = str(format(len(subject), '09')) # formats to a 9-bit string
    message = protocol_version + message_type + length_of_subject + subject
    
    if len(message) > 115:
        print(f'Sending SIMP message \"{message[0:90]}...\"')
    else:
        print(f'Sending SIMP message \"{message}\"')
    
    
    # print(f'Sending SIMP message \"{message}\"')

    socket.send(bytes(message, 'utf-8'))
   
    # Wait for a short time to avoid sending too many messages in quick succession
    time.sleep(WAIT_TIME)