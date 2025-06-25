"""
Compatibility layer for audioop module (removed in Python 3.13)
This provides basic functionality needed by the AudioSocket server.
"""

import struct

import numpy as np


def ulaw2lin(data, width):
    """Convert u-law encoded data to linear PCM"""
    if width != 2:
        raise ValueError("Only 16-bit audio supported")

    # u-law decoding table
    ulaw_table = [
        -32124,
        -31100,
        -30076,
        -29052,
        -28028,
        -27004,
        -25980,
        -24956,
        -23932,
        -22908,
        -21884,
        -20860,
        -19836,
        -18812,
        -17788,
        -16764,
        -15996,
        -15484,
        -14972,
        -14460,
        -13948,
        -13436,
        -12924,
        -12412,
        -11900,
        -11388,
        -10876,
        -10364,
        -9852,
        -9340,
        -8828,
        -8316,
        -7932,
        -7676,
        -7420,
        -7164,
        -6908,
        -6652,
        -6396,
        -6140,
        -5884,
        -5628,
        -5372,
        -5116,
        -4860,
        -4604,
        -4348,
        -4092,
        -3900,
        -3772,
        -3644,
        -3516,
        -3388,
        -3260,
        -3132,
        -3004,
        -2876,
        -2748,
        -2620,
        -2492,
        -2364,
        -2236,
        -2108,
        -1980,
        -1884,
        -1820,
        -1756,
        -1692,
        -1628,
        -1564,
        -1500,
        -1436,
        -1372,
        -1308,
        -1244,
        -1180,
        -1116,
        -1052,
        -988,
        -924,
        -876,
        -844,
        -812,
        -780,
        -748,
        -716,
        -684,
        -652,
        -620,
        -588,
        -556,
        -524,
        -492,
        -460,
        -428,
        -396,
        -372,
        -356,
        -340,
        -324,
        -308,
        -292,
        -276,
        -260,
        -244,
        -228,
        -212,
        -196,
        -180,
        -164,
        -148,
        -132,
        -120,
        -112,
        -104,
        -96,
        -88,
        -80,
        -72,
        -64,
        -56,
        -48,
        -40,
        -32,
        -24,
        -16,
        -8,
        0,
        32124,
        31100,
        30076,
        29052,
        28028,
        27004,
        25980,
        24956,
        23932,
        22908,
        21884,
        20860,
        19836,
        18812,
        17788,
        16764,
        15996,
        15484,
        14972,
        14460,
        13948,
        13436,
        12924,
        12412,
        11900,
        11388,
        10876,
        10364,
        9852,
        9340,
        8828,
        8316,
        7932,
        7676,
        7420,
        7164,
        6908,
        6652,
        6396,
        6140,
        5884,
        5628,
        5372,
        5116,
        4860,
        4604,
        4348,
        4092,
        3900,
        3772,
        3644,
        3516,
        3388,
        3260,
        3132,
        3004,
        2876,
        2748,
        2620,
        2492,
        2364,
        2236,
        2108,
        1980,
        1884,
        1820,
        1756,
        1692,
        1628,
        1564,
        1500,
        1436,
        1372,
        1308,
        1244,
        1180,
        1116,
        1052,
        988,
        924,
        876,
        844,
        812,
        780,
        748,
        716,
        684,
        652,
        620,
        588,
        556,
        524,
        492,
        460,
        428,
        396,
        372,
        356,
        340,
        324,
        308,
        292,
        276,
        260,
        244,
        228,
        212,
        196,
        180,
        164,
        148,
        132,
        120,
        112,
        104,
        96,
        88,
        80,
        72,
        64,
        56,
        48,
        40,
        32,
        24,
        16,
        8,
        0,
    ]

    # Convert bytes to list of u-law values
    ulaw_values = list(data)

    # Convert each u-law value to linear PCM
    linear_values = []
    for ulaw_val in ulaw_values:
        if ulaw_val < 128:
            linear_val = ulaw_table[ulaw_val]
        else:
            linear_val = ulaw_table[ulaw_val - 128]
        linear_values.append(linear_val)

    # Convert to bytes
    return struct.pack(f"<{len(linear_values)}h", *linear_values)


def ratecv(data, width, nchannels, inrate, outrate, state=None):
    """Resample audio data"""
    if width != 2:
        raise ValueError("Only 16-bit audio supported")

    # Convert bytes to numpy array
    samples = np.frombuffer(data, dtype=np.int16)

    # Simple resampling using numpy
    if inrate == outrate:
        return data, state

    # Calculate resampling ratio
    ratio = outrate / inrate
    new_length = int(len(samples) * ratio)

    # Simple linear interpolation
    indices = np.linspace(0, len(samples) - 1, new_length)
    resampled = np.interp(indices, np.arange(len(samples)), samples)

    # Convert back to bytes
    return resampled.astype(np.int16).tobytes(), state


def tostereo(data, width, nchannels, leftweight, rightweight):
    """Convert mono to stereo"""
    if width != 2:
        raise ValueError("Only 16-bit audio supported")
    if nchannels != 1:
        raise ValueError("Input must be mono")

    # Convert bytes to numpy array
    samples = np.frombuffer(data, dtype=np.int16)

    # Create stereo channels
    left_channel = samples * leftweight
    right_channel = samples * rightweight

    # Interleave channels
    stereo = np.empty(len(samples) * 2, dtype=np.int16)
    stereo[0::2] = left_channel
    stereo[1::2] = right_channel

    return stereo.tobytes()


def tomono(data, width, nchannels, leftweight, rightweight):
    """Convert stereo to mono"""
    if width != 2:
        raise ValueError("Only 16-bit audio supported")
    if nchannels != 2:
        raise ValueError("Input must be stereo")

    # Convert bytes to numpy array
    samples = np.frombuffer(data, dtype=np.int16)

    # Separate channels
    left_channel = samples[0::2]
    right_channel = samples[1::2]

    # Mix channels
    mono = left_channel * leftweight + right_channel * rightweight

    return mono.astype(np.int16).tobytes()
