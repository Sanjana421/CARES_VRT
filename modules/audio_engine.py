import threading

import numpy as np
import sounddevice as sd

from modules.calibration import scale_to_system_calibration


# Default output mode for playback
OUTPUT_MODE = "speakers"

# Hardware device indices (must match verified system configuration)
# These should be updated if the audio interface configuration changes.
MOTU_OUTPUT_DEVICE = 18   # speaker output (verified)
MOTU_INPUT_DEVICE = 22    # microphone input (verified)


class AudioEngine:
    def __init__(self, samplerate=44100, blocksize=512, output_mode="speakers"):
        # Sampling rate for playback and recording (Hz)
        self.samplerate = samplerate

        # Number of frames processed per callback
        # Lower values reduce latency but increase CPU load
        self.blocksize = blocksize

        # Output device selection (currently only one configured)
        self.output_device = MOTU_OUTPUT_DEVICE if output_mode == "speakers" else MOTU_OUTPUT_DEVICE

        # Input device (microphone or acquisition channel)
        self.input_device = MOTU_INPUT_DEVICE

        # Buffer storing continuous background noise (mono)
        # This is mixed into the output stream during trials
        self.noise_buffer = None

        # Index used to loop through the noise buffer
        self.noise_idx = 0

        # Thread handling playback + recording stream
        self._trial_thread = None

        # Event used to signal stream termination
        self._trial_stop = threading.Event()

        # Event set when stimulus playback has completed
        self._trial_playback_done = threading.Event()

        # List of recorded input chunks (collected per callback)
        self._recording_chunks = []

        # Lock to prevent concurrent trial execution
        self._trial_lock = threading.Lock()

    def play_test_tone(self, duration=1.0, freq=440):
        # Generate time vector
        t = np.linspace(0, duration, int(self.samplerate * duration), endpoint=False)

        # Generate sine wave (low amplitude to avoid clipping)
        tone = 0.3 * np.sin(2 * np.pi * freq * t).astype(np.float32)

        # Convert mono signal to stereo
        stereo = np.column_stack((tone, tone))

        # Play tone through output device
        sd.play(
            stereo,
            samplerate=self.samplerate,
            device=self.output_device,
        )

        # Wait until playback finishes
        sd.wait()

    def set_continuous_noise(self, noise, target_spl_noise=None):
        """
        Store noise buffer for continuous playback during trials.

        Parameters
        ----------
        noise : array-like
            Noise signal (mono or multi-channel).

        target_spl_noise : float, optional
            Desired SPL for the noise signal after calibration.
        """
        # Ensure float32 format
        noise = np.asarray(noise, dtype=np.float32)

        # Convert to mono if needed
        if noise.ndim > 1:
            noise = noise.mean(axis=1)

        # Apply SPL calibration if specified
        if target_spl_noise is not None:
            noise = scale_to_system_calibration(noise, target_spl_noise)

        # Store buffer and reset playback index
        self.noise_buffer = noise
        self.noise_idx = 0

    def stop_noise(self):
        """
        Disable background noise playback.
        """
        self.noise_buffer = None
        self.noise_idx = 0

    def _get_noise_chunk(self, frames):
        """
        Retrieve a chunk of noise for mixing into the output stream.
        Implements circular buffering for continuous playback.
        """
        if self.noise_buffer is None or len(self.noise_buffer) == 0:
            return np.zeros(frames, dtype=np.float32)

        end = self.noise_idx + frames

        # If within bounds, take contiguous slice
        if end <= len(self.noise_buffer):
            chunk = self.noise_buffer[self.noise_idx:end]
        else:
            # Wrap around buffer end to maintain continuity
            part1 = self.noise_buffer[self.noise_idx:]
            part2 = self.noise_buffer[: end - len(self.noise_buffer)]
            chunk = np.concatenate((part1, part2))

        # Update index with wrap-around
        self.noise_idx = end % len(self.noise_buffer)

        return chunk.astype(np.float32)

    def start_trial_capture(self, stimulus):
        """
        Start simultaneous playback and recording.

        - Stimulus is played through output device.
        - Background noise (if set) is mixed into output.
        - Input is recorded from the input device.

        Parameters
        ----------
        stimulus : array-like
            Audio signal to be played (mono or stereo).

        Returns
        -------
        threading.Event
            Event that is set when stimulus playback completes.
        """
        # Ensure float32 format
        stimulus = np.asarray(stimulus, dtype=np.float32)

        # Convert mono stimulus to stereo
        if stimulus.ndim == 1:
            stimulus = np.column_stack((stimulus, stimulus))

        with self._trial_lock:
            # Reset state for new trial
            self._trial_stop.clear()
            self._trial_playback_done.clear()
            self._recording_chunks = []

            num_samples = stimulus.shape[0]
            idx = 0  # playback index

            def callback(indata, outdata, frames, time, status):
                nonlocal idx

                # Report stream warnings/errors
                if status:
                    print("⚠️ Audio status:", status)

                end = min(idx + frames, num_samples)
                n = end - idx

                # Initialize output buffer with silence
                outdata.fill(0)

                # Write stimulus into output buffer
                if n > 0:
                    outdata[:n, :] = stimulus[idx:end, :]

                # Mix background noise if available
                if self.noise_buffer is not None and len(self.noise_buffer) > 0:
                    noise_chunk = self._get_noise_chunk(frames)

                    # Duplicate mono noise into stereo
                    outdata[:] = outdata + np.column_stack((noise_chunk, noise_chunk))

                    # Prevent clipping
                    outdata[:] = np.clip(outdata, -1.0, 1.0)

                # Store recorded input (channel 0 only)
                self._recording_chunks.append(indata[:, 0].copy())

                idx = end

                # Mark playback completion
                if idx >= num_samples and not self._trial_playback_done.is_set():
                    self._trial_playback_done.set()

                # Stop stream if requested
                if self._trial_stop.is_set():
                    raise sd.CallbackStop()

            def runner():
                # Open full-duplex audio stream (input + output)
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
                        # Keep stream active until stop signal
                        while not self._trial_stop.is_set():
                            self._trial_stop.wait(0.05)
                except Exception as e:
                    print("❌ Trial stream error:", e)
                    self._trial_playback_done.set()

            # Launch audio processing in background thread
            self._trial_thread = threading.Thread(target=runner, daemon=True)
            self._trial_thread.start()

            return self._trial_playback_done

    def stop_trial_capture(self):
        """
        Stop playback/recording and return recorded signal.

        Returns
        -------
        np.ndarray
            Concatenated mono recording from input channel.
        """
        with self._trial_lock:
            # Signal stream to stop
            self._trial_stop.set()

            # Wait for thread to terminate
            if self._trial_thread is not None:
                self._trial_thread.join(timeout=2.0)
                self._trial_thread = None

            # Return empty array if nothing recorded
            if not self._recording_chunks:
                return np.empty(0, dtype=np.float32)

            # Concatenate all recorded chunks
            return np.concatenate(self._recording_chunks).astype(np.float32)
