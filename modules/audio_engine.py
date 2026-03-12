import sounddevice as sd
import numpy as np
import threading


# ── MOTU device output mode ───────────────────────────────────────────────────
OUTPUT_MODE = "speakers"   # "speakers" = Out 3-4  |  "headphones" = Out 1-2


def _find_motu_device(want_output: bool, prefer_name: str) -> int:
    """
    Find MOTU device by name rather than hard-coded index.
    Matches MATLAB behaviour: 'Device', 'MOTU M Series'.
    Falls back to known lab indices if device not found.
    """
    fallback = 6 if want_output else 1
    candidates = []

    for i, d in enumerate(sd.query_devices()):
        if prefer_name.lower() in d["name"].lower():
            if want_output and d["max_output_channels"] > 0:
                candidates.append(i)
            elif not want_output and d["max_input_channels"] > 0:
                candidates.append(i)

    if candidates:
        chosen = candidates[0]   # first match = DirectSound (matches MATLAB)
        label = "OUTPUT" if want_output else "INPUT"
        print(f"{label} Device Index: {chosen:2d}  →  {sd.query_devices(chosen)['name']}")
        return chosen

    print(f"⚠️  MOTU not found — using fallback index {fallback}")
    return fallback


def _get_devices():
    if OUTPUT_MODE == "headphones":
        out = _find_motu_device(want_output=True,  prefer_name="Out 1-2 (MOTU")
    else:
        out = _find_motu_device(want_output=True,  prefer_name="Out 3-4 (MOTU")
    inp = _find_motu_device(want_output=False, prefer_name="In 1-2 (MOTU")
    return inp, out


# Resolve at import time so any lookup errors surface immediately on startup
print(f"🔊 Routing audio to {'HEADPHONES (Out 1–2)' if OUTPUT_MODE == 'headphones' else 'SPEAKERS (Out 3–4)'}")
_INPUT_DEVICE, _OUTPUT_DEVICE = _get_devices()


class AudioEngine:

    def __init__(self, samplerate=44100, blocksize=512,
                 output_device=_OUTPUT_DEVICE,
                 input_device=_INPUT_DEVICE):
        self.samplerate    = samplerate
        self.blocksize     = blocksize
        self.output_device = output_device
        self.input_device  = input_device

    def play_and_record(self, stimulus):
        """
        Play 2-channel stimulus through MOTU Out 3-4 (or Out 1-2 for headphones)
        while simultaneously recording from MOTU In 1-2 channel 0.
        Blocks until playback is complete.
        """
        stimulus    = np.asarray(stimulus, dtype=np.float32)
        num_samples = stimulus.shape[0]
        recording   = np.zeros(num_samples, dtype=np.float32)
        idx         = 0
        done        = threading.Event()

        def callback(indata, outdata, frames, time, status):
            nonlocal idx
            end = min(idx + frames, num_samples)
            n   = end - idx

            outdata[:n]        = stimulus[idx:end]
            outdata[n:]        = 0.0
            recording[idx:end] = indata[:n, 0]   # record ch0 only
            idx = end

            if idx >= num_samples:
                done.set()
                raise sd.CallbackStop()

        with sd.Stream(
            samplerate = self.samplerate,
            blocksize  = self.blocksize,
            device     = (self.input_device, self.output_device),
            channels   = (2, 2),   # MOTU opens stereo pairs on both in/out
            dtype      = 'float32',
            callback   = callback
        ):
            done.wait()

        return recording
