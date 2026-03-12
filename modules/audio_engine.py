import sounddevice as sd
import numpy as np
import threading


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
        """
        Play a 2-channel stimulus through MOTU Out 3-4 while simultaneously
        recording from MOTU In 1-2 channel 1.

        Matches MATLAB behaviour:
          - Plays in 512-sample batches (stimBatchLen = 512)
          - Blocks until the entire stimulus has played
          - Returns the mono recording as a numpy array
        """

        stimulus = np.asarray(stimulus, dtype=np.float32)

        # Ensure stimulus is 2-channel (samples x 2)
        if stimulus.ndim == 1:
            stimulus = np.column_stack((stimulus, stimulus))

        num_samples = stimulus.shape[0]

        # Pad to exact multiple of blocksize (matches MATLAB's trailing-zero logic)
        remainder = num_samples % self.blocksize
        if remainder != 0:
            pad = self.blocksize - remainder
            stimulus = np.vstack(
                (stimulus, np.zeros((pad, 2), dtype=np.float32))
            )
            padded_samples = stimulus.shape[0]
        else:
            padded_samples = num_samples

        recording = np.zeros((padded_samples, 1), dtype=np.float32)
        idx       = 0
        done_event = threading.Event()

        def callback(indata, outdata, frames, time, status):
            nonlocal idx

            end = idx + frames

            if end >= padded_samples:
                # Last batch — fill remainder and stop
                remaining = padded_samples - idx
                outdata[:remaining] = stimulus[idx:idx + remaining]
                outdata[remaining:]  = 0
                recording[idx:idx + remaining] = indata[:remaining, 0:1]
                idx = padded_samples
                done_event.set()
                raise sd.CallbackStop()
            else:
                outdata[:] = stimulus[idx:end]
                recording[idx:end] = indata[:, 0:1]
                idx = end

        with sd.Stream(
            samplerate  = self.samplerate,
            blocksize   = self.blocksize,
            device      = (self.input_device, self.output_device),
            channels    = (2, 2),   # MOTU opens stereo pairs on both in/out
            dtype       = 'float32',
            callback    = callback
        ):
            # Block here until the callback signals completion
            done_event.wait()

        # Return only the original (unpadded) samples, mono
        return recording[:num_samples, 0]