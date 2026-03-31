import sys
import os
import soundfile as sf

from PySide6.QtWidgets import QApplication, QMessageBox

from modules.landing_window import LandingWindow
from modules.data_manager import DataManager
from modules.ra_gui import RAWindow
from modules.child_gui import ChildWindow
from modules.stimulus_builder import StimulusBuilder
from modules.audio_engine import AudioEngine
from modules.trial_controller import TrialController
from modules.calibration import scale_to_system_calibration


def main():
    app = QApplication(sys.argv)

    landing = LandingWindow()

    def launch_experiment():
        landing.close()

        window = RAWindow()
        screen_geo = QApplication.primaryScreen().availableGeometry()
        window.setGeometry(screen_geo)
        window.showFullScreen()

        child = ChildWindow()
        builder = StimulusBuilder(os.getcwd())

        # -----------------------------
        # SHARED STATE
        # -----------------------------
        current_setup = {}
        data_manager = None
        audio_engine = None
        noise = None

        # ----------------------------------------------------
        # FUNCTION TO BUILD + START A LIST
        # ----------------------------------------------------
        def build_and_start_list():
            nonlocal data_manager, current_setup, audio_engine

            target_spl_word = 53.5
            target_spl_dist = 49.7

            stimuli = builder.build_list(
                list_number=current_setup["list_number"],
                target_ear=current_setup["target_ear"],
                target_spl_word=target_spl_word,
                target_spl_dist=target_spl_dist
            )

            controller = TrialController(stimuli, audio_engine)
            controller.data_manager = data_manager
            window.controller = controller

            def handle_trial_ready(trial_number, total_trials, word):
                window.update_trial_info(trial_number, total_trials, current_setup["snr"])
                window.update_target_word(word)
                child.update_progress(trial_number, total_trials)

            def on_questionnaire_complete(answers):
                question_texts = [q["text"] for q in child.questions]
                controller.data_manager.save_questionnaire(answers, question_texts)

                window.next_list_btn.setVisible(True)
                window.end_testing_btn.setVisible(True)
                child.show_waiting_screen()

            def handle_list_complete(responses):
                child.show_great_job_screen(
                    lambda: child.start_questionnaire(on_questionnaire_complete)
                )

            controller.on_trial_ready = handle_trial_ready
            controller.on_list_complete = handle_list_complete

            child.display_progress = 0
            child.current_progress = 0
            child.update()
            child.stacked_layout.setCurrentWidget(child.progress_page)

            child.show_prepare_sequence(lambda: controller.start_list())

        # ----------------------------------------------------
        # START SESSION BUTTON
        # ----------------------------------------------------
        def on_start_clicked():
            nonlocal current_setup, data_manager, audio_engine, noise

            setup_data = window.get_setup_data()
            if setup_data is None:
                return

            current_setup = setup_data

            if audio_engine is not None:
                audio_engine.stop_noise()

            audio_engine = AudioEngine(output_mode=setup_data["output_mode"])

            target_spl_word = 53.5
            target_spl_dist = 49.7
            target_spl_noise = 45.4 - setup_data["snr"]

            data_manager = DataManager(
                subject_id=setup_data["subject_id"],
                visit=setup_data["visit"],
                run=setup_data["run"],
                snr=setup_data["snr"],
                dist_cond=setup_data["dist_cond"],
                target_spl_word=target_spl_word,
                target_spl_dist=target_spl_dist,
                list_number=setup_data["list_number"],
                target_ear=setup_data["target_ear"]
            )

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

            noise, fs = sf.read(os.path.join(os.getcwd(), "stim", "MTB_child.wav"))
            if noise.ndim > 1:
                noise = noise.mean(axis=1)

            noise = scale_to_system_calibration(noise, target_spl_noise)
            audio_engine.start_continuous_noise(noise)

            window.show_trial_mode()
            build_and_start_list()

        # ----------------------------------------------------
        # NEXT LIST BUTTON
        # ----------------------------------------------------
        def handle_next_list():
            nonlocal audio_engine

            window.next_list_btn.setVisible(False)
            window.end_testing_btn.setVisible(False)

            if audio_engine is not None:
                audio_engine.stop_noise()
                audio_engine = None

            window.show_setup_mode()
            child.show_waiting_screen()

        # ----------------------------------------------------
        # END TESTING BUTTON
        # ----------------------------------------------------
        def handle_end_testing():
            nonlocal audio_engine

            window.next_list_btn.setVisible(False)
            window.end_testing_btn.setVisible(False)

            if audio_engine is not None:
                audio_engine.stop_noise()
                audio_engine = None

            window.show_session_complete()
            child.show_goodbye_screen()

        # ----------------------------------------------------
        # CONNECT BUTTONS
        # ----------------------------------------------------
        window.start_button.clicked.connect(on_start_clicked)
        window.next_list_btn.clicked.connect(handle_next_list)
        window.end_testing_btn.clicked.connect(handle_end_testing)

        window.correct_btn.clicked.connect(lambda: window.controller.submit_response("Correct"))
        window.incorrect_btn.clicked.connect(lambda: window.controller.submit_response("Incorrect"))
        window.no_response_btn.clicked.connect(lambda: window.controller.submit_response("No Response"))
        window.not_sure_btn.clicked.connect(lambda: window.controller.submit_response("Not Sure"))

        window.show()

    landing.launch_full_btn.clicked.connect(launch_experiment)
    landing.exit_btn.clicked.connect(app.quit)
    landing.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
