import numpy as np

# Calibrated 4/17/25 by SG in C2022 at IU (DistVRTv5)
# Both speakers at Windows volume 44, MOTU Out 3-4: 82.0 dB SPL
SYSTEM_CAL_RMS = 0.4
SYSTEM_DB_SPL  = 82.0

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
