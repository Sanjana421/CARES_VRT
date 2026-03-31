import threading
from PySide6.QtCore import QObject, Signal, QTimer


class TrialController(QObject):
    """
    Starts playback, keeps recording open until the response is submitted,
    then saves the whole mic buffer for that trial.
    """

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
        self.data_manager = None
        self.last_recording = None
        self.state = "IDLE"

        self._playback_done.connect(self._on_playback_complete)

    def start_list(self):
        self.current_trial_index = 0
        self.responses = []
        self.state = "PLAYING"
        QTimer.singleShot(2000, self._start_next_trial)

    def submit_response(self, response):
        if self.state != "AWAITING_RESPONSE":
            return

        trial_info = self.trials[self.current_trial_index]
        trial_number = self.current_trial_index + 1

        # Stop recording now so the subject's spoken response is included
        recording = self.audio_engine.stop_trial_capture()
        self.last_recording = recording

        self.responses.append({
            "trial_number": trial_number,
            "response": response
        })

        if self.data_manager and self.last_recording is not None:
            self.data_manager.save_trial(
                trial_number=trial_number,
                trial_info=trial_info,
                response=response,
                recording=self.last_recording,
                fs=self.audio_engine.samplerate
            )

        self.current_trial_index += 1
        self.state = "PLAYING"
        self._start_next_trial()

    def _start_next_trial(self):
        if self.current_trial_index >= self.total_trials:
            self.state = "IDLE"
            if self.on_list_complete:
                QTimer.singleShot(0, lambda: self.on_list_complete(self.responses))
            return

        trial_info = self.trials[self.current_trial_index]

        if self.on_trial_ready:
            self.on_trial_ready(
                trial_number=self.current_trial_index + 1,
                total_trials=self.total_trials,
                word=trial_info["word"]
            )

        stimulus = trial_info["stimulus"]

        def _play():
            playback_done = self.audio_engine.start_trial_capture(stimulus)
            playback_done.wait()
            self._playback_done.emit()

        threading.Thread(target=_play, daemon=True).start()

    def _on_playback_complete(self):
        self.state = "AWAITING_RESPONSE"
