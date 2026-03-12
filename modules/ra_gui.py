from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QLineEdit,
    QVBoxLayout, QHBoxLayout, QSpinBox, QDoubleSpinBox,
    QMessageBox, QStackedLayout, QFrame, QProgressBar,
    QRadioButton, QButtonGroup, QSizePolicy
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

# ─────────────────────────────────────────────────────────────────────────────
# Blush & Berry palette
#
#  Page bg       : #FFF0F3  (blush white)
#  Card bg       : #FFFFFF
#  Card border   : #F48FB1  (blush rose)
#  Header        : #AD1457 → #E91E63 → #F06292  (berry → raspberry → blush)
#  Accent bar    : #E91E63 → #F48FB1 → #FCE4EC
#  Primary btn   : #C2185B → #E91E63
#  Text primary  : #3B0A1A  (deep berry-brown)
#  Text muted    : #AD5070  (muted rose)
#  Word display  : #C2185B  (rich berry)
#  Trial counter : #E91E63  (raspberry)
#  SNR label     : #AD1457  (deep berry)
#  Progress bar  : #E91E63 → #F48FB1
# ─────────────────────────────────────────────────────────────────────────────
GLOBAL_STYLE = """
    QWidget {
        background-color: #FFF0F3;
        color: #3B0A1A;
        font-family: "Segoe UI", "SF Pro Display", Arial, sans-serif;
        font-size: 13px;
    }

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

    QLabel#header-title {
        font-size: 17px; font-weight: bold; color: #FFFFFF; letter-spacing: 1px;
    }

    QLabel#header-badge {
        font-size: 10px; color: #FCE4EC; letter-spacing: 2px;
        padding: 3px 10px; border: 1px solid #F48FB1; border-radius: 4px;
        background-color: rgba(255,255,255,0.12);
    }

    QLabel#breadcrumb {
        font-size: 11px; color: rgba(252,228,236,0.75); letter-spacing: 1px;
    }

    QFrame#section-card {
        background-color: #FFFFFF;
        border: 1px solid #F8BBD0;
        border-radius: 14px;
    }

    QLabel#section-label {
        font-size: 10px; font-weight: bold;
        color: #C2185B; letter-spacing: 3px;
    }

    QFrame#h-divider {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 #E91E63, stop:0.6 #F48FB1, stop:1 #FCE4EC);
        min-height: 2px; max-height: 2px;
    }

    QLabel#field-label {
        font-size: 11px; color: #AD5070;
        letter-spacing: 1px; font-weight: bold;
    }

    QLineEdit, QSpinBox, QDoubleSpinBox {
        background-color: #FFF5F7;
        border: 2px solid #F48FB1;
        border-radius: 8px; padding: 10px 14px;
        color: #3B0A1A; font-size: 14px; font-weight: bold;
        selection-background-color: #E91E63; min-height: 42px;
    }

    QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {
        border: 2px solid #E91E63; background-color: #FFF0F5;
    }

    QLineEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover {
        border: 2px solid #C2185B;
    }

    QSpinBox::up-button, QDoubleSpinBox::up-button,
    QSpinBox::down-button, QDoubleSpinBox::down-button {
        background-color: #FCE4EC; border: none; width: 22px; border-radius: 4px;
    }

    QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
    QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {
        background-color: #F48FB1;
    }

    QRadioButton {
        color: #3B0A1A; font-size: 13px; font-weight: bold; spacing: 10px;
    }

    QRadioButton::indicator {
        width: 20px; height: 20px; border-radius: 10px;
        border: 2px solid #F48FB1; background-color: #FFF5F7;
    }

    QRadioButton::indicator:hover  { border: 2px solid #E91E63; }
    QRadioButton::indicator:checked {
        border: 2px solid #C2185B; background-color: #E91E63;
    }
    QRadioButton:checked { color: #C2185B; }

    QPushButton#start-btn {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 #AD1457, stop:1 #E91E63);
        color: #FFFFFF; border: none; border-radius: 12px;
        font-size: 15px; font-weight: bold; letter-spacing: 2px;
        min-height: 56px; min-width: 280px; padding: 0 48px;
    }

    QPushButton#start-btn:hover {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 #C2185B, stop:1 #F06292);
    }

    QPushButton#start-btn:pressed { background-color: #880E4F; }

    QLabel#trial-stat-key {
        font-size: 10px; color: #AD5070; letter-spacing: 2px; font-weight: bold;
    }

    QLabel#trial-stat-val {
        font-size: 24px; font-weight: bold; color: #E91E63;
    }

    QLabel#snr-stat-val {
        font-size: 24px; font-weight: bold; color: #AD1457;
    }

    QFrame#word-card {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
            stop:0 #FFFFFF, stop:1 #FFF0F3);
        border: 2px solid #F48FB1; border-radius: 18px;
    }

    QProgressBar {
        background-color: #FCE4EC; border: none;
        border-radius: 6px; min-height: 10px; max-height: 10px;
    }

    QProgressBar::chunk {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 #C2185B, stop:0.5 #E91E63, stop:1 #F48FB1);
        border-radius: 6px;
    }

    QPushButton#resp-correct {
        background-color: #F1F8E9; color: #33691E;
        border: 2px solid #AED581; border-radius: 10px;
        font-size: 14px; font-weight: bold; letter-spacing: 1px; min-height: 64px;
    }

    QPushButton#resp-correct:hover {
        background-color: #DCEDC8; border-color: #558B2F; color: #1B5E20;
    }

    QPushButton#resp-incorrect {
        background-color: #FCE4EC; color: #880E4F;
        border: 2px solid #F48FB1; border-radius: 10px;
        font-size: 14px; font-weight: bold; letter-spacing: 1px; min-height: 64px;
    }

    QPushButton#resp-incorrect:hover {
        background-color: #F8BBD0; border-color: #C2185B; color: #880E4F;
    }

    QPushButton#resp-no-response {
        background-color: #FFF8F9; color: #AD5070;
        border: 2px solid #F8BBD0; border-radius: 10px;
        font-size: 14px; font-weight: bold; letter-spacing: 1px; min-height: 64px;
    }

    QPushButton#resp-no-response:hover {
        background-color: #FCE4EC; border-color: #F48FB1; color: #880E4F;
    }

    QPushButton#resp-not-sure {
        background-color: #F3E5F5; color: #6A1B9A;
        border: 2px solid #CE93D8; border-radius: 10px;
        font-size: 14px; font-weight: bold; letter-spacing: 1px; min-height: 64px;
    }

    QPushButton#resp-not-sure:hover {
        background-color: #E1BEE7; border-color: #8E24AA; color: #4A148C;
    }

    QPushButton#action-primary {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 #AD1457, stop:1 #E91E63);
        color: #FFFFFF; border: none; border-radius: 10px;
        font-size: 13px; font-weight: bold; letter-spacing: 1px; min-height: 50px;
    }

    QPushButton#action-primary:hover {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 #C2185B, stop:1 #F06292);
    }

    QPushButton#action-danger {
        background-color: #FFF8F9; color: #880E4F;
        border: 2px solid #F48FB1; border-radius: 10px;
        font-size: 13px; font-weight: bold; letter-spacing: 1px; min-height: 50px;
    }

    QPushButton#action-danger:hover {
        background-color: #FCE4EC; border-color: #C2185B; color: #880E4F;
    }
"""


