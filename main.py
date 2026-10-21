import logging
import os
import sys
import traceback
from datetime import datetime

# --- logging first, so anything that goes wrong is written down --------------
from modules import paths

os.makedirs(paths.LOGS_DIR, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(paths.LOGS_DIR, "collection_%s.log" % datetime.now().strftime("%Y%m%d")),
    level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("distvrt")

import soundfile as sf                                                # noqa: E402
from PySide6.QtWidgets import QApplication, QMessageBox               # noqa: E402

from modules import preflight                           # noqa: E402
from modules.audio_engine import AudioEngine, AudioSetupError        # noqa: E402
from modules.child_gui import ChildWindow                            # noqa: E402
from modules.data_manager import DataManager                         # noqa: E402
from modules.landing_window import LandingWindow                     # noqa: E402
from modules.ra_gui import RAWindow                                  # noqa: E402
from modules.stimulus_builder import StimulusBuilder                 # noqa: E402
from modules.trial_controller import TrialController                 # noqa: E402

# SPL targets - unchanged from the GitHub version (calibration left as it was)
TARGET_SPL_WORD = 55.9
TARGET_SPL_DIST = 53.9
TARGET_SPL_NOISE_BASE = 54.4


def _error_box(parent, title, text, icon=QMessageBox.Critical):
    log.error("%s | %s", title, text.replace("\n", " / "))
    box = QMessageBox(parent)
    box.setWindowTitle(title)
    box.setIcon(icon)
    box.setText(text)
    box.exec()


def main():
    app = QApplication(sys.argv)

    def _hook(exc_type, exc, tb):
        log.error("Unhandled error\n%s", "".join(traceback.format_exception(exc_type, exc, tb)))
        _error_box(None, "Unexpected error",
                   "Something went wrong:\n\n%s\n\nDetails were saved to:\n%s\n\n"
                   "Data already saved was not changed." % (exc, paths.LOGS_DIR))

    sys.excepthook = _hook

    problems = [m for lvl, m in preflight.run_checks(check_audio=False) if lvl == "FAIL"]
    if problems:
        _error_box(None, "Setup problem", "The experiment cannot start:\n\n- " +
                   "\n- ".join(problems) + "\n\nRun Check_Setup.bat for details.")
        return 1

    log.info("Start. root=%s data=%s", paths.ROOT, paths.DATA_DIR)
    landing = LandingWindow()
    noise_cache = {}

    def launch_experiment():
        landing.close()

        window = RAWindow()
        window.setGeometry(QApplication.primaryScreen().availableGeometry())
        window.showFullScreen()

        child = ChildWindow()
        builder = StimulusBuilder()

        state = {"setup": {}, "dm": None, "engine": None}

        def to_setup(message=None):
            if state["engine"] is not None:
                state["engine"].stop_noise()
                state["engine"] = None
            window.next_list_btn.setVisible(False)
            window.end_testing_btn.setVisible(False)
            window.show_setup_mode()
            child.show_waiting_screen()
            if message:
                _error_box(window, "Session stopped", message)

        def build_and_start_list():
            setup, engine, dm = state["setup"], state["engine"], state["dm"]

            engine.set_continuous_noise(noise_cache["noise"],
                                        TARGET_SPL_NOISE_BASE - setup["snr"])
            stimuli = builder.build_list(
                list_number=setup["list_number"], target_ear=setup["target_ear"],
                dist_cond=setup["dist_cond"],
                target_spl_word=TARGET_SPL_WORD,
                target_spl_dist=TARGET_SPL_DIST)

            controller = TrialController(stimuli, engine)
            controller.data_manager = dm
            window.controller = controller

            def handle_trial_ready(trial_number, total_trials, word):
                window.update_trial_info(trial_number, total_trials, setup["snr"])
                window.update_target_word(word)
                child.update_progress(trial_number, total_trials)

            def on_questionnaire_complete(answers):
                dm.save_questionnaire(answers, [q["text"] for q in child.questions])
                window.next_list_btn.setVisible(True)
                window.end_testing_btn.setVisible(True)
                child.show_waiting_screen()

            def handle_list_complete(_responses):
                if state["engine"] is not None:
                    state["engine"].stop_noise()
                log.info("List complete: %s", dm.log_path)
                child.show_great_job_screen(
                    lambda: child.start_questionnaire(on_questionnaire_complete))

            controller.on_trial_ready = handle_trial_ready
            controller.on_list_complete = handle_list_complete
            controller.on_error = lambda msg: to_setup(msg)

            child.display_progress = 0
            child.current_progress = 0
            child.update()
            child.stacked_layout.setCurrentWidget(child.progress_page)
            child.show_prepare_sequence(lambda: controller.start_list())

        def on_start_clicked():
            setup = window.get_setup_data()
            if setup is None:
                return

            if state["engine"] is not None:
                state["engine"].stop_noise()
            try:
                state["engine"] = AudioEngine()
                dm = DataManager(
                    subject_id=setup["subject_id"], visit=setup["visit"], run=setup["run"],
                    snr=setup["snr"], dist_cond=setup["dist_cond"],
                    target_spl_word=TARGET_SPL_WORD,
                    target_spl_dist=TARGET_SPL_DIST,
                    list_number=setup["list_number"], target_ear=setup["target_ear"])
            except AudioSetupError as exc:
                state["engine"] = None
                _error_box(window, "Audio device not found", str(exc))
                return
            except (ValueError, OSError) as exc:
                state["engine"] = None
                _error_box(window, "Cannot start", str(exc))
                return

            if dm.check_duplicate():
                msg = QMessageBox(window)
                msg.setWindowTitle("Condition Already Exists")
                msg.setText(
                    "<b>Data for these exact conditions already exists.</b><br><br>"
                    "Subject: %s &nbsp;|&nbsp; Visit: %s &nbsp;|&nbsp; Run: %s &nbsp;|&nbsp; "
                    "List: %s &nbsp;|&nbsp; SNR: %s &nbsp;|&nbsp; Distractor: %s<br><br>"
                    "Replace it? The old files are moved to the <i>_replaced</i> folder "
                    "inside this visit - nothing is deleted."
                    % (setup["subject_id"], setup["visit"], setup["run"], setup["list_number"],
                       paths.matlab_num2str(setup["snr"]), "Yes" if setup["dist_cond"] else "No"))
                msg.setIcon(QMessageBox.Warning)
                msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
                msg.setDefaultButton(QMessageBox.No)
                if msg.exec() != QMessageBox.Yes:
                    state["engine"] = None
                    return
                dm.overwrite_session()

            state["setup"], state["dm"] = setup, dm
            dm.save_metadata()
            log.info("Session start %s", setup)

            if "noise" not in noise_cache:
                noise_cache["noise"], _ = sf.read(paths.NOISE_FILE, dtype="float32")

            window.show_trial_mode()
            build_and_start_list()

        def handle_next_list():
            to_setup()

        def handle_end_testing():
            if state["engine"] is not None:
                state["engine"].stop_noise()
                state["engine"] = None
            window.next_list_btn.setVisible(False)
            window.end_testing_btn.setVisible(False)
            window.show_session_complete()
            child.show_goodbye_screen()

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
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
