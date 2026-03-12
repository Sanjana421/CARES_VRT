import sounddevice as sd
import numpy as np
import threading

TARGET_SAMPLERATE = 44100
TARGET_BLOCKSIZE  = 512


def find_motu_devices():
    devices = sd.query_devices()
    input_dev  = None
    output_dev = None

    for idx, dev in enumerate(devices):
        if "MOTU" in dev["name"]:
            if dev["max_input_channels"] > 0 and input_dev is None:
                input_dev = idx
            if dev["max_output_channels"] > 0 and output_dev is None:
                output_dev = idx

    if input_dev is None or output_dev is None:
        raise RuntimeError("MOTU device not found.")

    return input_dev, output_dev


class AudioEngine:

    def __init__(self,
                 output_mode="speakers",   # "speakers" or "headphones"
                 samplerate=TARGET_SAMPLERATE,
                 blocksize=TARGET_BLOCKSIZE):

        self.samplerate = samplerate
        self.blocksize  = blocksize
        self.output_mode = output_mode.lower()

        self.input_device, self.output_device = find_motu_devices()

        # 🎧 HEADPHONES = Out 1–2
        # 🔊 SPEAKERS   = Out 3–4
        if self.output_mode == "headphones":
            self.output_mapping = [0, 1]
            print("🎧 Routing audio to HEADPHONES (Out 1–2)")
        else:
            self.output_mapping = [2, 3]
            print("🔊 Routing audio to SPEAKERS (Out 3–4)")

        print(f"Input Device Index:  {self.input_device}")
        print(f"Output Device Index: {self.output_device}")
        print()

    def play_and_record(self, stimulus):

        stimulus = np.asarray(stimulus, dtype=np.float32)

        if stimulus.ndim != 2 or stimulus.shape[1] != 2:
            raise ValueError("Stimulus must be stereo (N x 2).")

        total_samples = stimulus.shape[0]
        recording     = np.zeros(total_samples, dtype=np.float32)

        idx  = 0
        done = threading.Event()

        def callback(indata, outdata, frames, time, status):
            nonlocal idx

            if status:
                print(status)

            end = min(idx + frames, total_samples)
            n   = end - idx

            outdata[:n] = stimulus[idx:end]
            outdata[n:] = 0.0

            # record from In 1 (channel 0)
            recording[idx:end] = indata[:n, 0]

            idx = end

            if idx >= total_samples:
                done.set()
                raise sd.CallbackStop()

        with sd.Stream(
            samplerate=self.samplerate,
            blocksize=self.blocksize,
            dtype="float32",
            device=(self.input_device, self.output_device),
            channels=(1, 2),
            input_mapping=[0],               # In 1
            output_mapping=self.output_mapping,  # depends on mode
            callback=callback
        ):
            done.wait()

        return recording