class RAWindow(QWidget):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("DistVRT — Research Assistant")
        self.resize(1440, 900); self.setMinimumSize(1100, 720)
        self.setStyleSheet(GLOBAL_STYLE)
        self.controller = None
        self.stacked_layout = QStackedLayout()
        self.setLayout(self.stacked_layout)
        self._build_setup_ui()
        self._build_trial_ui()
        self.show_setup_mode()

    def _make_header(self, screen_name):
        wrapper = QWidget()
        wl = QVBoxLayout(wrapper); wl.setContentsMargins(0,0,0,0); wl.setSpacing(0)
        accent = QFrame(); accent.setObjectName("accent-bar"); wl.addWidget(accent)
        bar = QFrame(); bar.setObjectName("header-bar")
        bl = QHBoxLayout(bar); bl.setContentsMargins(36,0,36,0); bl.setSpacing(16)
        title = QLabel("DistVRT"); title.setObjectName("header-title")
        sep = QLabel("·"); sep.setStyleSheet("color: rgba(255,182,193,0.4); font-size: 18px;")
        bc = QLabel(screen_name.upper()); bc.setObjectName("breadcrumb")
        badge = QLabel("● ACTIVE"); badge.setObjectName("header-badge")
        bl.addWidget(title); bl.addWidget(sep); bl.addWidget(bc); bl.addStretch(); bl.addWidget(badge)
        wl.addWidget(bar)
        return wrapper

    def _make_section_card(self, label_text):
        card = QFrame(); card.setObjectName("section-card")
        cl = QVBoxLayout(card); cl.setContentsMargins(28,22,28,26); cl.setSpacing(18)
        lbl = QLabel(label_text); lbl.setObjectName("section-label"); cl.addWidget(lbl)
        div = QFrame(); div.setObjectName("h-divider"); cl.addWidget(div)
        return card, cl

    def _field_row(self, label_text, widget):
        row = QHBoxLayout(); row.setSpacing(20)
        lbl = QLabel(label_text.upper()); lbl.setObjectName("field-label")
        lbl.setFixedWidth(200); lbl.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        row.addWidget(lbl); row.addWidget(widget)
        return row

    def _radio_row(self, label_text, options):
        row = QHBoxLayout(); row.setSpacing(20)
        lbl = QLabel(label_text.upper()); lbl.setObjectName("field-label")
        lbl.setFixedWidth(200); lbl.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        group = QButtonGroup()
        btn_row = QHBoxLayout(); btn_row.setSpacing(30); first = True
        for text, btn_id in options:
            rb = QRadioButton(text)
            if first: rb.setChecked(True); first = False
            group.addButton(rb, btn_id); btn_row.addWidget(rb)
        btn_row.addStretch()
        row.addWidget(lbl); row.addLayout(btn_row)
        return row, group

    def _build_setup_ui(self):
        page = QWidget()
        outer = QVBoxLayout(page); outer.setContentsMargins(0,0,0,0); outer.setSpacing(0)
        outer.addWidget(self._make_header("Session Setup"))
        content = QVBoxLayout(); content.setContentsMargins(48,36,48,36); content.setSpacing(20)

        cc, cl = self._make_section_card("SESSION CONSTANTS")
        self.subject_input = QLineEdit(); self.subject_input.setPlaceholderText("e.g.  P001")
        cl.addLayout(self._field_row("Subject ID", self.subject_input))
        self.visit_spin = QSpinBox(); self.visit_spin.setMinimum(1); self.visit_spin.setMaximum(99)
        cl.addLayout(self._field_row("Visit Number", self.visit_spin))
        ear_row, self.ear_group = self._radio_row("Target Ear", [("Left Ear",1),("Right Ear",2)])
        cl.addLayout(ear_row); content.addWidget(cc)

        dc, dl = self._make_section_card("SESSION DETAILS")
        self.run_spin = QSpinBox(); self.run_spin.setMinimum(0); self.run_spin.setMaximum(99)
        dl.addLayout(self._field_row("Run Number", self.run_spin))
        self.list_spin = QSpinBox(); self.list_spin.setMinimum(1); self.list_spin.setMaximum(99)
        dl.addLayout(self._field_row("List Number", self.list_spin))
        self.snr_spin = QDoubleSpinBox()
        self.snr_spin.setRange(-30.0,30.0); self.snr_spin.setDecimals(1)
        self.snr_spin.setSingleStep(0.5); self.snr_spin.setSuffix("  dB")
        dl.addLayout(self._field_row("SNR", self.snr_spin))
        dist_row, self.dist_group = self._radio_row("Distractor Condition",[("No",0),("Yes",1)])
        dl.addLayout(dist_row); content.addWidget(dc)

        content.addSpacing(8)
        self.start_button = QPushButton("START SESSION  ▶")
        self.start_button.setObjectName("start-btn"); self.start_button.setCursor(Qt.PointingHandCursor)
        content.addWidget(self.start_button, alignment=Qt.AlignLeft)
        outer.addLayout(content); outer.addStretch()
        self.setup_widget = page; self.stacked_layout.addWidget(page)

    def _build_trial_ui(self):
        page = QWidget()
        outer = QVBoxLayout(page); outer.setContentsMargins(0,0,0,0); outer.setSpacing(0)
        outer.addWidget(self._make_header("Experiment Control"))
        body = QHBoxLayout(); body.setContentsMargins(48,36,48,36); body.setSpacing(32)

        left = QVBoxLayout(); left.setSpacing(20)
        stat_row = QHBoxLayout(); stat_row.setSpacing(0)
        for attr_name, lbl_txt, obj_name in [
            ("trial_label","TRIAL","trial-stat-val"),
            (None,None,None),
            ("snr_label","SNR","snr-stat-val"),
        ]:
            if attr_name is None: stat_row.addStretch(); continue
            col = QVBoxLayout(); col.setSpacing(4)
            k = QLabel(lbl_txt); k.setObjectName("trial-stat-key")
            v = QLabel("—"); v.setObjectName(obj_name); v.setFont(QFont("Segoe UI",22,QFont.Bold))
            setattr(self, attr_name, v); col.addWidget(k); col.addWidget(v)
            stat_row.addLayout(col)
        left.addLayout(stat_row)

        wc = QFrame(); wc.setObjectName("word-card")
        wc.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        wcl = QVBoxLayout(wc); wcl.setAlignment(Qt.AlignCenter)
        self.target_word_label = QLabel("—")
        self.target_word_label.setAlignment(Qt.AlignCenter)
        self.target_word_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.target_word_label.setStyleSheet("""
            color: #C2185B;
            font-size: 160px;
            font-weight: 900;
            letter-spacing: 6px;
        """)
        wcl.addWidget(self.target_word_label)
        left.addWidget(wc, stretch=1)

        pr = QHBoxLayout()
        pl = QLabel("PROGRESS"); pl.setObjectName("trial-stat-key"); pl.setFixedWidth(90)
        self.progress_bar = QProgressBar(); self.progress_bar.setTextVisible(False)
        pr.addWidget(pl); pr.addWidget(self.progress_bar); left.addLayout(pr)

        right = QVBoxLayout(); right.setSpacing(12)
        rc, rl = self._make_section_card("RESPONSE"); rl.setSpacing(12)
        self.correct_btn     = QPushButton("✓  Correct");     self.correct_btn.setObjectName("resp-correct")
        self.incorrect_btn   = QPushButton("✗  Incorrect");   self.incorrect_btn.setObjectName("resp-incorrect")
        self.no_response_btn = QPushButton("—  No Response"); self.no_response_btn.setObjectName("resp-no-response")
        self.not_sure_btn    = QPushButton("?  Not Sure");    self.not_sure_btn.setObjectName("resp-not-sure")
        for btn in [self.correct_btn,self.incorrect_btn,self.no_response_btn,self.not_sure_btn]:
            btn.setCursor(Qt.PointingHandCursor); rl.addWidget(btn)
        right.addWidget(rc, stretch=1)

        ac, al = self._make_section_card("SESSION ACTIONS"); al.setSpacing(10)
        self.next_list_btn = QPushButton("Next List  →"); self.next_list_btn.setObjectName("action-primary")
        self.next_list_btn.setCursor(Qt.PointingHandCursor); self.next_list_btn.setVisible(False)
        self.end_testing_btn = QPushButton("End Testing"); self.end_testing_btn.setObjectName("action-danger")
        self.end_testing_btn.setCursor(Qt.PointingHandCursor); self.end_testing_btn.setVisible(False)
        al.addWidget(self.next_list_btn); al.addWidget(self.end_testing_btn); right.addWidget(ac)

        body.addLayout(left, stretch=3); body.addLayout(right, stretch=2)
        outer.addLayout(body, stretch=1)
        self.trial_widget = page; self.stacked_layout.addWidget(page)

    def show_setup_mode(self): self.stacked_layout.setCurrentWidget(self.setup_widget)
    def show_trial_mode(self):  self.stacked_layout.setCurrentWidget(self.trial_widget)

    def get_setup_data(self):
        if not self.subject_input.text().strip():
            msg = QMessageBox(self)
            msg.setWindowTitle("Validation Error")
            msg.setText("Subject ID is required before starting the session.")
            msg.setIcon(QMessageBox.Warning)
            msg.setStyleSheet("""
                QMessageBox { background-color: #FFF0F3; color: #3B0A1A; }
                QLabel { color: #3B0A1A; font-size: 13px; }
                QPushButton {
                    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #AD1457,stop:1 #E91E63);
                    color: white; border-radius: 6px; padding: 8px 24px; font-weight: bold; border: none;
                }
            """)
            msg.exec(); return None
        return {
            "subject_id":  self.subject_input.text().strip(),
            "visit":       self.visit_spin.value(),
            "run":         self.run_spin.value(),
            "list_number": self.list_spin.value(),
            "snr":         self.snr_spin.value(),
            "target_ear":  self.ear_group.checkedId(),
            "dist_cond":   self.dist_group.checkedId(),
        }

    def update_trial_info(self, trial_number, total_trials, snr):
        self.trial_label.setText(f"{trial_number}  /  {total_trials}")
        self.snr_label.setText(f"{snr:+.1f} dB")
        self.progress_bar.setMaximum(total_trials)
        self.progress_bar.setValue(trial_number)

    def update_target_word(self, word):
        self.target_word_label.setText(word.upper())

    def show_session_complete(self):
        self.trial_label.setText("DONE"); self.snr_label.setText("—")
        self.target_word_label.setText("SESSION\nCOMPLETE")
        self.target_word_label.setStyleSheet("""
            color: #AD1457; font-size: 80px; font-weight: 900; letter-spacing: 2px;
        """)