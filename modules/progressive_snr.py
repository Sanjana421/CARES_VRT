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
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)
from scipy.optimize import curve_fit

from modules import paths, preflight
from modules.audio_engine import AudioEngine, AudioSetupError
from modules.calibration import scale_to_system_calibration
from modules.child_gui import ChildWindow
from modules.ra_gui import GLOBAL_STYLE
from modules.stimulus_builder import (
    StimulusBuilder,
    _cell_str,
    _read_mono,
    _resample,
)


# Keep these equal to the constants already used by main.py.
# The current collection calibration values are unchanged.
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


def matlab_progressive_snr_levels(poorest_snr, step_db=2.0):
    """
    Create five SNR levels for five words per level.

    With a 2 dB step, this matches ProgressiveSNRtest.m:
    the first group is easier than the poorest-SNR endpoint, then
    the SNR decreases after each five-word group.
    """
    poorest_snr = float(poorest_snr)
    step_db = float(step_db)

    if not math.isfinite(poorest_snr):
        raise ValueError("The poorest SNR endpoint must be a finite number.")
    if not math.isfinite(step_db) or step_db <= 0:
        raise ValueError("The SNR step must be a positive number.")

    offset = 4 * step_db

    if poorest_snr > 0:
        first_level = poorest_snr - offset
    else:
        first_level = poorest_snr + offset

    return [
        first_level - step_db * group
        for group in range(5)
    ]


def _sigmoid(x, slope, intercept):
    z = np.clip(slope * x + intercept, -700, 700)
    return 1.0 / (1.0 + np.exp(-z))


def write_snr_estimates(progressive_csv, estimate_csv):
    """
    Port the core fit and threshold calculation from NEWCalc_customSNR.m.

    skipinitialspace=True lets Python read both Python-written CSVs and
    MATLAB-written CSVs, whose headers and rows have spaces after commas.
    """
    grouped = {}

    with open(
        progressive_csv,
        "r",
        newline="",
        encoding="utf-8-sig",
    ) as file:
        reader = csv.DictReader(file, skipinitialspace=True)

        for row in reader:
            response = row.get("Response", "").strip().lower()
            if response not in ("correct", "incorrect"):
                continue

            snr = float(row["SNR"])
            grouped.setdefault(snr, []).append(
                1.0 if response == "correct" else 0.0
            )

    if len(grouped) < 2:
        raise ValueError(
            "At least two SNR levels are needed to fit estimates."
        )

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
            raise ValueError(
                "The fitted confidence interval is not usable."
            )

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

    estimate_fields = [
        "TargetAccuracyPercent",
        "SNR_Estimate_dB",
        "CI_Lower_dB",
        "CI_Upper_dB",
        "CI_Width_dB",
    ]

    with open(
        estimate_csv,
        "w",
        newline="",
        encoding="utf-8",
    ) as file:
        writer = csv.DictWriter(file, fieldnames=estimate_fields)
        writer.writeheader()
        writer.writerows(rows)


class ProgressiveSNRWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DistVRT — Progressive SNR")
        self.setMinimumSize(1100, 720)
        self.setStyleSheet(GLOBAL_STYLE)
        self.setObjectName("page-bg")
        self.setAttribute(Qt.WA_StyledBackground, True)

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
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.pages)

        self._build_setup_page()
        self._build_trial_page()
        self.pages.setCurrentWidget(self.setup_page)

    def _make_header(self, screen_name):
        wrapper = QWidget()
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        bar = QFrame()
        bar.setObjectName("header-bar")
        bar.setAttribute(Qt.WA_StyledBackground, True)

        bar_layout = QHBoxLayout(bar)
        bar_layout.setContentsMargins(36, 0, 36, 0)
        bar_layout.setSpacing(14)

        title = QLabel("DistVRT")
        title.setObjectName("header-title")

        separator = QLabel("·")
        separator.setStyleSheet(
            "color: rgba(255,182,193,0.5); "
            "font-size: 20px; font-weight: 300;"
        )

        breadcrumb = QLabel(screen_name.upper())
        breadcrumb.setObjectName("breadcrumb")

        badge_text = (
            "● SETUP"
            if "SETUP" in screen_name.upper()
            else "● ACTIVE"
        )
        badge = QLabel(badge_text)
        badge.setObjectName("header-badge")

        bar_layout.addWidget(title)
        bar_layout.addWidget(separator)
        bar_layout.addWidget(breadcrumb)
        bar_layout.addStretch()
        bar_layout.addWidget(badge)
        layout.addWidget(bar)

        accent = QFrame()
        accent.setObjectName("accent-bar")
        accent.setAttribute(Qt.WA_StyledBackground, True)
        layout.addWidget(accent)

        return wrapper

    def _make_section_card(self, label_text):
        card = QFrame()
        card.setObjectName("section-card")
        card.setAttribute(Qt.WA_StyledBackground, True)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(28, 20, 28, 24)
        layout.setSpacing(16)

        label = QLabel(label_text)
        label.setObjectName("section-label")
        layout.addWidget(label)

        divider = QFrame()
        divider.setObjectName("h-divider")
        divider.setAttribute(Qt.WA_StyledBackground, True)
        layout.addWidget(divider)

        return card, layout

    def _field_row(self, label_text, widget):
        row = QHBoxLayout()
        row.setSpacing(20)

        label = QLabel(label_text.upper())
        label.setObjectName("field-label")
        label.setFixedWidth(230)
        label.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)

        row.addWidget(label)
        row.addWidget(widget, stretch=1)
        return row

    def _build_setup_page(self):
        self.setup_page = QWidget()
        self.setup_page.setObjectName("page-bg")
        self.setup_page.setAttribute(Qt.WA_StyledBackground, True)

        outer = QVBoxLayout(self.setup_page)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(self._make_header("Progressive SNR Setup"))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        inner = QWidget()
        inner.setObjectName("page-bg")
        inner.setAttribute(Qt.WA_StyledBackground, True)

        content = QVBoxLayout(inner)
        content.setContentsMargins(52, 36, 52, 36)
        content.setSpacing(20)

        constants_card, constants_layout = self._make_section_card(
            "SESSION CONSTANTS"
        )

        self.subject_input = QLineEdit()
        self.subject_input.setPlaceholderText("e.g.  Claire_Pilot")
        constants_layout.addLayout(
            self._field_row("Subject ID", self.subject_input)
        )

        # The selected number is checked against the loaded word-list file
        # before the experiment begins.
        self.list_spin = QSpinBox()
        self.list_spin.setRange(1, 99)
        self.list_spin.setValue(13)
        constants_layout.addLayout(
            self._field_row("List Number", self.list_spin)
        )

        self.ear_combo = QComboBox()
        self.ear_combo.addItem("Left Ear", 1)
        self.ear_combo.addItem("Right Ear", 2)
        self.ear_combo.addItem("Both Ears", 3)
        self.ear_combo.setMinimumHeight(44)
        self.ear_combo.setStyleSheet(
            "QComboBox {"
            " background-color: #FFF5F7;"
            " border: 1.5px solid #F8BBD0;"
            " border-radius: 9px;"
            " padding: 8px 14px;"
            " color: #2D0A14;"
            " font-size: 14px;"
            " font-weight: 600;"
            "}"
            "QComboBox:hover { border-color: #C2185B; }"
            "QComboBox:focus {"
            " border-color: #E91E63;"
            " background-color: #FFFAFC;"
            "}"
            "QComboBox QAbstractItemView {"
            " background-color: #FFFFFF;"
            " selection-background-color: #FCE4EC;"
            " color: #2D0A14;"
            "}"
        )
        constants_layout.addLayout(
            self._field_row("Target Ear", self.ear_combo)
        )
        content.addWidget(constants_card)

        snr_card, snr_layout = self._make_section_card(
            "PROGRESSIVE SNR PARAMETERS"
        )

        self.poorest_snr_input = QDoubleSpinBox()
        self.poorest_snr_input.setRange(-100.0, 100.0)
        self.poorest_snr_input.setDecimals(2)
        self.poorest_snr_input.setSingleStep(0.5)
        self.poorest_snr_input.setValue(-20.0)
        self.poorest_snr_input.setSuffix("  dB")
        snr_layout.addLayout(
            self._field_row(
                "Poorest SNR Endpoint",
                self.poorest_snr_input,
            )
        )

        self.snr_step_input = QDoubleSpinBox()
        self.snr_step_input.setRange(0.1, 10.0)
        self.snr_step_input.setDecimals(1)
        self.snr_step_input.setSingleStep(0.5)
        self.snr_step_input.setValue(2.0)
        self.snr_step_input.setSuffix("  dB")
        snr_layout.addLayout(
            self._field_row("SNR Step Size", self.snr_step_input)
        )

        note = QLabel(
            "25 words total · 5 words at each of 5 SNR levels. "
            "The default 2 dB step matches the MATLAB protocol."
        )
        note.setWordWrap(True)
        note.setStyleSheet(
            "color: #9C4060; font-size: 12px; padding-top: 4px;"
        )
        snr_layout.addWidget(note)
        content.addWidget(snr_card)

        content.addSpacing(12)
        button_row = QHBoxLayout()
        button_row.addStretch()

        start_button = QPushButton("START PROGRESSIVE SNR  ▶")
        start_button.setObjectName("start-btn")
        start_button.setCursor(Qt.PointingHandCursor)
        start_button.clicked.connect(self.start_experiment)
        button_row.addWidget(start_button)

        button_row.addStretch()
        content.addLayout(button_row)
        content.addStretch()

        scroll.setWidget(inner)
        outer.addWidget(scroll, stretch=1)
        self.pages.addWidget(self.setup_page)

    def _build_trial_page(self):
        self.trial_page = QWidget()
        self.trial_page.setObjectName("page-bg")
        self.trial_page.setAttribute(Qt.WA_StyledBackground, True)

        outer = QVBoxLayout(self.trial_page)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(
            self._make_header("Progressive SNR Experiment")
        )

        body = QHBoxLayout()
        body.setContentsMargins(48, 32, 48, 32)
        body.setSpacing(28)

        left = QVBoxLayout()
        left.setSpacing(18)

        stats = QHBoxLayout()
        stats.setSpacing(0)

        trial_column = QVBoxLayout()
        trial_column.setSpacing(3)

        trial_key = QLabel("TRIAL")
        trial_key.setObjectName("trial-stat-key")

        self.trial_info = QLabel("—")
        self.trial_info.setObjectName("trial-stat-val")

        trial_column.addWidget(trial_key)
        trial_column.addWidget(self.trial_info)
        stats.addLayout(trial_column)

        stats.addStretch()

        snr_column = QVBoxLayout()
        snr_column.setSpacing(3)

        snr_key = QLabel("SNR")
        snr_key.setObjectName("trial-stat-key")

        self.snr_info = QLabel("—")
        self.snr_info.setObjectName("snr-stat-val")

        snr_column.addWidget(snr_key)
        snr_column.addWidget(self.snr_info)
        stats.addLayout(snr_column)

        left.addLayout(stats)

        word_card = QFrame()
        word_card.setObjectName("word-card")
        word_card.setAttribute(Qt.WA_StyledBackground, True)
        word_card.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Expanding,
        )

        word_layout = QVBoxLayout(word_card)
        word_layout.setAlignment(Qt.AlignCenter)
        word_layout.setContentsMargins(28, 28, 28, 28)

        kicker = QLabel("TARGET WORD")
        kicker.setAlignment(Qt.AlignCenter)
        kicker.setStyleSheet(
            "font-size: 10px; font-weight: 800; "
            "color: #C2185B; letter-spacing: 3px;"
        )

        self.word_label = QLabel("—")
        self.word_label.setAlignment(Qt.AlignCenter)
        self.word_label.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Expanding,
        )
        self.word_label.setWordWrap(True)
        self.word_label.setStyleSheet(
            "color: #C2185B; font-size: 156px; "
            "font-weight: 900; letter-spacing: 6px;"
        )

        word_layout.addWidget(kicker)
        word_layout.addWidget(self.word_label, stretch=1)
        left.addWidget(word_card, stretch=1)

        progress_row = QHBoxLayout()
        progress_row.setSpacing(14)

        progress_label = QLabel("PROGRESS")
        progress_label.setObjectName("trial-stat-key")
        progress_label.setFixedWidth(88)

        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setRange(0, 25)

        progress_row.addWidget(progress_label)
        progress_row.addWidget(self.progress_bar, stretch=1)
        left.addLayout(progress_row)

        response_card, response_layout = self._make_section_card(
            "RESPONSE"
        )
        response_layout.setSpacing(10)

        self.correct_button = QPushButton("✓  Correct")
        self.correct_button.setObjectName("resp-correct")
        self.correct_button.setCursor(Qt.PointingHandCursor)
        self.correct_button.clicked.connect(
            lambda: self.submit_response("Correct")
        )

        self.incorrect_button = QPushButton("✗  Incorrect")
        self.incorrect_button.setObjectName("resp-incorrect")
        self.incorrect_button.setCursor(Qt.PointingHandCursor)
        self.incorrect_button.clicked.connect(
            lambda: self.submit_response("Incorrect")
        )

        response_layout.addWidget(self.correct_button)
        response_layout.addWidget(self.incorrect_button)

        right = QVBoxLayout()
        right.addWidget(response_card, stretch=1)

        body.addLayout(left, stretch=3)
        body.addLayout(right, stretch=2)

        outer.addLayout(body, stretch=1)
        self.pages.addWidget(self.trial_page)

    def start_experiment(self):
        subject = self.subject_input.text().strip()
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", subject):
            QMessageBox.warning(
                self,
                "Invalid Subject ID",
                "Use letters, numbers, underscores, or hyphens "
                "in the Subject ID.",
            )
            return

        failures = [
            message
            for level, message in preflight.run_checks(
                check_audio=False
            )
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
        self.list_number = int(self.list_spin.value())
        self.ear = int(self.ear_combo.currentData())

        poorest_snr = float(self.poorest_snr_input.value())
        step_db = float(self.snr_step_input.value())

        try:
            self.current_snr_levels = matlab_progressive_snr_levels(
                poorest_snr,
                step_db,
            )
            self.current_snr = self.current_snr_levels[0]

            self.builder = StimulusBuilder()
            if not 1 <= self.list_number <= self.builder.n_lists:
                raise ValueError(
                    "List number must be between 1 and %d."
                    % self.builder.n_lists
                )

            self.engine = AudioEngine()
            self.noise, _ = sf.read(
                paths.NOISE_FILE,
                dtype="float32",
            )
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

            self.apple_trials = set(
                random.sample(range(1, 25), 6)
            )
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
            QMessageBox.critical(
                self,
                "Cannot start",
                str(exc),
            )

    def _set_noise_for_snr(self, snr):
        """
        Keep the current noise waveform and phase while applying the
        existing collection calibration at the new SNR level.
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
            "%d / 25" % (self.trial_index + 1)
        )
        self.snr_info.setText(
            "%+.1f dB" % self.current_snr
        )
        self.progress_bar.setValue(self.trial_index + 1)
        self.word_label.setText(word.upper())

        self.correct_button.setEnabled(True)
        self.incorrect_button.setEnabled(True)

        audio, fs = _read_mono(
            os.path.join(paths.WORD_DIR, word + ".wav")
        )
        audio = _resample(
            audio,
            fs,
            self.engine.samplerate,
        )
        audio = scale_to_system_calibration(
            audio,
            TARGET_SPL_WORD,
        )

        # MATLAB ProgressiveSNRtest.m uses 6103 leading zero samples.
        word_audio = np.concatenate(
            [
                np.zeros(6103, dtype=np.float32),
                audio.astype(np.float32),
            ]
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
                "SNR": paths.matlab_num2str(self.current_snr),
                "Timestamp": "",
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
            self._set_noise_for_snr(
                self.current_snr_levels[next_group]
            )

        self.start_next_trial()

    def finish_list(self):
        self._stop_audio()

        try:
            os.makedirs(
                os.path.dirname(self.output_csv),
                exist_ok=True,
            )

            needs_header = (
                not os.path.exists(self.output_csv)
                or os.path.getsize(self.output_csv) == 0
            )

            # MATLAB writes the rows after the list is finished, so the
            # rows from this list share one save-time timestamp.
            list_timestamp = datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            for row in self.responses:
                row["Timestamp"] = list_timestamp

            with open(
                self.output_csv,
                "a",
                newline="",
                encoding="utf-8",
            ) as file:
                writer = csv.DictWriter(
                    file,
                    fieldnames=CSV_FIELDS,
                )
                if needs_header:
                    writer.writeheader()
                writer.writerows(self.responses)

        except OSError as exc:
            QMessageBox.critical(
                self,
                "Could not save list",
                "The list could not be written to the configured "
                "data folder:\n\n%s\n\n%s"
                % (self.output_csv, exc),
            )
            return

        estimate_path = os.path.join(
            os.path.dirname(self.output_csv),
            "%s_SNR_Estimates.csv" % self.subject_id,
        )

        try:
            write_snr_estimates(
                self.output_csv,
                estimate_path,
            )
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

        QMessageBox.information(
            self,
            "List Saved",
            message,
        )

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
    window.showFullScreen()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
