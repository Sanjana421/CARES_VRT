import threading

from PySide6.QtCore import QObject, Signal, QTimer


class TrialController(QObject):
    """Plays a trial, keeps recording until the examiner scores it, then saves it.
    After trial 25 the log rows are written (like MATLAB's ComputeAndReport)."""

    _playback_done = Signal()

    def __init__(self, trials, audio_engine):
        super().__init__()
        self.trials = trials
        self.audio_engine = audio_engine
        self.current_trial_index = 0
        self.total_trials = len(trials)
        self.responses = []
        self.on_trial_ready = None
        self.on_list_complete = None
        self.on_error = None
        self.data_manager = None
        self.last_recording = None
        self.state = "IDLE"
        self._playback_done.connect(self._on_playback_complete)

    def _fail(self, message):
        self.state = "IDLE"
        try:
            self.audio_engine.stop_trial_capture()
        except Exception:                                         # noqa: BLE001
            pass
        if self.on_error:
            self.on_error(message)

    def start_list(self):
        self.current_trial_index = 0
        self.responses = []
        self.state = "PLAYING"
        QTimer.singleShot(2000, self._start_next_trial)       # MATLAB: pause(2)

    def submit_response(self, response):
        if self.state != "AWAITING_RESPONSE":
            return
        trial_info = self.trials[self.current_trial_index]
        trial_number = self.current_trial_index + 1

        recording = self.audio_engine.stop_trial_capture()
        self.last_recording = recording
        self.responses.append({"trial_number": trial_number, "response": response})

        if self.data_manager is not None:
            try:
                self.data_manager.save_trial(
                    trial_number=trial_number, trial_info=trial_info, response=response,
                    recording=recording, fs=self.audio_engine.samplerate)
            except Exception as exc:                              # noqa: BLE001
                self._fail("Could not save trial %d:\n%s\n\nThis list was stopped. Nothing "
                           "already saved was changed." % (trial_number, exc))
                return

        self.current_trial_index += 1
        self.state = "PLAYING"
        self._start_next_trial()

    def _start_next_trial(self):
        if self.current_trial_index >= self.total_trials:
            self.state = "IDLE"
            if self.data_manager is not None:
                try:
                    self.data_manager.finalize_list()
                except Exception as exc:                          # noqa: BLE001
                    self._fail("Could not write the log file:\n%s\n\nThe recordings are saved. "
                               "A copy of the scores is in the participant's Extras folder." % exc)
                    return
            if self.on_list_complete:
                QTimer.singleShot(0, lambda: self.on_list_complete(self.responses))
            return

        trial_info = self.trials[self.current_trial_index]
        if self.on_trial_ready:
            self.on_trial_ready(trial_number=self.current_trial_index + 1,
                                total_trials=self.total_trials, word=trial_info["word"])

        stimulus = trial_info["stimulus"]

        def _play():
            done = self.audio_engine.start_trial_capture(stimulus)
            done.wait()
            self._playback_done.emit()

        threading.Thread(target=_play, daemon=True).start()

    def _on_playback_complete(self):
        if getattr(self.audio_engine, "error", None):
            self._fail(self.audio_engine.error)
            return
        self.state = "AWAITING_RESPONSE"
