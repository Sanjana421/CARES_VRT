import sounddevice as sd
import soundfile as sf
import numpy as np
from scipy.signal import resample

SYSTEM_DB_SPL = 68.2
SYSTEM_RMS = 0.4

def scale_to_spl(x, target_spl):
    rms = np.sqrt(np.mean(x**2))
    if rms == 0:
        return x
    x = x / rms
    x = x * SYSTEM_RMS
    gain_db = target_spl - SYSTEM_DB_SPL
    gain = 10 ** (gain_db / 20)
    return x * gain

device = 18
target_spl = 65

audio, fs = sf.read(r"C:\Projects\DistVRT\DistVRTv4SF_DistShapedNoise.wav")
#audio, fs = sf.read(r"C:\Projects\DistVRT\DistVRTv4SF_AllStimShapedNoise.wav")
#audio, fs = sf.read(r"C:\Projects\DistVRT\DistVRTv4SF_NoiseShapedNoise.wav")
#audio, fs = sf.read(r"C:\Projects\DistVRT\DistVRTv4SF_WordsShapedNoise.wav")
print("file fs:", fs)

if audio.ndim > 1:
    audio = audio.mean(axis=1)

audio = scale_to_spl(audio, target_spl)

# resample to the device rate
fs_out = 44100
if fs != fs_out:
    new_len = int(len(audio) * fs_out / fs)
    audio = resample(audio, new_len)
    fs = fs_out

sd.play(np.column_stack([audio, audio]), samplerate=fs, device=device)
sd.wait()