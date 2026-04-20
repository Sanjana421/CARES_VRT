# threading:
# Used to run audio playback in the background so the GUI stays responsive.
# Similar in purpose to running a separate process or timer-based background task.
import threading

# QObject and Signal:
# Base Qt object and custom signal support.
# QObject gives this class Qt event-loop integration.
# Signal is used here to notify the main thread when playback has completed.
# QTimer is used for delayed actions inside the Qt event loop.
from PySide6.QtCore import QObject, Signal, QTimer


class TrialController(QObject):
    """
    Controls trial presentation and response collection for one stimulus list.

    Workflow:
    1. Start each trial by playing the stimulus and opening recording.
    2. Wait for playback to finish.
    3. Keep recording open until the response is submitted.
    4. Stop recording and save the trial data.
    """

    # Qt signal emitted when stimulus playback has finished.
    _playback_done = Signal()

    def __init__(self, trials, audio_engine):
        super().__init__()

        # List of trial dictionaries produced by StimulusBuilder.
        # Each entry contains the stimulus waveform and trial metadata.
        self.trials = trials

        # AudioEngine handles playback, microphone capture, and noise mixing.
        self.audio_engine = audio_engine

        # Index of the trial currently being run.
        self.current_trial_index = 0

        # Total number of trials in the current list.
        self.total_trials = len(trials)

        # Stores response records for the current list.
        self.responses = []

        # Callback used by the main UI when a trial is ready to be displayed.
        self.on_trial_ready = None

        # Callback used when all trials in the list are complete.
        self.on_list_complete = None

        # Data manager used to save behavioral data and recordings.
        self.data_manager = None

        # Most recent recorded audio buffer returned after stopping capture.
        self.last_recording = None

        # Simple state machine for trial flow control.
        # Common values:
        # - IDLE
        # - PLAYING
        # - AWAITING_RESPONSE
        self.state = "IDLE"

        # Connect the internal Qt signal to the completion handler.
        self._playback_done.connect(self._on_playback_complete)

    def start_list(self):
        # Reset trial index and response storage before starting a new list.
        self.current_trial_index = 0
        self.responses = []

        # Set the controller state to indicate that trials are underway.
        self.state = "PLAYING"

        # Wait 2 seconds before starting the first trial.
        # This gives the interface time to settle before playback begins.
        QTimer.singleShot(2000, self._start_next_trial)

    def submit_response(self, response):
        """
        Called when the participant or experimenter submits a response.

        This stops the recording buffer, stores the response, and saves the trial.
        """
        # Ignore responses unless the controller is in the expected state.
        if self.state != "AWAITING_RESPONSE":
            return

        # Retrieve metadata for the current trial.
        trial_info = self.trials[self.current_trial_index]
        trial_number = self.current_trial_index + 1

        # Stop recording and retrieve the full captured microphone buffer.
        recording = self.audio_engine.stop_trial_capture()
        self.last_recording = recording

        # Store the response locally for list-level summary handling.
        self.responses.append({
            "trial_number": trial_number,
            "response": response
        })

        # Save trial data and audio if a data manager has been attached.
        if self.data_manager and self.last_recording is not None:
            self.data_manager.save_trial(
                trial_number=trial_number,
                trial_info=trial_info,
                response=response,
                recording=self.last_recording,
                fs=self.audio_engine.samplerate
            )

        # Advance to the next trial.
        self.current_trial_index += 1
        self.state = "PLAYING"
        self._start_next_trial()

    def _start_next_trial(self):
        # When all trials are finished, return to idle state and notify the UI.
        if self.current_trial_index >= self.total_trials:
            self.state = "IDLE"
            if self.on_list_complete:
                QTimer.singleShot(0, lambda: self.on_list_complete(self.responses))
            return

        # Get the trial data for the current trial.
        trial_info = self.trials[self.current_trial_index]

        # Notify the UI that a new trial is ready to be displayed.
        if self.on_trial_ready:
            self.on_trial_ready(
                trial_number=self.current_trial_index + 1,
                total_trials=self.total_trials,
                word=trial_info["word"]
            )

        # Extract the stereo stimulus for playback.
        stimulus = trial_info["stimulus"]

        def _play():
            # Start playback and recording together.
            # The returned event is set when the stimulus playback has completed.
            playback_done = self.audio_engine.start_trial_capture(stimulus)

            # Wait until playback finishes before moving to the response state.
            playback_done.wait()

            # Emit a Qt signal so the main thread can safely update state.
            self._playback_done.emit()

        # Run playback in a background thread so the interface remains responsive.
        threading.Thread(target=_play, daemon=True).start()

    def _on_playback_complete(self):
        # Once the stimulus has finished playing, keep recording open
        # and wait for the response to be entered.
        self.state = "AWAITING_RESPONSE"# threading:
