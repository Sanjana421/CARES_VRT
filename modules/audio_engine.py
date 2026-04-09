import threading

import numpy as np
import sounddevice as sd

from modules.calibration import scale_to_system_calibration


# Adjust these only if your MOTU device indices change
MOTU_HEADPHONES_OUT = 20
MOTU_SPEAKERS_OUT = 18
MOTU_INPUT_DEVICE = 22


class AudioEngine:
    def __init__(self, samplerate=44100, blocksize=512, output_mode="speakers"):
        self.samplerate = samplerate
        self.blocksize = blocksize

        if output_mode == "headphones":
            self.output_device = MOTU_HEADPHONES_OUT
        else:
            self.output_device = MOTU_SPEAKERS_OUT

        self.input_device = MOTU_INPUT_DEVICE

        self.noise_stream = None
        self.noise_idx = 0
        self.noise_buffer = None

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

    def start_continuous_noise(self, noise, target_spl_noise=None):
        """
        Start continuous noise playback on the output device.
        If target_spl_noise is provided, the noise is calibrated with the same
        SPL scaling method as the speech/distractor stimuli.
        """
        noise = np.asarray(noise, dtype=np.float32)

        if noise.ndim > 1:
            noise = noise.mean(axis=1)

        if target_spl_noise is not None:
            noise = scale_to_system_calibration(noise, target_spl_noise)

        self.noise_buffer = noise
        self.noise_idx = 0

        def callback(outdata, frames, time, status):
            if status:
                print("⚠️ Noise status:", status)

            if self.noise_buffer is None or len(self.noise_buffer) == 0:
                outdata.fill(0)
                return

            end = self.noise_idx + frames

            if end <= len(self.noise_buffer):
                chunk = self.noise_buffer[self.noise_idx:end]
            else:
                part1 = self.noise_buffer[self.noise_idx:]
                part2 = self.noise_buffer[: end - len(self.noise_buffer)]
                chunk = np.concatenate((part1, part2))

            self.noise_idx = end % len(self.noise_buffer)

            outdata[:] = np.column_stack((chunk, chunk))

        self.noise_stream = sd.OutputStream(
            samplerate=self.samplerate,
            channels=2,
            device=self.output_device,
            dtype="float32",
            latency="low",
            callback=callback,
        )

        self.noise_stream.start()
        print("🔊 Continuous noise started")

    def stop_noise(self):
        if self.noise_stream is not None:
            try:
                self.noise_stream.stop()
                self.noise_stream.close()
            finally:
                self.noise_stream = None
                self.noise_buffer = None
                self.noise_idx = 0
                print("🔇 Noise stopped")

    def start_trial_capture(self, stimulus):
        """
        Start stimulus playback and record from the input at the same time.
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
