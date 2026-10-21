"""scale2SysCalSF.m logic (as MATLAB), with the calibration VALUES kept from the GitHub version."""
import numpy as np

# Values: unchanged from the GitHub version
SYSTEM_CAL_RMS = 0.4
SYSTEM_DB_SPL = 73.3          # both speakers, Windows volume 44, MOTU Out 3-4


def scale_to_system_calibration(x, target_spl):
    """scale2SysCalSF.m: RMS -> 1, -> systemCalRMS, then attenuate to the target SPL.
    For a 2-column signal the RMS is taken per column, as MATLAB's rms() does."""
    x = np.asarray(x, dtype=np.float64)
    rms = np.sqrt(np.mean(x ** 2, axis=0))
    rms = np.where(rms == 0, 1.0, rms)
    x = x / rms * SYSTEM_CAL_RMS
    x = x * 10 ** ((target_spl - SYSTEM_DB_SPL) / 20)
    return x.astype(np.float32)
