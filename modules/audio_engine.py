import threading

import numpy as np
import sounddevice as sd

from modules.calibration import scale_to_system_calibration


# in modules/audio_engine.py
OUTPUT_MODE = "speakers"
MOTU_OUTPUT_DEVICE = 18   # use your verified speakers output
MOTU_INPUT_DEVICE = 22    # use your verified mic input


class AudioEngine:
    def __init__(self, samplerate=44100, blocksize=512, output_mode="speakers"):
        self.samplerate = samplerate
        self.blocksize = blocksize
        self.output_device = MOTU_OUTPUT_DEVICE if output_mode == "speakers" else MOTU_OUTPUT_DEVICE
        self.input_device = MOTU_INPUT_DEVICE

        self.noise_buffer = None
        self.noise_idx = 0

        self._trial_thread = None
        self._trial_stop = threading.Event()
        self._trial_playback_done = threading.Event()
        self._recording_chunks = []
        self._trial_lock = threading.Lock()

    def play_test_tone(self, duration=1.0, freq=440):
        t = np.linspace(0, duration, int(self.samplerate * duration), endpoint=False)
        tone = 0.3 * np.sin(2 * np.pi * freq * t).astype(np.float32)

        stereo = np.column_stack((tone, tone))
        sd.play(
            stereo,
            samplerate=self.samplerate,
            device=self.output_device,
        )
        sd.wait()

    def set_continuous_noise(self, noise, target_spl_noise=None):
        """
        Store calibrated noise for mixing into the trial stream.
        No separate output stream is opened.
        """
        noise = np.asarray(noise, dtype=np.float32)

        if noise.ndim > 1:
            noise = noise.mean(axis=1)

        if target_spl_noise is not None:
            noise = scale_to_system_calibration(noise, target_spl_noise)

        self.noise_buffer = noise
        self.noise_idx = 0

    def stop_noise(self):
        """
        Keep compatibility with the rest of the app.
        Noise is no longer a separate stream.
        """
        self.noise_buffer = None
        self.noise_idx = 0

    def _get_noise_chunk(self, frames):
        if self.noise_buffer is None or len(self.noise_buffer) == 0:
            return np.zeros(frames, dtype=np.float32)

        end = self.noise_idx + frames

        if end <= len(self.noise_buffer):
            chunk = self.noise_buffer[self.noise_idx:end]
        else:
            part1 = self.noise_buffer[self.noise_idx:]
            part2 = self.noise_buffer[: end - len(self.noise_buffer)]
            chunk = np.concatenate((part1, part2))

        self.noise_idx = end % len(self.noise_buffer)
        return chunk.astype(np.float32)

    def start_trial_capture(self, stimulus):
        """
        Start stimulus playback and record from the input at the same time.
        The calibrated continuous noise is mixed into the same output stream.
        Returns an Event that is set when stimulus playback finishes.
        """
        stimulus = np.asarray(stimulus, dtype=np.float32)

        if stimulus.ndim == 1:
            stimulus = np.column_stack((stimulus, stimulus))

        with self._trial_lock:
            self._trial_stop.clear()
            self._trial_playback_done.clear()
            self._recording_chunks = []

            num_samples = stimulus.shape[0]
            idx = 0

            def callback(indata, outdata, frames, time, status):
                nonlocal idx

                if status:
                    print("⚠️ Audio status:", status)

                end = min(idx + frames, num_samples)
                n = end - idx

                outdata.fill(0)

                if n > 0:
                    outdata[:n, :] = stimulus[idx:end, :]

                if self.noise_buffer is not None and len(self.noise_buffer) > 0:
                    noise_chunk = self._get_noise_chunk(frames)
                    outdata[:] = outdata + np.column_stack((noise_chunk, noise_chunk))
                    outdata[:] = np.clip(outdata, -1.0, 1.0)

                self._recording_chunks.append(indata[:, 0].copy())

                idx = end

                if idx >= num_samples and not self._trial_playback_done.is_set():
                    self._trial_playback_done.set()

                if self._trial_stop.is_set():
                    raise sd.CallbackStop()

            def runner():
                try:
                    with sd.Stream(
                        samplerate=self.samplerate,
                        blocksize=self.blocksize,
                        device=(self.input_device, self.output_device),
                        channels=(2, 2),
                        dtype="float32",
                        latency="low",
                        callback=callback,
                    ):
                        while not self._trial_stop.is_set():
                            self._trial_stop.wait(0.05)
                except Exception as e:
                    print("❌ Trial stream error:", e)
                    self._trial_playback_done.set()

            self._trial_thread = threading.Thread(target=runner, daemon=True)
            self._trial_thread.start()

            return self._trial_playback_done

    def stop_trial_capture(self):
        """
        Stop the current trial recording and return the recorded mono input buffer.
        """
        with self._trial_lock:
            self._trial_stop.set()

            if self._trial_thread is not None:
                self._trial_thread.join(timeout=2.0)
                self._trial_thread = None

            if not self._recording_chunks:
                return np.empty(0, dtype=np.float32)

            return np.concatenate(self._recording_chunks).astype(np.float32)