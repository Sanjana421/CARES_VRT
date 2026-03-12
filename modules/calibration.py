import numpy as np

SYSTEM_CAL_RMS = 0.4
SYSTEM_DB_SPL = 80.75

def scale_to_system_calibration(x, target_spl):
    target_atten = target_spl - SYSTEM_DB_SPL

    xt_rms = np.sqrt(np.mean(x**2))
    if xt_rms == 0:
        return x

    x = x / xt_rms
    x = x * SYSTEM_CAL_RMS

    scale_factor = 10 ** (target_atten / 20)
    x = x * scale_factor

    return x