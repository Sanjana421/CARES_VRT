import sounddevice as sd
import numpy as np

# MOTU multiple output channels testing
# Run: python -c "import sounddevice as sd; [print(i, d['name']) for i, d in enumerate(sd.query_devices())]" - to verify these on any new machine.
OUTPUT_MODE = "speakers"   # change to "headphones" for amplifier

MOTU_OUTPUT_DEVICE = 8 if OUTPUT_MODE == "headphones" else 6   # Out 3-4 (MOTU M Series)  → channels 3 & 4 → amplifier → speaker
MOTU_INPUT_DEVICE  = 1   # In 1-2 (MOTU M Series)   → channel 1 → microphone recording


class AudioEngine:

    def __init__(self, samplerate=44100, blocksize=512,
                 output_device=MOTU_OUTPUT_DEVICE,
                 input_device=MOTU_INPUT_DEVICE):
        self.samplerate    = samplerate
        self.blocksize     = blocksize
        self.output_device = output_device
        self.input_device  = input_device

    def play_and_record(self, stimulus):

        stimulus = stimulus.astype(np.float32)
        num_samples = stimulus.shape[0]
        recording = np.zeros((num_samples, 1), dtype=np.float32)
        idx = 0

        def callback(outdata, indata, frames, time, status):
            nonlocal idx

            end = idx + frames

            if end > num_samples:
                remaining = num_samples - idx
                outdata[:remaining] = stimulus[idx:idx+remaining]
                outdata[remaining:] = 0
                recording[idx:idx+remaining] = indata[:remaining, 0:1]
                raise sd.CallbackStop()
            else:
                outdata[:] = stimulus[idx:end]
                recording[idx:end] = indata[:, 0:1]
                idx = end

        with sd.Stream(
            samplerate=self.samplerate,
            blocksize=self.blocksize,
            device=(self.input_device, self.output_device),
            channels=(1, 2),        # 1 input channel (mic), 2 output channels (word + dist)
            dtype='float32',
            callback=callback
        ) as stream:
            while stream.active:
                sd.sleep(10)

        return recording