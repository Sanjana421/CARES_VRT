import sounddevice as sd
import numpy as np


class AudioEngine:

    def __init__(self, samplerate=44100, blocksize=512):
        self.samplerate = samplerate
        self.blocksize = blocksize

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
            channels=(2, 1),
            dtype='float32',
            callback=callback
        ) as stream:
            while stream.active:
                sd.sleep(10)

        return recording