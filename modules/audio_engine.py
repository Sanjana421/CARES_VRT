import sounddevice as sd
import numpy as np
import threading

# ── MOTU M Series device indices ─────────────────────────────────────────────
# Verify with:
#   python -c "import sounddevice as sd; [print(i,d['name']) for i,d in enumerate(sd.query_devices())]"
OUTPUT_MODE        = "speakers"   # "speakers" = Out 3-4 | "headphones" = Out 1-2
MOTU_OUTPUT_DEVICE = 8 if OUTPUT_MODE == "headphones" else 6
MOTU_INPUT_DEVICE  = 1


class AudioEngine:

    def __init__(self, samplerate=44100, blocksize=512,
                 output_device=MOTU_OUTPUT_DEVICE,
                 input_device=MOTU_INPUT_DEVICE):
        self.samplerate    = samplerate
        self.blocksize     = blocksize
        self.output_device = output_device
        self.input_device  = input_device

    def play_and_record(self, stimulus):
        """
        Play 2-channel stimulus through MOTU Out 3-4 while recording from
        MOTU In 1-2 channel 0.  Blocks until playback is complete.
        Matches MATLAB audioPlayerRecorder batch playback exactly.
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
            channels   = (2, 2),   # MOTU always opens stereo pairs
            dtype      = 'float32',
            callback   = callback
        ):
            done.wait()   # block until all samples played

        return recording