import sys
import os
from PySide6.QtWidgets import QApplication, QMessageBox

from modules.landing_window import LandingWindow
from modules.data_manager import DataManager
from modules.ra_gui import RAWindow
from modules.child_gui import ChildWindow
from modules.stimulus_builder import StimulusBuilder
from modules.audio_engine import AudioEngine
from modules.trial_controller import TrialController


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
        audio_engine = AudioEngine()

        # -----------------------------
        # SHARED STATE
        # -----------------------------
        current_setup = {}
        data_manager = None

        # ----------------------------------------------------
        # FUNCTION TO BUILD + START A LIST
        # ----------------------------------------------------
        def build_and_start_list():

            nonlocal data_manager, current_setup

            target_spl_noise = 52.9 - current_setup["snr"]
            target_spl_word = 42.5
            target_spl_dist = 44.7

            stimuli = builder.build_list(
                list_number=current_setup["list_number"],
                target_ear=current_setup["target_ear"],
                target_spl_word=target_spl_word,
                target_spl_dist=target_spl_dist,
                target_spl_noise=target_spl_noise
            )

            controller = TrialController(stimuli, audio_engine)
            controller.data_manager = data_manager
            window.controller = controller

            # ---------------------------------------
            # CALLBACKS
            # ---------------------------------------
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

            # Reset child progress screen
            child.display_progress = 0
            child.current_progress = 0
            child.update()
            child.stacked_layout.setCurrentWidget(child.progress_page)

            # Start list with countdown
            child.show_prepare_sequence(lambda: controller.start_list())

        # ----------------------------------------------------
        # START SESSION BUTTON
        # ----------------------------------------------------
        def on_start_clicked():

            nonlocal current_setup, data_manager

            setup_data = window.get_setup_data()
            if setup_data is None:
                return

            current_setup = setup_data

            target_spl_word = 42.5
            target_spl_dist = 44.7

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
                msg.button(QMessageBox.Yes).setText("  Overwrite  ")
                msg.button(QMessageBox.No).setText("  Cancel  ")
                msg.setStyleSheet("""
                    QMessageBox {
                        background-color: #FFF0F3;
                        color: #3B0A1A;
                    }
                    QLabel {
                        color: #3B0A1A;
                        font-size: 13px;
                        min-width: 380px;
                    }
                    QPushButton {
                        border-radius: 8px;
                        padding: 10px 28px;
                        font-weight: bold;
                        font-size: 13px;
                        min-width: 110px;
                    }
                    QPushButton[text="  Overwrite  "] {
                        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                            stop:0 #AD1457, stop:1 #E91E63);
                        color: white;
                        border: none;
                    }
                    QPushButton[text="  Overwrite  "]:hover {
                        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                            stop:0 #C2185B, stop:1 #F06292);
                    }
                    QPushButton[text="  Cancel  "] {
                        background-color: #FFF0F3;
                        color: #AD1457;
                        border: 2px solid #F48FB1;
                    }
                    QPushButton[text="  Cancel  "]:hover {
                        background-color: #FCE4EC;
                        border-color: #C2185B;
                    }
                """)
                if msg.exec() != QMessageBox.Yes:
                    return
                data_manager.delete_existing()

            window.show_trial_mode()
            build_and_start_list()

        # ----------------------------------------------------
        # NEXT LIST BUTTON
        # ----------------------------------------------------
        def handle_next_list():

            window.next_list_btn.setVisible(False)
            window.end_testing_btn.setVisible(False)

            # Move to next list number automatically
            window.show_setup_mode()
            
            # Reset child display
            child.show_waiting_screen()

        # ----------------------------------------------------
        # END TESTING BUTTON
        # ----------------------------------------------------
        def handle_end_testing():
            window.next_list_btn.setVisible(False)
            window.end_testing_btn.setVisible(False)
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