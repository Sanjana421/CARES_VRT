# os:
# Used for file and folder path handling.
# Similar to MATLAB fullfile and path utilities.
import os

# sys:
# Used here to access command-line arguments and to exit the application cleanly.
import sys

# soundfile:
# Used to read audio files from disk.
# Similar to MATLAB audio file loading functions.
import soundfile as sf

# QApplication / QMessageBox:
# Core Qt application object and dialog box for user warnings/validation.
from PySide6.QtWidgets import QApplication, QMessageBox

# Local application modules:
# - AudioEngine: handles playback and recording
# - ChildWindow: participant-facing interface
# - DataManager: saves trial and questionnaire data
# - LandingWindow: initial start screen
# - RAWindow: research assistant control screen
# - StimulusBuilder: creates trial stimuli
# - TrialController: manages trial flow
from modules.audio_engine import AudioEngine
from modules.child_gui import ChildWindow
from modules.data_manager import DataManager
from modules.landing_window import LandingWindow
from modules.ra_gui import RAWindow
from modules.stimulus_builder import StimulusBuilder
from modules.trial_controller import TrialController


def _load_mono_audio(path):
    """
    Load an audio file and return a mono waveform.

    If the file is stereo, the channels are averaged to create one channel.
    This is similar to collapsing a 2-column matrix into a single vector in MATLAB.
    """
    audio, fs = sf.read(path)
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    return audio, fs


