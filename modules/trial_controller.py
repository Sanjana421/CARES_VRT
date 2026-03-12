from PySide6.QtCore import QTimer


class TrialController:

    def __init__(self, trials, audio_engine):
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

    def start_list(self):

        # Always reset for new list
        self.current_trial_index = 0
        self.responses = []
        self.state = "PLAYING"

        self._start_next_trial()

    def _start_next_trial(self):

        if self.current_trial_index >= self.total_trials:
            self.state = "IDLE"

            if self.on_list_complete:
                QTimer.singleShot(
                    0,
                    lambda: self.on_list_complete(self.responses)
                )
            return

        trial_info = self.trials[self.current_trial_index]

        if self.on_trial_ready:
            self.on_trial_ready(
                trial_number=self.current_trial_index + 1,
                total_trials=self.total_trials,
                word=trial_info["word"]
            )

        stimulus = trial_info["stimulus"]

        recording = self.audio_engine.play_and_record(stimulus)
        self.last_recording = recording

        self.state = "AWAITING_RESPONSE"

    def submit_response(self, response):

        if self.state != "AWAITING_RESPONSE":
            return

        trial_info = self.trials[self.current_trial_index]
        trial_number = self.current_trial_index + 1

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