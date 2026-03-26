import sounddevice as sd
import numpy as np
import threading


class AudioEngine:

    def __init__(self, samplerate=44100, blocksize=512,
                 output_mode="speakers"):

        self.samplerate = samplerate
        self.blocksize  = blocksize

        
        if output_mode == "headphones":
            self.output_device = 20   # Out 1-2
            print("🎧 Output → HEADPHONES (Out 1–2)")
        else:
            self.output_device = 18   # Out 3-4
            print("🔊 Output → SPEAKERS (Out 3–4)")

        self.input_device = 22        # In 1-2

        print(f"INPUT  DEVICE: {self.input_device} → {sd.query_devices(self.input_device)['name']}")
        print(f"OUTPUT DEVICE: {self.output_device} → {sd.query_devices(self.output_device)['name']}")

    def play_and_record(self, stimulus):

        stimulus    = np.asarray(stimulus, dtype=np.float32)
        num_samples = stimulus.shape[0]
        recording   = np.zeros(num_samples, dtype=np.float32)
        idx         = 0
        done        = threading.Event()

        def callback(indata, outdata, frames, time, status):
            nonlocal idx

            end = min(idx + frames, num_samples)
            n   = end - idx

            outdata[:n, :] = stimulus[idx:end, :]
            outdata[n:, :] = 0.0

            recording[idx:end] = indata[:n, 0]
            idx = end

            if idx >= num_samples:
                done.set()
                raise sd.CallbackStop()

        with sd.Stream(
            samplerate=self.samplerate,
            blocksize=self.blocksize,
            device=(self.input_device, self.output_device),
            channels=(2, 2),
            dtype='float32',
            callback=callback
        ):
            done.wait()

        return recording
