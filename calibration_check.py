# sounddevice:
# Used for audio playback through the selected hardware output device.
# Similar in purpose to sending audio to a specific sound card output in MATLAB.
import sounddevice as sd

# soundfile:
# Used to read audio files from disk.
# Similar to MATLAB's audio file reading functions.
import soundfile as sf

# numpy:
# Main numerical array library used for waveform math and channel mixing.
# Similar to MATLAB matrices and vector operations.
import numpy as np

# resample:
# Used to convert audio from its original sampling rate to the output sampling rate.
# This keeps playback timing consistent with the audio hardware.
from scipy.signal import resample

# Calibration reference for the system.
# SYSTEM_DB_SPL is the measured SPL corresponding to the reference RMS value.
SYSTEM_DB_SPL = 68.2
SYSTEM_RMS = 0.4


def scale_to_spl(x, target_spl):
    """
    Scale an audio signal to a desired SPL using the system calibration reference.

    Parameters
    ----------
    x : array-like
        Audio waveform.

    target_spl : float
        Desired sound pressure level in dB SPL.
    """
    # Compute RMS level of the waveform.
    rms = np.sqrt(np.mean(x**2))

    # Avoid divide-by-zero if the signal is silent.
    if rms == 0:
        return x

    # Normalize to unit RMS, then scale to the calibrated reference RMS.
    x = x / rms
    x = x * SYSTEM_RMS

    # Convert desired SPL difference into a linear gain factor.
    gain_db = target_spl - SYSTEM_DB_SPL
    gain = 10 ** (gain_db / 20)

    # Apply final gain to reach the desired SPL.
    return x * gain


# Output device index for playback.
# This should match the verified audio output device on the system.
device = 18

# Target SPL for playback.
target_spl = 65

# Read the chosen sound file from disk.
# The commented lines below show alternative stimulus files that can be tested.
audio, fs = sf.read(r"C:\Projects\DistVRT\DistVRTv4SF_DistShapedNoise.wav")
#audio, fs = sf.read(r"C:\Projects\DistVRT\DistVRTv4SF_AllStimShapedNoise.wav")
#audio, fs = sf.read(r"C:\Projects\DistVRT\DistVRTv4SF_NoiseShapedNoise.wav")
#audio, fs = sf.read(r"C:\Projects\DistVRT\DistVRTv4SF_WordsShapedNoise.wav")

# Print the original sampling rate of the file for verification.
print("file fs:", fs)

# Convert stereo input to mono by averaging channels if needed.
if audio.ndim > 1:
    audio = audio.mean(axis=1)

# Scale the waveform to the desired SPL using the calibration reference.
audio = scale_to_spl(audio, target_spl)

# Resample to the output device's expected sampling rate.
# This ensures playback timing matches the hardware configuration.
fs_out = 44100
if fs != fs_out:
    new_len = int(len(audio) * fs_out / fs)
    audio = resample(audio, new_len)
    fs = fs_out

# Duplicate mono audio into stereo for left/right playback.
# This creates a 2-channel signal for standard device output.
sd.play(np.column_stack([audio, audio]), samplerate=fs, device=device)

# Wait until playback completes before ending the script.
sd.wait()