# Used to run audio playback in the background so the GUI stays responsive.
# Similar in purpose to running a separate process or timer-based background task.
import threading

# QObject and Signal:
# Base Qt object and custom signal support.
# QObject gives this class Qt event-loop integration.
# Signal is used here to notify the main thread when playback has completed.
# QTimer is used for delayed actions inside the Qt event loop.
from PySide6.QtCore import QObject, Signal, QTimer


class TrialController(QObject):
    """
    Controls trial presentation and response collection for one stimulus list.

    Workflow:
    1. Start each trial by playing the stimulus and opening recording.
    2. Wait for playback to finish.
    3. Keep recording open until the response is submitted.
    4. Stop recording and save the trial data.
    """

    # Qt signal emitted when stimulus playback has finished.
    _playback_done = Signal()

    def __init__(self, trials, audio_engine):
        super().__init__()

        # List of trial dictionaries produced by StimulusBuilder.
        # Each entry contains the stimulus waveform and trial metadata.
        self.trials = trials

        # AudioEngine handles playback, microphone capture, and noise mixing.
        self.audio_engine = audio_engine

        # Index of the trial currently being run.
        self.current_trial_index = 0

        # Total number of trials in the current list.
        self.total_trials = len(trials)

        # Stores response records for the current list.
        self.responses = []

        # Callback used by the main UI when a trial is ready to be displayed.
        self.on_trial_ready = None

        # Callback used when all trials in the list are complete.
        self.on_list_complete = None

        # Data manager used to save behavioral data and recordings.
        self.data_manager = None

        # Most recent recorded audio buffer returned after stopping capture.
        self.last_recording = None

        # Simple state machine for trial flow control.
        # Common values:
        # - IDLE
        # - PLAYING
        # - AWAITING_RESPONSE
        self.state = "IDLE"

        # Connect the internal Qt signal to the completion handler.
        self._playback_done.connect(self._on_playback_complete)

    def start_list(self):
        # Reset trial index and response storage before starting a new list.
        self.current_trial_index = 0
        self.responses = []

        # Set the controller state to indicate that trials are underway.
        self.state = "PLAYING"

        # Wait 2 seconds before starting the first trial.
        # This gives the interface time to settle before playback begins.
        QTimer.singleShot(2000, self._start_next_trial)

    def submit_response(self, response):
        """
        Called when the participant or experimenter submits a response.

        This stops the recording buffer, stores the response, and saves the trial.
        """
        # Ignore responses unless the controller is in the expected state.
        if self.state != "AWAITING_RESPONSE":
            return

        # Retrieve metadata for the current trial.
        trial_info = self.trials[self.current_trial_index]
        trial_number = self.current_trial_index + 1

        # Stop recording and retrieve the full captured microphone buffer.
        recording = self.audio_engine.stop_trial_capture()
        self.last_recording = recording

        # Store the response locally for list-level summary handling.
        self.responses.append({
            "trial_number": trial_number,
            "response": response
        })

        # Save trial data and audio if a data manager has been attached.
        if self.data_manager and self.last_recording is not None:
            self.data_manager.save_trial(
                trial_number=trial_number,
                trial_info=trial_info,
                response=response,
                recording=self.last_recording,
                fs=self.audio_engine.samplerate
            )

        # Advance to the next trial.
        self.current_trial_index += 1
        self.state = "PLAYING"
        self._start_next_trial()

    def _start_next_trial(self):
        # When all trials are finished, return to idle state and notify the UI.
        if self.current_trial_index >= self.total_trials:
            self.state = "IDLE"
            if self.on_list_complete:
                QTimer.singleShot(0, lambda: self.on_list_complete(self.responses))
            return

        # Get the trial data for the current trial.
        trial_info = self.trials[self.current_trial_index]

        # Notify the UI that a new trial is ready to be displayed.
        if self.on_trial_ready:
            self.on_trial_ready(
                trial_number=self.current_trial_index + 1,
                total_trials=self.total_trials,
                word=trial_info["word"]
            )

        # Extract the stereo stimulus for playback.
        stimulus = trial_info["stimulus"]

        def _play():
            # Start playback and recording together.
            # The returned event is set when the stimulus playback has completed.
            playback_done = self.audio_engine.start_trial_capture(stimulus)

            # Wait until playback finishes before moving to the response state.
            playback_done.wait()

            # Emit a Qt signal so the main thread can safely update state.
            self._playback_done.emit()

        # Run playback in a background thread so the interface remains responsive.
        threading.Thread(target=_play, daemon=True).start()

    def _on_playback_complete(self):
        # Once the stimulus has finished playing, keep recording open
        # and wait for the response to be entered.
        self.state = "AWAITING_RESPONSE"
