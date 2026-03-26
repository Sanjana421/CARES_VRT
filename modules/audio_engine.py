import sounddevice as sd
import numpy as np
import threading


class AudioEngine:

    def __init__(self, samplerate=44100, blocksize=512,
                 output_mode="speakers"):

        self.samplerate = samplerate
        self.blocksize  = blocksize

        # 🔊 Device selection
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

    # ─────────────────────────────────────────────────────────────
    # 🔊 TEST AUDIO
    # ─────────────────────────────────────────────────────────────
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

    # ─────────────────────────────────────────────────────────────
    # 🔊 CONTINUOUS BACKGROUND NOISE
    # ─────────────────────────────────────────────────────────────
    def start_continuous_noise(self, noise):

        noise = np.asarray(noise, dtype=np.float32)

        # 🔥 force mono → stereo later
        if noise.ndim > 1:
            noise = noise.mean(axis=1)

        self.noise_idx = 0

        def callback(outdata, frames, time, status):
            if status:
                print("⚠️ Noise status:", status)

            end = self.noise_idx + frames

            if end < len(noise):
                chunk = noise[self.noise_idx:end]
            else:
                part1 = noise[self.noise_idx:]
                part2 = noise[:end - len(noise)]
                chunk = np.concatenate((part1, part2))

            self.noise_idx = end % len(noise)

            # 🔥 scale noise here (IMPORTANT for balance)
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

    # ─────────────────────────────────────────────────────────────
    # 🎧 MAIN PLAYBACK + RECORDING
    # ─────────────────────────────────────────────────────────────
    def play_and_record(self, stimulus):

        stimulus = np.asarray(stimulus, dtype=np.float32)

        # 🔥 Ensure stereo
        if stimulus.ndim == 1:
            stimulus = np.column_stack((stimulus, stimulus))

        num_samples = stimulus.shape[0]
        recording   = np.zeros(num_samples, dtype=np.float32)

        idx  = 0
        done = threading.Event()

        def callback(indata, outdata, frames, time, status):
            nonlocal idx

            if status:
                print("⚠️ Audio status:", status)

            end = min(idx + frames, num_samples)
            n   = end - idx

            outdata.fill(0)

            if n > 0:
                outdata[:n, :] = stimulus[idx:end, :]

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
            latency='low',
            callback=callback
        ):
            done.wait()

        return recording
