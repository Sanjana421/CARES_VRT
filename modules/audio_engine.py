import sounddevice as sd
import numpy as np
import threading


class AudioEngine:
    def __init__(self, samplerate=44100, blocksize=512, output_mode="speakers"):
        self.samplerate = samplerate
        self.blocksize = blocksize

        if output_mode == "headphones":
            self.output_device = 20   # Out 1-2
            print("🎧 Output → HEADPHONES (Out 1–2)")
        else:
            self.output_device = 18   # Out 3-4
            print("🔊 Output → SPEAKERS (Out 3–4)")

        self.input_device = 22        # In 1-2

        print(f"INPUT  DEVICE: {self.input_device} → {sd.query_devices(self.input_device)['name']}")
        print(f"OUTPUT DEVICE: {self.output_device} → {sd.query_devices(self.output_device)['name']}")

        self.noise_stream = None
        self.noise_idx = 0

        self._trial_thread = None
        self._trial_stop = threading.Event()
        self._trial_playback_done = threading.Event()
        self._recording_chunks = []
        self._trial_lock = threading.Lock()

    def play_test_tone(self, duration=1.0, freq=440):
        print("🔊 Playing test tone...")

        t = np.linspace(0, duration, int(self.samplerate * duration), endpoint=False)
        tone = 0.3 * np.sin(2 * np.pi * freq * t)

        sd.play(
            np.column_stack((tone, tone)),
            samplerate=self.samplerate,
            device=self.output_device
        )
        sd.wait()

        print("✅ Test tone finished")

    def start_continuous_noise(self, noise):
        noise = np.asarray(noise, dtype=np.float32)

        if noise.ndim > 1:
            noise = noise.mean(axis=1)

        self.noise_idx = 0

        def callback(outdata, frames, time, status):
            if status:
                print("⚠️ Noise status:", status)

            end = self.noise_idx + frames

            if end <= len(noise):
                chunk = noise[self.noise_idx:end]
            else:
                part1 = noise[self.noise_idx:]
                part2 = noise[:end - len(noise)]
                chunk = np.concatenate((part1, part2))

            self.noise_idx = end % len(noise)

            chunk = 0.3 * chunk
            outdata[:] = np.column_stack((chunk, chunk))

        self.noise_stream = sd.OutputStream(
            samplerate=self.samplerate,
            channels=2,
            device=self.output_device,
            dtype='float32',
            latency='low',
            callback=callback
        )

        self.noise_stream.start()
        print("🔊 Continuous noise started")

    def stop_noise(self):
        if self.noise_stream is not None:
            self.noise_stream.stop()
            self.noise_stream.close()
            self.noise_stream = None
            print("🔇 Noise stopped")

    def start_trial_capture(self, stimulus):
        """
        Start stimulus playback and begin recording input immediately.
        Recording continues until stop_trial_capture() is called.
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

                # keep recording the mic while playback runs
                self._recording_chunks.append(indata[:, 0].copy())

                idx = end

                if idx >= num_samples and not self._trial_playback_done.is_set():
                    self._trial_playback_done.set()

                if self._trial_stop.is_set():
                    raise sd.CallbackStop()

            def runner():
                with sd.Stream(
                    samplerate=self.samplerate,
                    blocksize=self.blocksize,
                    device=(self.input_device, self.output_device),
                    channels=(2, 2),
                    dtype='float32',
                    latency='low',
                    callback=callback
                ):
                    while not self._trial_stop.is_set():
                        self._trial_stop.wait(0.05)

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
