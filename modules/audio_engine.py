"""
Real-time playback + recording through the MOTU M Series.
Equivalent of MATLAB:  audioPlayerRecorder('Device','MOTU M Series','BufferSize',512,
PlayerChannelMapping,[3 4], RecorderChannelMapping,[1])  +  audioplayer for the noise.

Devices are found BY NAME (config.ini [audio]) so Windows device numbers can differ
between lab computers.
"""
import threading

import numpy as np
import sounddevice as sd

from modules import paths
from modules.calibration import scale_to_system_calibration

HOST_PREFERENCE = ["Windows DirectSound", "MME", "Windows WASAPI", "Windows WDM-KS"]


class AudioSetupError(RuntimeError):
    pass


def list_devices_text():
    hosts = [h["name"] for h in sd.query_hostapis()]
    lines = []
    for i, d in enumerate(sd.query_devices()):
        lines.append("  %2d  in=%d out=%d  [%s]  %s" % (
            i, d["max_input_channels"], d["max_output_channels"],
            hosts[d["hostapi"]], d["name"]))
    return "\n".join(lines)


def resolve_devices():
    """Return (input_index, output_index, host_api_name). Raises AudioSetupError."""
    iface = paths.cfg("audio", "interface", "MOTU").lower()
    out_key = paths.cfg("audio", "output_name", "Out 3-4").lower()
    in_key = paths.cfg("audio", "input_name", "In 1-2").lower()
    devs = sd.query_devices()
    hosts = [h["name"] for h in sd.query_hostapis()]

    def match(key, chan_key, hostname):
        return [i for i, d in enumerate(devs)
                if iface in d["name"].lower() and key in d["name"].lower()
                and d[chan_key] > 0 and hosts[d["hostapi"]] == hostname]

    order = HOST_PREFERENCE + [h for h in hosts if h not in HOST_PREFERENCE]
    for host in order:
        o = match(out_key, "max_output_channels", host)
        n = match(in_key, "max_input_channels", host)
        if o and n:
            return n[0], o[0], host
    raise AudioSetupError(
        "Could not find the MOTU audio interface.\n\n"
        "Looking for an output containing '%s' and an input containing '%s' "
        "(both with '%s' in the name).\n"
        "Check that the MOTU is switched on and plugged in, then run Check_Setup.bat.\n\n"
        "Devices Windows reports:\n%s" % (out_key, in_key, iface, list_devices_text()))


class AudioEngine:
    def __init__(self, samplerate=None, blocksize=None, output_mode=None):
        self.samplerate = samplerate or paths.cfg_int("audio", "samplerate", 44100)
        self.blocksize = blocksize or paths.cfg_int("audio", "blocksize", 512)
        self.input_device, self.output_device, self.host_api = resolve_devices()
        self.error = None

        self.noise_buffer = None
        self.noise_idx = 0

        self._stream = None
        self._stim = None
        self._pos = 0
        self._trial_playback_done = threading.Event()
        self._recording_chunks = []
        self._cb_lock = threading.Lock()

    # ------------------------------------------------------------------ tone
    def play_test_tone(self, duration=0.7, freq=440, level=0.05):
        """Short quiet tone, left speaker then right speaker."""
        t = np.linspace(0, duration, int(self.samplerate * duration), endpoint=False)
        tone = (level * np.sin(2 * np.pi * freq * t)).astype(np.float32)
        silence = np.zeros_like(tone)
        sig = np.concatenate([np.column_stack((tone, silence)),
                              np.column_stack((silence, tone))])
        sd.play(sig, samplerate=self.samplerate, device=self.output_device)
        sd.wait()

    # ----------------------------------------------------------------- noise
    def set_continuous_noise(self, noise, target_spl_noise):
        """Scale noise like scale2SysCalSF (per channel), start it at a random point of
        the file (MakeStim) and START PLAYING IT NOW, continuously, until stop_noise().
        MATLAB: play(noisePlayer) before the first trial; it never pauses between trials."""
        noise = np.asarray(noise, dtype=np.float32)
        if noise.ndim == 1:
            noise = np.column_stack((noise, noise))
        noise = scale_to_system_calibration(noise, target_spl_noise)
        start = int(np.random.randint(1, len(noise) + 1))
        self.noise_buffer = np.roll(noise, -start, axis=0)
        self.noise_idx = 0
        self._open_stream()

    def stop_noise(self):
        self._close_stream()
        self.noise_buffer = None
        self.noise_idx = 0

    def _noise_chunk(self, frames):
        n = len(self.noise_buffer)
        idx = (self.noise_idx + np.arange(frames)) % n
        self.noise_idx = int((self.noise_idx + frames) % n)
        return self.noise_buffer[idx]

    # ---------------------------------------------------------------- stream
    # One duplex stream stays open for the whole list.  The noise is mixed into it
    # all the time (so it is continuous, with no gap between trials); the trial
    # stimulus and the microphone recording are switched on and off inside it.
    def _callback(self, indata, outdata, frames, time_info, status):
        outdata.fill(0)
        with self._cb_lock:
            stim, pos = self._stim, self._pos
            if stim is not None:
                end = min(pos + frames, len(stim))
                if end > pos:
                    outdata[:end - pos, :] = stim[pos:end, :]
                self._pos = end
                self._recording_chunks.append(indata[:, 0].copy())
                if end >= len(stim) and not self._trial_playback_done.is_set():
                    self._trial_playback_done.set()
        if self.noise_buffer is not None:
            outdata[:] = np.clip(outdata + self._noise_chunk(frames), -1.0, 1.0)

    def _open_stream(self):
        self._close_stream()
        try:
            self._stream = sd.Stream(samplerate=self.samplerate, blocksize=self.blocksize,
                                     device=(self.input_device, self.output_device),
                                     channels=(1, 2), dtype="float32", latency="low",
                                     callback=self._callback)
            self._stream.start()
        except Exception as exc:                                    # noqa: BLE001
            self._stream = None
            raise AudioSetupError("Could not open the audio stream: %s" % exc)

    def _close_stream(self):
        stream, self._stream = self._stream, None
        if stream is not None:
            try:
                stream.stop()
                stream.close()
            except Exception:                                       # noqa: BLE001
                pass

    # ----------------------------------------------------------------- trial
    def start_trial_capture(self, stimulus):
        """Play `stimulus` on top of the running noise and record the mic until
        stop_trial_capture().  Returns an Event set when the stimulus has finished."""
        stimulus = np.asarray(stimulus, dtype=np.float32)
        if stimulus.ndim == 1:
            stimulus = np.column_stack((stimulus, stimulus))
        self.error = None
        try:
            if self._stream is None or not self._stream.active:
                self._open_stream()
        except AudioSetupError as exc:
            self.error = str(exc)
            self._trial_playback_done.set()
            return self._trial_playback_done
        with self._cb_lock:
            self._trial_playback_done.clear()
            self._recording_chunks = []
            self._pos = 0
            self._stim = stimulus
        return self._trial_playback_done

    def stop_trial_capture(self):
        """Stop the trial (noise keeps playing) and return the mono recording."""
        with self._cb_lock:
            self._stim = None
            chunks, self._recording_chunks = self._recording_chunks, []
        if not chunks:
            return np.empty(0, dtype=np.float32)
        return np.concatenate(chunks).astype(np.float32)
