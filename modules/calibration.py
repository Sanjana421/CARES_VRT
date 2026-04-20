import numpy as np

# System calibration reference
# Measurement conditions:
# - Both speakers active
# - Windows system volume set to 44
# - MOTU outputs 3–4 used
# - Measured level at listener position: 68.2 dB SPL
#
# SYSTEM_CAL_RMS:
# RMS value of the digital signal that produced the calibrated SPL.
# This serves as the reference amplitude for scaling.
SYSTEM_CAL_RMS = 0.4

# SYSTEM_DB_SPL:
# Sound pressure level (in dB SPL) corresponding to SYSTEM_CAL_RMS
# under the calibration conditions above.
SYSTEM_DB_SPL = 68.2


def scale_to_system_calibration(x, target_spl):
    """
    Scale an input signal to a desired sound pressure level (SPL)
    based on the system calibration reference.

    Parameters
    ----------
    x : array-like
        Input audio signal.

    target_spl : float
        Desired output level in dB SPL at the listener position.

    Returns
    -------
    np.ndarray
        Scaled signal expected to produce the target SPL when played
        under the same calibration conditions.

    Assumptions
    -----------
    - Playback hardware and volume settings match calibration.
    - Linear relationship between digital amplitude and SPL.
    """

    # Convert input to float32 for consistent audio processing
    x = np.asarray(x, dtype=np.float32)

    # Difference between desired SPL and calibrated reference SPL
    # (positive = increase level, negative = decrease level)
    target_atten = target_spl - SYSTEM_DB_SPL

    # Compute RMS of input signal
    xt_rms = np.sqrt(np.mean(x ** 2))

    # Avoid division by zero for silent input
    if xt_rms == 0:
        return x

    # Normalize signal to unit RMS
    x = x / xt_rms

    # Scale to calibrated RMS reference
    x = x * SYSTEM_CAL_RMS

    # Convert SPL difference (dB) to linear amplitude scale factor
    scale_factor = 10 ** (target_atten / 20)

    # Apply final scaling to reach target SPL
    x = x * scale_factor

    return x.astype(np.float32)
