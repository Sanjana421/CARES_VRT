# PySide6 widgets are the building blocks of the GUI.
# This set is similar to assembling a MATLAB App Designer interface using
# containers, text labels, inputs, buttons, and layouts.
from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QLineEdit,
    QVBoxLayout, QHBoxLayout, QSpinBox, QDoubleSpinBox,
    QMessageBox, QStackedLayout, QFrame, QProgressBar,
    QRadioButton, QButtonGroup, QSizePolicy, QScrollArea
)

# Qt core tools used for alignment, styling flags, and widget behavior.
from PySide6.QtCore import Qt

# QFont controls text appearance such as size, weight, and family.
from PySide6.QtGui import QFont


# Global stylesheet for the research assistant interface.
#
# Notes for MATLAB users:
# - This is similar to defining a consistent UIFigure/App style once and
#   applying it to all controls.
# - Object names such as QFrame#header-bar target specific widgets by name,
#   similar to styling specific UI components rather than all components.
# - Transparent defaults are important here because Qt otherwise lets many
#   child widgets inherit solid background fills that can cover labels.
GLOBAL_STYLE = """
/* ── Transparent-by-default: prevents text/background overlap issues ─────── */
QWidget      { background-color: transparent; color: #2D0A14;
               font-family: "Segoe UI", "SF Pro Display", Arial, sans-serif; }
QLabel       { background-color: transparent; }
QFrame       { background-color: transparent; }
QRadioButton { background-color: transparent; }

/* ── Named root page backgrounds ─────────────────────────────────────────── */
QWidget#page-bg { background-color: #FFF0F3; }

/* ── Header bar ──────────────────────────────────────────────────────────── */
QFrame#header-bar {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #880E4F, stop:0.5 #C2185B, stop:1 #AD1457);
    min-height: 58px; max-height: 58px;
}

QFrame#accent-bar {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #E91E63, stop:0.5 #F48FB1, stop:1 #FCE4EC);
    min-height: 4px; max-height: 4px;
}

QLabel#header-title  { font-size: 17px; font-weight: 700; color: #FFFFFF; letter-spacing: 1px; }
QLabel#breadcrumb    { font-size: 11px; color: rgba(252,228,236,0.78); letter-spacing: 1px; }
QLabel#header-badge  {
    font-size: 10px; color: #FCE4EC; letter-spacing: 2px;
    padding: 4px 10px; border: 1px solid rgba(255,182,193,0.5);
    border-radius: 5px; background-color: rgba(255,255,255,0.12);
}

/* ── Section cards ───────────────────────────────────────────────────────── */
QFrame#section-card {
    background-color: #FFFFFF;
    border: 1.5px solid #F8BBD0;
    border-radius: 16px;
}

QLabel#section-label {
    font-size: 10px; font-weight: 800; color: #C2185B; letter-spacing: 3px;
}

QFrame#h-divider {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #E91E63, stop:0.6 #F48FB1, stop:1 #FCE4EC);
    min-height: 2px; max-height: 2px; border: none;
}

/* ── Field labels ────────────────────────────────────────────────────────── */
QLabel#field-label {
    font-size: 11px; color: #9C4060; letter-spacing: 1px; font-weight: 700;
}

/* ── Inputs ──────────────────────────────────────────────────────────────── */
QLineEdit, QSpinBox, QDoubleSpinBox {
    background-color: #FFF5F7;
    border: 1.5px solid #F8BBD0; border-radius: 9px;
    padding: 9px 14px; color: #2D0A14;
    font-size: 14px; font-weight: 600;
    selection-background-color: #E91E63; min-height: 40px;
}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {
    border: 1.5px solid #E91E63; background-color: #FFFAFC;
}
QLineEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover {
    border: 1.5px solid #C2185B;
}
QSpinBox::up-button, QDoubleSpinBox::up-button,
QSpinBox::down-button, QDoubleSpinBox::down-button {
    background-color: #FCE4EC; border: none; width: 24px; border-radius: 4px;
}
QSpinBox::up-button:hover,   QDoubleSpinBox::up-button:hover,
QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {
    background-color: #F48FB1;
}

/* ── Radio buttons ───────────────────────────────────────────────────────── */
QRadioButton { color: #2D0A14; font-size: 13px; font-weight: 600; spacing: 10px; }
QRadioButton::indicator {
    width: 20px; height: 20px; border-radius: 10px;
    border: 2px solid #F48FB1; background-color: #FFF5F7;
}
QRadioButton::indicator:hover   { border: 2px solid #E91E63; }
QRadioButton::indicator:checked { border: 3px solid #C2185B; background-color: #E91E63; }
QRadioButton:checked { color: #C2185B; font-weight: 700; }

/* ── Buttons ─────────────────────────────────────────────────────────────── */
QPushButton#start-btn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #AD1457, stop:1 #E91E63);
    color: #FFFFFF; border: none; border-radius: 12px;
    font-size: 15px; font-weight: 800; letter-spacing: 2px;
    min-height: 54px; min-width: 260px; padding: 0 44px;
}
QPushButton#start-btn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #C2185B, stop:1 #F06292);
}
QPushButton#start-btn:pressed { background-color: #880E4F; }

/* ── Trial stats ─────────────────────────────────────────────────────────── */
QLabel#trial-stat-key { font-size: 10px; color: #9C4060; letter-spacing: 2px; font-weight: 700; }
QLabel#trial-stat-val { font-size: 26px; font-weight: 800; color: #E91E63; }
QLabel#snr-stat-val   { font-size: 26px; font-weight: 800; color: #AD1457; }

/* ── Word card ───────────────────────────────────────────────────────────── */
QFrame#word-card {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #FFFFFF, stop:1 #FFF0F3);
    border: 1.5px solid #F8BBD0; border-radius: 20px;
}

/* ── Progress bar ────────────────────────────────────────────────────────── */
QProgressBar {
    background-color: #FCE4EC; border: none;
    border-radius: 6px; min-height: 10px; max-height: 10px;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #C2185B, stop:0.5 #E91E63, stop:1 #F48FB1);
    border-radius: 6px;
}

/* ── Response buttons ────────────────────────────────────────────────────── */
QPushButton#resp-correct {
    background-color: #F1F8E9; color: #2E7D32;
    border: 1.5px solid #A5D6A7; border-radius: 10px;
    font-size: 14px; font-weight: 700; letter-spacing: 1px; min-height: 62px;
}
QPushButton#resp-correct:hover  { background-color: #DCEDC8; border-color: #66BB6A; color: #1B5E20; }
QPushButton#resp-correct:pressed { background-color: #C5E1A5; }

QPushButton#resp-incorrect {
    background-color: #FCE4EC; color: #880E4F;
    border: 1.5px solid #F48FB1; border-radius: 10px;
    font-size: 14px; font-weight: 700; letter-spacing: 1px; min-height: 62px;
}
QPushButton#resp-incorrect:hover { background-color: #F8BBD0; border-color: #C2185B; }

QPushButton#resp-no-response {
    background-color: #FFF8F9; color: #9C4060;
    border: 1.5px solid #F8BBD0; border-radius: 10px;
    font-size: 14px; font-weight: 700; letter-spacing: 1px; min-height: 62px;
}
QPushButton#resp-no-response:hover { background-color: #FCE4EC; border-color: #F48FB1; color: #880E4F; }

QPushButton#resp-not-sure {
    background-color: #F3E5F5; color: #6A1B9A;
    border: 1.5px solid #CE93D8; border-radius: 10px;
    font-size: 14px; font-weight: 700; letter-spacing: 1px; min-height: 62px;
}
QPushButton#resp-not-sure:hover { background-color: #E1BEE7; border-color: #8E24AA; color: #4A148C; }

/* ── Action buttons ──────────────────────────────────────────────────────── */
QPushButton#action-primary {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #AD1457, stop:1 #E91E63);
    color: #FFFFFF; border: none; border-radius: 10px;
    font-size: 13px; font-weight: 700; letter-spacing: 1px; min-height: 48px;
}
QPushButton#action-primary:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #C2185B, stop:1 #F06292);
}
QPushButton#action-danger {
    background-color: #FFF8F9; color: #880E4F;
    border: 1.5px solid #F48FB1; border-radius: 10px;
    font-size: 13px; font-weight: 700; letter-spacing: 1px; min-height: 48px;
}
QPushButton#action-danger:hover { background-color: #FCE4EC; border-color: #C2185B; }

/* ── Scroll area ─────────────────────────────────────────────────────────── */
QScrollArea  { background-color: transparent; border: none; }
QScrollBar:vertical { background: #FCE4EC; width: 6px; border-radius: 3px; margin: 0; }
QScrollBar::handle:vertical { background: #F48FB1; border-radius: 3px; min-height: 20px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
"""


