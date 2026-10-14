import numpy as np

# Current Python calibration reference from your document
# Both speakers at Windows volume 44, MOTU Out 3-4: 68.2 dB SPL
SYSTEM_CAL_RMS = 0.4
SYSTEM_DB_SPL = 73.3


def scale_to_system_calibration(x, target_spl):
    """
    Scale a signal to the calibrated system reference.

    target_spl is the desired SPL at the listener position after calibration.
    """
    x = np.asarray(x, dtype=np.float32)

    target_atten = target_spl - SYSTEM_DB_SPL

    xt_rms = np.sqrt(np.mean(x ** 2))
    if xt_rms == 0:
        return x

    x = x / xt_rms
    x = x * SYSTEM_CAL_RMS

    scale_factor = 10 ** (target_atten / 20)
    x = x * scale_factor

    return x.astype(np.float32)