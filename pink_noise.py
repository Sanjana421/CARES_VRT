# numpy:
# Main numerical array library used for waveform generation and scaling.
# Similar to MATLAB matrices and vectorized operations.
import numpy as np

# sounddevice:
# Used for direct audio playback through the selected output device.
# Comparable to sending audio to a sound card output in MATLAB.
import sounddevice as sd

# lfilter:
# Applies the IIR filter used here to approximate pink noise.
# Similar to running a digital filter on a signal in MATLAB.
from scipy.signal import lfilter

# Match the MATLAB calibration setup.
# These constants define the same playback conditions used in the MATLAB script.
FS = 44100
DURATION_SEC = 500
DB_ATTEN = -7.9588          # same as MATLAB script
TARGET_RMS = 0.4            # same as MATLAB comment
OUTPUT_DEVICE = 18          # Out 3-4 (speakers)
# OUTPUT_DEVICE = 20        # Out 1-2 (headphones)


def pink_noise(num_samples: int, seed: int | None = None) -> np.ndarray:
    """
    Generate an approximation of pink noise using an IIR pinking filter.

    This produces a spectrum closer to standard calibration pink noise than
    white noise, and is suitable for playback checks and system calibration.
    """
    # Create a random number generator so the output can be reproduced if needed.
    rng = np.random.default_rng(seed)

    # Generate white noise as the starting signal.
    # This is the raw random sequence that will be filtered into pink noise.
    white = rng.standard_normal(num_samples).astype(np.float64)

    # Paul Kellet pink noise filter coefficients.
    # The filter shapes the white noise spectrum so power decreases with frequency.
    b = np.array([0.049922035, 0.095993537, 0.050612699, 0.004408786], dtype=np.float64)
    a = np.array([1.0, -2.494956002, 2.017265875, -0.522189400], dtype=np.float64)

    # Apply the filter to generate pink noise.
    pink = lfilter(b, a, white)

    # Remove any DC offset introduced by filtering.
    pink -= np.mean(pink)
    return pink


def main():
    # Total number of samples to generate for the playback duration.
    n = int(FS * DURATION_SEC)

    # 1) Generate pink noise.
    wav = pink_noise(n)

    # 2) Normalize the waveform to RMS = 1.
    # This matches the MATLAB step wavTemp./rms(wavTemp).
    rms = np.sqrt(np.mean(wav ** 2))
    if rms == 0:
        raise RuntimeError("Generated noise has zero RMS.")
    wav = wav / rms

    # 3) Apply attenuation so the final signal matches the calibration target.
    # Convert the dB adjustment into a linear amplitude factor.
    scale_factor = 10 ** (DB_ATTEN / 20.0)
    wav = wav * scale_factor

    # Sanity checks help verify that the scaling is behaving as expected.
    print(f"RMS after scaling: {np.sqrt(np.mean(wav ** 2)):.6f}")
    print(f"Peak after scaling: {np.max(np.abs(wav)):.6f}")

    # 4) Duplicate mono noise to stereo.
    # Equivalent to repmat(wav, 1, 2) in MATLAB.
    stereo = np.column_stack((wav, wav)).astype(np.float32)

    # 5) Play the noise through the selected MOTU output device.
    sd.play(stereo, samplerate=FS, device=OUTPUT_DEVICE)
    sd.wait()


# Standard Python entry point.
if __name__ == "__main__":
    main()