class RAWindow(QWidget):
    """
    Research assistant control window.

    This interface supports two main modes:
    - session setup, where the experiment parameters are entered,
    - trial control, where the current stimulus and responses are managed.
    """

    def __init__(self):
        super().__init__()

        # Window title shown in the application frame.
        self.setWindowTitle("DistVRT — Research Assistant")

        # Initial window size for desktop use.
        self.resize(1440, 900)
        self.setMinimumSize(1100, 720)

        # Apply the full visual style sheet defined above.
        self.setStyleSheet(GLOBAL_STYLE)

        # Give the root widget a named background so the page background style applies.
        self.setObjectName("page-bg")
        self.setAttribute(Qt.WA_StyledBackground, True)

        # Optional controller object can be attached by the main application.
        self.controller = None

        # Stacked layout allows switching between setup and trial pages
        # without opening a new window.
        self.stacked_layout = QStackedLayout()
        self.setLayout(self.stacked_layout)

        # Build both major pages once at startup.
        self._build_setup_ui()
        self._build_trial_ui()

        # Start in setup mode.
        self.show_setup_mode()

    # ── Helper: make header ───────────────────────────────────────────────────

    def _make_header(self, screen_name):
        # Header wrapper groups the title bar and accent strip together.
        wrapper = QWidget()
        wl = QVBoxLayout(wrapper)
        wl.setContentsMargins(0, 0, 0, 0)
        wl.setSpacing(0)

        # Main gradient bar containing the title and page label.
        bar = QFrame()
        bar.setObjectName("header-bar")
        bar.setAttribute(Qt.WA_StyledBackground, True)
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(36, 0, 36, 0)
        bl.setSpacing(14)

        title = QLabel("DistVRT")
        title.setObjectName("header-title")

        sep = QLabel("·")
        sep.setStyleSheet("color: rgba(255,182,193,0.5); font-size: 20px; font-weight: 300;")

        bc = QLabel(screen_name.upper())
        bc.setObjectName("breadcrumb")

        badge_str = "● ACTIVE" if screen_name == "Experiment Control" else "● SETUP"
        badge = QLabel(badge_str)
        badge.setObjectName("header-badge")

        bl.addWidget(title)
        bl.addWidget(sep)
        bl.addWidget(bc)
        bl.addStretch()
        bl.addWidget(badge)
        wl.addWidget(bar)

        # Thin accent strip beneath the header improves page separation.
        accent = QFrame()
        accent.setObjectName("accent-bar")
        accent.setAttribute(Qt.WA_StyledBackground, True)
        wl.addWidget(accent)

        return wrapper

    # ── Helper: make section card ─────────────────────────────────────────────

    def _make_section_card(self, label_text):
        # Standard card container used throughout the interface.
        card = QFrame()
        card.setObjectName("section-card")
        card.setAttribute(Qt.WA_StyledBackground, True)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(28, 20, 28, 24)
        cl.setSpacing(16)

        lbl = QLabel(label_text)
        lbl.setObjectName("section-label")
        cl.addWidget(lbl)

        div = QFrame()
        div.setObjectName("h-divider")
        div.setAttribute(Qt.WA_StyledBackground, True)
        cl.addWidget(div)

        return card, cl

    # ── Helper: field rows ────────────────────────────────────────────────────

    def _field_row(self, label_text, widget):
        # Standard label + input row for session configuration fields.
        row = QHBoxLayout()
        row.setSpacing(20)

        lbl = QLabel(label_text.upper())
        lbl.setObjectName("field-label")
        lbl.setFixedWidth(190)
        lbl.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)

        row.addWidget(lbl)
        row.addWidget(widget, stretch=1)
        return row

    def _radio_row(self, label_text, options):
        # Standard label + radio-button row for categorical settings.
        row = QHBoxLayout()
        row.setSpacing(20)

        lbl = QLabel(label_text.upper())
        lbl.setObjectName("field-label")
        lbl.setFixedWidth(190)
        lbl.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)

        # QButtonGroup is used to track which radio option is selected.
        group = QButtonGroup()
        btn_row = QHBoxLayout()
        btn_row.setSpacing(28)

        first = True
        for text, btn_id in options:
            rb = QRadioButton(text)
            if first:
                rb.setChecked(True)
                first = False
            group.addButton(rb, btn_id)
            btn_row.addWidget(rb)

        btn_row.addStretch()
        row.addWidget(lbl)
        row.addLayout(btn_row, stretch=1)
        return row, group

    # ── Setup page ────────────────────────────────────────────────────────────

    def _build_setup_ui(self):
        # Setup page collects all session parameters before testing begins.
        page = QWidget()
        page.setObjectName("page-bg")
        page.setAttribute(Qt.WA_StyledBackground, True)

        outer = QVBoxLayout(page)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(self._make_header("Session Setup"))

        # Scroll area keeps the setup page usable at smaller screen sizes.
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        inner = QWidget()
        inner.setObjectName("page-bg")
        inner.setAttribute(Qt.WA_StyledBackground, True)

        content = QVBoxLayout(inner)
        content.setContentsMargins(52, 36, 52, 36)
        content.setSpacing(20)

        # Card 1: session constants.
        cc, cl = self._make_section_card("SESSION CONSTANTS")

        self.subject_input = QLineEdit()
        self.subject_input.setPlaceholderText("e.g.  P001")
        cl.addLayout(self._field_row("Subject ID", self.subject_input))

        self.visit_spin = QSpinBox()
        self.visit_spin.setMinimum(1)
        self.visit_spin.setMaximum(99)
        cl.addLayout(self._field_row("Visit Number", self.visit_spin))

        ear_row, self.ear_group = self._radio_row("Target Ear", [("Left Ear", 1), ("Right Ear", 2)])
        cl.addLayout(ear_row)

        output_row, self.output_group = self._radio_row("Audio Output", [("Speakers", 0), ("Headphones", 1)])
        cl.addLayout(output_row)

        content.addWidget(cc)

        # Card 2: session details.
        dc, dl = self._make_section_card("SESSION DETAILS")

        self.run_spin = QSpinBox()
        self.run_spin.setMinimum(0)
        self.run_spin.setMaximum(99)
        dl.addLayout(self._field_row("Run Number", self.run_spin))

        self.list_spin = QSpinBox()
        self.list_spin.setMinimum(1)
        self.list_spin.setMaximum(99)
        dl.addLayout(self._field_row("List Number", self.list_spin))

        self.snr_spin = QDoubleSpinBox()
        self.snr_spin.setRange(-30.0, 30.0)
        self.snr_spin.setDecimals(1)
        self.snr_spin.setSingleStep(0.5)
        self.snr_spin.setSuffix("  dB")
        dl.addLayout(self._field_row("SNR", self.snr_spin))

        dist_row, self.dist_group = self._radio_row("Distractor Condition", [("No", 0), ("Yes", 1)])
        dl.addLayout(dist_row)

        content.addWidget(dc)

        # Session start button.
        content.addSpacing(12)
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self.start_button = QPushButton("START SESSION  ▶")
        self.start_button.setObjectName("start-btn")
        self.start_button.setCursor(Qt.PointingHandCursor)
        btn_row.addWidget(self.start_button)

        btn_row.addStretch()
        content.addLayout(btn_row)
        content.addStretch()

        scroll.setWidget(inner)
        outer.addWidget(scroll, stretch=1)

        self.setup_widget = page
        self.stacked_layout.addWidget(page)

    # ── Trial page ────────────────────────────────────────────────────────────

    def _build_trial_ui(self):
        # Trial page is used during active testing and response logging.
        page = QWidget()
        page.setObjectName("page-bg")
        page.setAttribute(Qt.WA_StyledBackground, True)

        outer = QVBoxLayout(page)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(self._make_header("Experiment Control"))

        body = QHBoxLayout()
        body.setContentsMargins(48, 32, 48, 32)
        body.setSpacing(28)

        # Left column: trial status, target word, and progress bar.
        left = QVBoxLayout()
        left.setSpacing(18)

        stat_row = QHBoxLayout()
        stat_row.setSpacing(0)

        # Create the status display using a compact loop.
        # This is similar to building repeated UI blocks in MATLAB with a helper function.
        for attr_name, lbl_txt, obj_name in [
            ("trial_label", "TRIAL", "trial-stat-val"),
            (None, None, None),
            ("snr_label", "SNR", "snr-stat-val"),
        ]:
            if attr_name is None:
                stat_row.addStretch()
                continue

            col = QVBoxLayout()
            col.setSpacing(3)

            k = QLabel(lbl_txt)
            k.setObjectName("trial-stat-key")

            v = QLabel("—")
            v.setObjectName(obj_name)
            v.setFont(QFont("Segoe UI", 22, QFont.Bold))

            setattr(self, attr_name, v)

            col.addWidget(k)
            col.addWidget(v)
            stat_row.addLayout(col)

        left.addLayout(stat_row)

        # Target word display card.
        wc = QFrame()
        wc.setObjectName("word-card")
        wc.setAttribute(Qt.WA_StyledBackground, True)
        wc.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        wcl = QVBoxLayout(wc)
        wcl.setAlignment(Qt.AlignCenter)
        wcl.setContentsMargins(28, 28, 28, 28)

        kicker = QLabel("TARGET WORD")
        kicker.setAlignment(Qt.AlignCenter)
        kicker.setStyleSheet("font-size: 10px; font-weight: 800; color: #C2185B; letter-spacing: 3px;")

        self.target_word_label = QLabel("—")
        self.target_word_label.setAlignment(Qt.AlignCenter)
        self.target_word_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.target_word_label.setWordWrap(True)
        self.target_word_label.setStyleSheet(
            "color: #C2185B; font-size: 156px; font-weight: 900; letter-spacing: 6px;"
        )

        wcl.addWidget(kicker)
        wcl.addWidget(self.target_word_label, stretch=1)
        left.addWidget(wc, stretch=1)

        # Progress bar summarizes task completion.
        pr = QHBoxLayout()
        pr.setSpacing(14)
        pl = QLabel("PROGRESS")
        pl.setObjectName("trial-stat-key")
        pl.setFixedWidth(88)

        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)

        pr.addWidget(pl)
        pr.addWidget(self.progress_bar, stretch=1)
        left.addLayout(pr)

        # Right column: participant response buttons and session controls.
        right = QVBoxLayout()
        right.setSpacing(14)

        rc, rl = self._make_section_card("RESPONSE")
        rl.setSpacing(10)

        self.correct_btn = QPushButton("✓  Correct")
        self.correct_btn.setObjectName("resp-correct")

        self.incorrect_btn = QPushButton("✗  Incorrect")
        self.incorrect_btn.setObjectName("resp-incorrect")

        self.no_response_btn = QPushButton("—  No Response")
        self.no_response_btn.setObjectName("resp-no-response")

        self.not_sure_btn = QPushButton("?  Not Sure")
        self.not_sure_btn.setObjectName("resp-not-sure")

        for btn in [self.correct_btn, self.incorrect_btn, self.no_response_btn, self.not_sure_btn]:
            btn.setCursor(Qt.PointingHandCursor)
            rl.addWidget(btn)

        right.addWidget(rc, stretch=1)

        ac, al = self._make_section_card("SESSION ACTIONS")
        al.setSpacing(10)

        self.next_list_btn = QPushButton("Next List  →")
        self.next_list_btn.setObjectName("action-primary")
        self.next_list_btn.setCursor(Qt.PointingHandCursor)
        self.next_list_btn.setVisible(False)

        self.end_testing_btn = QPushButton("End Testing")
        self.end_testing_btn.setObjectName("action-danger")
        self.end_testing_btn.setCursor(Qt.PointingHandCursor)
        self.end_testing_btn.setVisible(False)

        al.addWidget(self.next_list_btn)
        al.addWidget(self.end_testing_btn)

        right.addWidget(ac)
        right.addStretch()

        body.addLayout(left, stretch=3)
        body.addLayout(right, stretch=2)
        outer.addLayout(body, stretch=1)

        self.trial_widget = page
        self.stacked_layout.addWidget(page)

    # ── Public API ────────────────────────────────────────────────────────────

    def show_setup_mode(self):
        # Switch to the setup screen.
        self.stacked_layout.setCurrentWidget(self.setup_widget)

    def show_trial_mode(self):
        # Switch to the active trial screen.
        self.stacked_layout.setCurrentWidget(self.trial_widget)

    def show_action_buttons(self, next_list=True, end_testing=True):
        # Controls whether end-of-session actions are visible.
        self.next_list_btn.setVisible(next_list)
        self.end_testing_btn.setVisible(end_testing)

    def hide_action_buttons(self):
        # Hide session action buttons when they are not needed.
        self.next_list_btn.setVisible(False)
        self.end_testing_btn.setVisible(False)

    def get_setup_data(self):
        # Validate that a subject ID has been entered before starting the session.
        subject = self.subject_input.text().strip()
        if not subject:
            msg = QMessageBox(self)
            msg.setWindowTitle("Validation Error")
            msg.setText("Subject ID is required before starting the session.")
            msg.setIcon(QMessageBox.Warning)
            msg.setStyleSheet("""
                QMessageBox { background-color: #FFF0F3; }
                QLabel { color: #2D0A14; font-size: 13px; }
                QPushButton {
                    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                        stop:0 #AD1457,stop:1 #E91E63);
                    color: white; border-radius: 7px;
                    padding: 8px 24px; font-weight: bold; border: none;
                }
            """)
            msg.exec()
            return None

        # Package setup fields in a plain dictionary for downstream use.
        # This is similar to creating a MATLAB struct of session parameters.
        return {
            "subject_id": subject,
            "visit": self.visit_spin.value(),
            "run": self.run_spin.value(),
            "list_number": self.list_spin.value(),
            "snr": self.snr_spin.value(),
            "target_ear": self.ear_group.checkedId(),
            "dist_cond": self.dist_group.checkedId(),
            "output_mode": "headphones" if self.output_group.checkedId() == 1 else "speakers",
        }

    def update_trial_info(self, trial_number, total_trials, snr):
        # Refresh the trial counter, SNR display, and progress bar position.
        self.trial_label.setText(f"{trial_number}  /  {total_trials}")
        self.snr_label.setText(f"{snr:+.1f} dB")
        self.progress_bar.setMaximum(total_trials)
        self.progress_bar.setValue(trial_number)

    def update_target_word(self, word):
        # Show the current target word in a large, high-visibility format.
        self.target_word_label.setText(word.upper())

    def show_session_complete(self):
        # Update the screen to reflect that the session has ended.
        self.trial_label.setText("DONE")
        self.snr_label.setText("—")
        self.target_word_label.setText("SESSION\nCOMPLETE")
        self.target_word_label.setStyleSheet(
            "color: #AD1457; font-size: 72px; font-weight: 900; letter-spacing: 2px;"
        )
        self.show_action_buttons(next_list=True, end_testing=True)