def main():
    # Create the Qt application object.
    # This is the main event loop for the GUI.
    app = QApplication(sys.argv)

    # Landing window shown first when the program starts.
    landing = LandingWindow()

    def launch_experiment():
        # Close the landing screen once the session begins.
        landing.close()

        # Research assistant window used to control the session.
        window = RAWindow()
        screen_geo = QApplication.primaryScreen().availableGeometry()
        window.setGeometry(screen_geo)
        window.showFullScreen()

        # Participant-facing child window.
        child = ChildWindow()

        # StimulusBuilder loads the MATLAB lists and audio files,
        # then prepares the trial stimuli for the selected session.
        builder = StimulusBuilder(os.getcwd())

        # Session-level variables that are shared across nested callbacks.
        current_setup = {}
        data_manager = None
        audio_engine = None
        noise = None

        def build_and_start_list():
            """
            Create the current list of trials, configure audio playback,
            and begin the trial sequence.
            """
            nonlocal data_manager, current_setup, audio_engine, noise

            # Fixed SPL values used for this experiment.
            # These may correspond to calibration targets used across the study.
            target_spl_word = 38.5
            target_spl_dist = 37.5

            # Noise SPL is adjusted relative to the chosen SNR.
            target_spl_noise_base = 35.9
            target_spl_noise = target_spl_noise_base - current_setup["snr"]

            # Load calibrated continuous noise into the audio engine if available.
            if audio_engine is not None and noise is not None:
                audio_engine.set_continuous_noise(noise, target_spl_noise=target_spl_noise)

            # Build all trials for the selected list number and ear assignment.
            stimuli = builder.build_list(
                list_number=current_setup["list_number"],
                target_ear=current_setup["target_ear"],
                target_spl_word=target_spl_word,
                target_spl_dist=target_spl_dist,
                target_spl_noise=target_spl_noise,
            )

            # TrialController coordinates playback, recording, and response capture.
            controller = TrialController(stimuli, audio_engine)
            controller.data_manager = data_manager
            window.controller = controller

            def handle_trial_ready(trial_number, total_trials, word):
                # Update the research assistant screen and participant screen
                # with the current trial number, SNR, and target word.
                window.update_trial_info(trial_number, total_trials, current_setup["snr"])
                window.update_target_word(word)
                child.update_progress(trial_number, total_trials)

            def on_questionnaire_complete(answers):
                # Save questionnaire responses after the child finishes the rating page.
                question_texts = [q["text"] for q in child.questions]
                controller.data_manager.save_questionnaire(answers, question_texts)
                window.next_list_btn.setVisible(True)
                window.end_testing_btn.setVisible(True)
                child.show_waiting_screen()

            def handle_list_complete(responses):
                # When the list is finished, stop the noise stream and move to the feedback flow.
                nonlocal audio_engine
                if audio_engine is not None:
                    audio_engine.stop_noise()

                child.show_great_job_screen(
                    lambda: child.start_questionnaire(on_questionnaire_complete)
                )

            # Register callbacks used by the controller during the trial loop.
            controller.on_trial_ready = handle_trial_ready
            controller.on_list_complete = handle_list_complete

            # Reset progress display before starting the countdown and trial list.
            child.display_progress = 0
            child.current_progress = 0
            child.update()
            child.stacked_layout.setCurrentWidget(child.progress_page)

            # Show the prepare countdown, then begin the trial list.
            child.show_prepare_sequence(lambda: controller.start_list())

        def on_start_clicked():
            """
            Read setup values from the RA window, create the data manager and audio engine,
            then start the selected session.
            """
            nonlocal current_setup, data_manager, audio_engine, noise

            # Collect session parameters entered by the research assistant.
            setup_data = window.get_setup_data()
            if setup_data is None:
                return

            current_setup = setup_data

            # Stop any prior noise stream before creating a new audio engine.
            if audio_engine is not None:
                audio_engine.stop_noise()

            # Create the audio engine using the selected output mode.
            audio_engine = AudioEngine(output_mode=setup_data["output_mode"])

            # Fixed SPL values used in the current experimental setup.
            target_spl_word = 38.5
            target_spl_dist = 37.5

            # DataManager organizes all saved files for this session.
            data_manager = DataManager(
                subject_id=setup_data["subject_id"],
                visit=setup_data["visit"],
                run=setup_data["run"],
                snr=setup_data["snr"],
                dist_cond=setup_data["dist_cond"],
                target_spl_word=target_spl_word,
                target_spl_dist=target_spl_dist,
                list_number=setup_data["list_number"],
                target_ear=setup_data["target_ear"],
            )

            # Check whether this exact session configuration already exists.
            # This is a safeguard against accidental overwriting.
            if data_manager.check_duplicate():
                msg = QMessageBox(window)
                msg.setWindowTitle("Condition Already Exists")
                msg.setText(
                    "<b>A session with these exact conditions already exists.</b><br><br>"
                    f"Subject: {setup_data['subject_id']}  ·  "
                    f"Visit: {setup_data['visit']}  ·  "
                    f"Run: {setup_data['run']}  ·  "
                    f"List: {setup_data['list_number']}<br><br>"
                    "Do you want to overwrite the existing data?"
                )
                msg.setIcon(QMessageBox.Warning)
                msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
                msg.setDefaultButton(QMessageBox.No)

                if msg.exec() != QMessageBox.Yes:
                    return

                data_manager.overwrite_session()

            # Save session metadata before starting the trials.
            data_manager.save_metadata()

            # Load the continuous noise file used during the session.
            noise_path = os.path.join(os.getcwd(), "stim", "MTB_child.wav")
            noise, _ = _load_mono_audio(noise_path)

            # Switch the RA window into trial mode and begin the first list.
            window.show_trial_mode()
            build_and_start_list()

        def handle_next_list():
            # Move to the next list/setup flow after the current list is complete.
            nonlocal audio_engine

            window.next_list_btn.setVisible(False)
            window.end_testing_btn.setVisible(False)

            if audio_engine is not None:
                audio_engine.stop_noise()
                audio_engine = None

            window.show_setup_mode()
            child.show_waiting_screen()

        def handle_end_testing():
            # End the full session and show the final goodbye screen.
            nonlocal audio_engine

            window.next_list_btn.setVisible(False)
            window.end_testing_btn.setVisible(False)

            if audio_engine is not None:
                audio_engine.stop_noise()
                audio_engine = None

            window.show_session_complete()
            child.show_goodbye_screen()

        # Connect RA window controls to the session logic.
        window.start_button.clicked.connect(on_start_clicked)
        window.next_list_btn.clicked.connect(handle_next_list)
        window.end_testing_btn.clicked.connect(handle_end_testing)

        # Connect response buttons to the current trial controller.
        window.correct_btn.clicked.connect(lambda: window.controller.submit_response("Correct"))
        window.incorrect_btn.clicked.connect(lambda: window.controller.submit_response("Incorrect"))
        window.no_response_btn.clicked.connect(lambda: window.controller.submit_response("No Response"))
        window.not_sure_btn.clicked.connect(lambda: window.controller.submit_response("Not Sure"))

        # Show the RA window once everything has been initialized.
        window.show()

    # Connect landing screen buttons to launch or quit actions.
    landing.launch_full_btn.clicked.connect(launch_experiment)
    landing.exit_btn.clicked.connect(app.quit)

    # Show the landing page first.
    landing.show()

    # Enter the Qt event loop.
    sys.exit(app.exec())


# Standard Python entry point.
if __name__ == "__main__":
    main()
