import csv
import math
import os
import random
import re
from datetime import datetime

import numpy as np
import soundfile as sf
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)
from scipy.optimize import curve_fit

from modules import paths, preflight
from modules.audio_engine import AudioEngine, AudioSetupError
from modules.calibration import scale_to_system_calibration
from modules.child_gui import ChildWindow
from modules.stimulus_builder import (
    TARGET_FS,
    StimulusBuilder,
    _cell_str,
    _read_mono,
    _resample,
)

# Keep these equal to the constants already used by main.py.
# The existing Python calibration values are not changed here.
TARGET_SPL_WORD = 55.9
TARGET_SPL_NOISE_BASE = 54.4

CSV_FIELDS = [
    "Talker",
    "ListNum",
    "Word",
    "Ear",
    "Response",
    "SNR",
    "Timestamp",
    "FilePath",
]


def matlab_progressive_snr_levels(poorest_snr):
    """
    Reproduce ProgressiveSNRtest.m's five groups of five words.

    MATLAB starts with the easiest level and decreases SNR by 2 dB
    after each five-word group.
    """
    if poorest_snr > 0:
        first_level = poorest_snr - 8
    else:
        first_level = poorest_snr + 8

    return [first_level - 2 * group for group in range(5)]


def _sigmoid(x, slope, intercept):
    z = np.clip(slope * x + intercept, -700, 700)
    return 1.0 / (1.0 + np.exp(-z))


def write_snr_estimates(progressive_csv, estimate_csv):
    """
    Port the core fit and threshold calculation from NEWCalc_customSNR.m.
    Fits grouped accuracy by SNR with an ordinary least-squares logistic curve.
    """
    grouped = {}

    with open(progressive_csv, "r", newline="", encoding="utf-8-sig") as file:
        for row in csv.DictReader(file):
            response = row.get("Response", "").strip().lower()
            if response not in ("correct", "incorrect"):
                continue

            snr = float(row["SNR"])
            grouped.setdefault(snr, []).append(1.0 if response == "correct" else 0.0)

    if len(grouped) < 2:
        raise ValueError("At least two SNR levels are needed to fit estimates.")

    x = np.array(sorted(grouped), dtype=float)
    accuracy = np.array(
        [np.mean(grouped[level]) for level in x],
        dtype=float,
    )

    params, covariance = curve_fit(
        _sigmoid,
        x,
        accuracy,
        p0=(0.1, 0.0),
        maxfev=20000,
    )

    slope, intercept = params
    if not math.isfinite(slope) or abs(slope) < 1e-12:
        raise ValueError("The logistic fit did not produce a usable slope.")

    rows = []
    for target in (0.50, 0.80):
        logit = math.log(target / (1.0 - target))
        estimate = (logit - intercept) / slope

        gradient = np.array(
            [
                -(logit - intercept) / (slope ** 2),
                -1.0 / slope,
            ],
            dtype=float,
        )
        variance = float(gradient @ covariance @ gradient.T)

        if not math.isfinite(variance) or variance < 0:
            raise ValueError("The fitted confidence interval is not usable.")

        standard_error = math.sqrt(variance)
        lower = estimate - 1.96 * standard_error
        upper = estimate + 1.96 * standard_error

        rows.append(
            {
                "TargetAccuracyPercent": target * 100,
                "SNR_Estimate_dB": estimate,
                "CI_Lower_dB": lower,
                "CI_Upper_dB": upper,
                "CI_Width_dB": upper - lower,
            }
        )

    with open(estimate_csv, "w", newline="", encoding="utf-8") as file:
        fields = [
            "TargetAccuracyPercent",
            "SNR_Estimate_dB",
            "CI_Lower_dB",
            "CI_Upper_dB",
            "CI_Width_dB",
        ]
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


class ProgressiveSNRWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DistVRT — Progressive SNR")
        self.resize(900, 650)

        self.engine = None
        self.child = None
        self.builder = None
        self.noise = None
        self.words = []
        self.responses = []
        self.apple_trials = set()
        self.apple_seen = set()
        self.apple_count = 0
        self.trial_index = 0
        self.current_snr_levels = []
        self.current_snr = None
        self.subject_id = ""
        self.list_number = 13
        self.ear = 1
        self.output_csv = ""

        self.pages = QStackedWidget()
        layout = QVBoxLayout(self)
        layout.addWidget(self.pages)

        self._build_setup_page()
        self._build_trial_page()
        self.pages.setCurrentWidget(self.setup_page)

    def _build_setup_page(self):
        self.setup_page = QWidget()
        layout = QVBoxLayout(self.setup_page)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(18)

        title = QLabel("Progressive SNR Setup")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 28px; font-weight: bold;")
        layout.addWidget(title)

        self.subject_input = QLineEdit()
        self.subject_input.setPlaceholderText("Subject ID, e.g. Claire_Pilot")
        layout.addWidget(self.subject_input)

        self.list_combo = QComboBox()
        for list_number in (13, 14, 15, 16):
            self.list_combo.addItem(str(list_number), list_number)
        layout.addWidget(self.list_combo)

        self.ear_combo = QComboBox()
        self.ear_combo.addItem("Left ear", 1)
        self.ear_combo.addItem("Right ear", 2)
        self.ear_combo.addItem("Both ears", 3)
        layout.addWidget(self.ear_combo)

        self.poorest_snr_input = QDoubleSpinBox()
        self.poorest_snr_input.setRange(-100.0, 100.0)
        self.poorest_snr_input.setDecimals(2)
        self.poorest_snr_input.setSingleStep(1.0)
        self.poorest_snr_input.setValue(-20.0)
        self.poorest_snr_input.setSuffix(" dB")
        layout.addWidget(self.poorest_snr_input)

        start_button = QPushButton("Start")
        start_button.clicked.connect(self.start_experiment)
        layout.addWidget(start_button)

        self.pages.addWidget(self.setup_page)

    def _build_trial_page(self):
        self.trial_page = QWidget()
        layout = QVBoxLayout(self.trial_page)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(24)

        self.trial_info = QLabel("")
        self.trial_info.setAlignment(Qt.AlignCenter)
        self.trial_info.setStyleSheet("font-size: 22px;")
        layout.addWidget(self.trial_info)

        self.word_label = QLabel("")
        self.word_label.setAlignment(Qt.AlignCenter)
        self.word_label.setStyleSheet("font-size: 42px; font-weight: bold;")
        layout.addWidget(self.word_label)

        buttons = QHBoxLayout()
        self.correct_button = QPushButton("Correct")
        self.incorrect_button = QPushButton("Incorrect")
        self.correct_button.clicked.connect(
            lambda: self.submit_response("Correct")
        )
        self.incorrect_button.clicked.connect(
            lambda: self.submit_response("Incorrect")
        )
        buttons.addWidget(self.correct_button)
        buttons.addWidget(self.incorrect_button)
        layout.addLayout(buttons)

        self.pages.addWidget(self.trial_page)

    def start_experiment(self):
        subject = self.subject_input.text().strip()
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", subject):
            QMessageBox.warning(
                self,
                "Invalid Subject ID",
                "Use letters, numbers, underscores, or hyphens in the Subject ID.",
            )
            return

        failures = [
            message
            for level, message in preflight.run_checks(check_audio=False)
            if level == "FAIL"
        ]
        if failures:
            QMessageBox.critical(
                self,
                "Setup problem",
                "The experiment cannot start:\n\n- "
                + "\n- ".join(failures),
            )
            return

        self.subject_id = subject
        self.list_number = int(self.list_combo.currentData())
        self.ear = int(self.ear_combo.currentData())
        poorest_snr = float(self.poorest_snr_input.value())
        self.current_snr_levels = matlab_progressive_snr_levels(poorest_snr)
        self.current_snr = self.current_snr_levels[0]

        try:
            self.builder = StimulusBuilder()
            if self.list_number > self.builder.n_lists:
                raise ValueError("The selected word list is not available.")

            self.engine = AudioEngine()
            self.noise, _ = sf.read(paths.NOISE_FILE, dtype="float32")
            self.engine.set_continuous_noise(
                self.noise,
                TARGET_SPL_NOISE_BASE - self.current_snr,
            )

            word_order = np.random.permutation(25)
            self.words = [
                _cell_str(
                    self.builder.word_lists[
                        word_order[index],
                        self.list_number - 1,
                    ]
                )
                for index in range(25)
            ]

            self.responses = []
            self.trial_index = 0
            self.apple_trials = set(random.sample(range(1, 25), 6))
            self.apple_trials.add(25)
            self.apple_seen = set()
            self.apple_count = 0

            subject_folder = paths.subject_dir(self.subject_id)
            self.output_csv = os.path.join(
                subject_folder,
                "SNRProgressive_%s.csv" % self.subject_id,
            )

            self.child = ChildWindow()
            self.child.update_progress(0, 7)
            self.pages.setCurrentWidget(self.trial_page)
            self.child.show_prepare_sequence(self.start_next_trial)

        except (AudioSetupError, OSError, ValueError, KeyError) as exc:
            self._stop_audio()
            QMessageBox.critical(self, "Cannot start", str(exc))

    def _set_noise_for_snr(self, snr):
        """
        Retain the existing noise waveform and phase while changing its
        calibrated level for the next five-word SNR group.
        """
        if self.engine is None or self.engine.noise_buffer is None:
            return

        self.engine.noise_buffer = scale_to_system_calibration(
            self.engine.noise_buffer,
            TARGET_SPL_NOISE_BASE - snr,
        )

    def start_next_trial(self):
        if self.trial_index >= 25:
            self.finish_list()
            return

        group_index = self.trial_index // 5
        self.current_snr = self.current_snr_levels[group_index]
        word = self.words[self.trial_index]

        self.trial_info.setText(
            "Word %d of 25     SNR: %.2f dB"
            % (self.trial_index + 1, self.current_snr)
        )
        self.word_label.setText(word)
        self.correct_button.setEnabled(True)
        self.incorrect_button.setEnabled(True)

        audio, fs = _read_mono(
            os.path.join(paths.WORD_DIR, word + ".wav")
        )
        audio = _resample(audio, fs, self.engine.samplerate)
        audio = scale_to_system_calibration(audio, TARGET_SPL_WORD)

        # MATLAB ProgressiveSNRtest.m uses 6103 leading zero samples.
        word_audio = np.concatenate(
            [np.zeros(6103, dtype=np.float32), audio.astype(np.float32)]
        )
        silence = np.zeros_like(word_audio)

        if self.ear == 1:
            stimulus = np.column_stack((word_audio, silence))
        elif self.ear == 2:
            stimulus = np.column_stack((silence, word_audio))
        else:
            stimulus = np.column_stack((word_audio, word_audio))

        self.engine.start_trial_capture(stimulus)

    def submit_response(self, response):
        if self.trial_index >= 25 or self.engine is None:
            return

        self.correct_button.setEnabled(False)
        self.incorrect_button.setEnabled(False)

        try:
            self.engine.stop_trial_capture()
        except Exception:
            pass

        word = self.words[self.trial_index]
        self.responses.append(
            {
                "Talker": "Female_2",
                "ListNum": self.list_number,
                "Word": word,
                "Ear": self.ear,
                "Response": response,
                "SNR": "%.2f" % self.current_snr,
                "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "FilePath": "stim/Female_2/%s.wav" % word,
            }
        )

        completed_trial = self.trial_index + 1
        if (
            completed_trial in self.apple_trials
            and completed_trial not in self.apple_seen
        ):
            self.apple_seen.add(completed_trial)
            self.apple_count += 1
            self.child.update_progress(self.apple_count, 7)

        self.trial_index += 1

        if self.trial_index < 25 and self.trial_index % 5 == 0:
            next_group = self.trial_index // 5
            self._set_noise_for_snr(self.current_snr_levels[next_group])

        self.start_next_trial()

    def finish_list(self):
        self._stop_audio()

        try:
            os.makedirs(os.path.dirname(self.output_csv), exist_ok=True)
            needs_header = (
                not os.path.exists(self.output_csv)
                or os.path.getsize(self.output_csv) == 0
            )
            with open(
                self.output_csv,
                "a",
                newline="",
                encoding="utf-8",
            ) as file:
                writer = csv.DictWriter(file, fieldnames=CSV_FIELDS)
                if needs_header:
                    writer.writeheader()
                writer.writerows(self.responses)

        except OSError as exc:
            QMessageBox.critical(
                self,
                "Could not save list",
                "The list could not be written to the configured data folder:\n\n"
                "%s\n\n%s" % (self.output_csv, exc),
            )
            return

        estimate_path = os.path.join(
            os.path.dirname(self.output_csv),
            "%s_SNR_Estimates.csv" % self.subject_id,
        )

        try:
            write_snr_estimates(self.output_csv, estimate_path)
            message = (
                "List saved successfully.\n\n"
                "Progressive data:\n%s\n\n"
                "SNR estimates:\n%s"
                % (self.output_csv, estimate_path)
            )
        except Exception as exc:
            message = (
                "List saved successfully.\n\n"
                "Progressive data:\n%s\n\n"
                "The SNR estimate could not be calculated:\n%s"
                % (self.output_csv, exc)
            )

        QMessageBox.information(self, "List Saved", message)

        if self.child is not None:
            self.child.show_great_job_screen(
                lambda: self.child.show_goodbye_screen()
            )

    def _stop_audio(self):
        if self.engine is not None:
            try:
                self.engine.stop_noise()
            except Exception:
                pass
            self.engine = None

    def closeEvent(self, event):
        self._stop_audio()
        if self.child is not None:
            self.child.close()
        event.accept()


def main():
    app = QApplication([])
    window = ProgressiveSNRWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
