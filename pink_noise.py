import numpy as np
import sounddevice as sd
from scipy.signal import lfilter

# Match the MATLAB calibration setup
FS = 44100
DURATION_SEC = 500
DB_ATTEN = -7.9588          # same as MATLAB script
TARGET_RMS = 0.4            # same as MATLAB comment
OUTPUT_DEVICE = 18          # Out 3-4 (speakers)
# OUTPUT_DEVICE = 20        # Out 1-2 (headphones)

def pink_noise(num_samples: int, seed: int | None = None) -> np.ndarray:
    """
    Pink noise approximation using a standard IIR pinking filter.
    Good for calibration checks and much closer to MATLAB 'Pink Noise' than white noise.
    """
    rng = np.random.default_rng(seed)
    white = rng.standard_normal(num_samples).astype(np.float64)

    # Paul Kellet pink noise filter
    b = np.array([0.049922035, 0.095993537, 0.050612699, 0.004408786], dtype=np.float64)
    a = np.array([1.0, -2.494956002, 2.017265875, -0.522189400], dtype=np.float64)

    pink = lfilter(b, a, white)
    pink -= np.mean(pink)
    return pink

def main():
    n = int(FS * DURATION_SEC)

    # 1) Generate pink noise
    wav = pink_noise(n)

    # 2) Rescale to RMS = 1 (same idea as MATLAB's wavTemp./rms(wavTemp))
    rms = np.sqrt(np.mean(wav ** 2))
    if rms == 0:
        raise RuntimeError("Generated noise has zero RMS.")
    wav = wav / rms

    # 3) Apply attenuation so final RMS matches the calibration target
    scale_factor = 10 ** (DB_ATTEN / 20.0)
    wav = wav * scale_factor

    # Sanity check
    print(f"RMS after scaling: {np.sqrt(np.mean(wav ** 2)):.6f}")
    print(f"Peak after scaling: {np.max(np.abs(wav)):.6f}")

    # 4) Duplicate to stereo, same as MATLAB repmat(wav,1,2)
    stereo = np.column_stack((wav, wav)).astype(np.float32)

    # 5) Play through the MOTU output
    sd.play(stereo, samplerate=FS, device=OUTPUT_DEVICE)
    sd.wait()

if __name__ == "__main__":
    main()