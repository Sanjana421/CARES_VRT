import os
import math
import random

from PySide6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout, QSlider,
    QPushButton, QApplication, QStackedLayout, QFrame, QSizePolicy
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPainter, QPen, QColor, QFont, QPixmap, QBrush, QLinearGradient

BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
ASSETS_DIR   = os.path.join(PROJECT_ROOT, "assets")

# ─────────────────────────────────────────────────────────────────────────────
#  Same transparent-by-default pattern as ra_gui.py:
#  QLabel / QFrame inherit background-color from QWidget unless we explicitly
#  set transparent.  Named page widgets get their solid background via
#  WA_StyledBackground so only they paint solid fills.
# ─────────────────────────────────────────────────────────────────────────────
CHILD_STYLE = """
/* Transparent defaults */
QWidget      { background-color: transparent; color: #2D0A14;
               font-family: "Segoe UI", Arial, sans-serif; font-size: 14px; }
QLabel       { background-color: transparent; }
QFrame       { background-color: transparent; }

/* Named page backgrounds */
QWidget#child-page { background-color: #FFF0F3; }

/* ── Waiting ─────────────────────────────────────────────────────────────── */
QLabel#waiting-title { font-size: 60px; font-weight: bold; color: #C2185B; letter-spacing: -1px; }
QLabel#waiting-sub   { font-size: 24px; color: #E91E63; letter-spacing: 1px; font-weight: bold; }

/* ── Great Job ───────────────────────────────────────────────────────────── */
QLabel#great-job-title { font-size: 84px; font-weight: bold; color: #AD1457; letter-spacing: -2px; }
QLabel#great-job-sub   { font-size: 30px; color: #E91E63; font-weight: bold; }

/* ── Questionnaire ───────────────────────────────────────────────────────── */
QLabel#question-text { font-size: 42px; font-weight: bold; color: #2D0A14; letter-spacing: -1px; }

/* anchor-label sits inside a WHITE card — must use dark ink, not BEIGE */
QLabel#anchor-label  { font-size: 18px; font-weight: bold; color: #AD1457; }

QFrame#q-card {
    background-color: #FFFFFF;
    border: 2px solid #F8BBD0;
    border-radius: 22px;
}

QPushButton#next-btn {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #AD1457, stop:1 #E91E63);
    color: #FFFFFF; border: none; border-radius: 14px;
    font-size: 22px; font-weight: bold; letter-spacing: 2px;
    min-height: 68px; min-width: 260px; padding: 0 44px;
}
QPushButton#next-btn:hover {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #C2185B, stop:1 #F06292);
}
QPushButton#next-btn:pressed { background-color: #880E4F; }

/* ── Ready ───────────────────────────────────────────────────────────────── */
QLabel#ready-title { font-size: 58px; font-weight: bold; color: #C2185B; letter-spacing: -1px; }
QLabel#ready-sub   { font-size: 24px; color: #E91E63; font-weight: bold; letter-spacing: 1px; }

QPushButton#ready-btn {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #880E4F, stop:0.5 #C2185B, stop:1 #E91E63);
    color: #FFFFFF; border: none; border-radius: 20px;
    font-size: 30px; font-weight: bold; letter-spacing: 3px;
    min-height: 108px; min-width: 420px; padding: 0 64px;
}
QPushButton#ready-btn:hover {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #AD1457, stop:0.5 #E91E63, stop:1 #F06292);
}
QPushButton#ready-btn:pressed { background-color: #880E4F; }

/* ── Goodbye ─────────────────────────────────────────────────────────────── */
QLabel#goodbye-emoji { font-size: 90px; }
QLabel#goodbye-title { font-size: 76px; font-weight: bold; color: #AD1457; letter-spacing: -2px; }
QLabel#goodbye-sub   { font-size: 28px; color: #E91E63; font-weight: bold; }

QLabel#funfact-label { font-size: 12px; color: #C2185B; letter-spacing: 3px; font-weight: bold; }

QLabel#funfact-box {
    font-size: 22px; color: #2D0A14;
    background-color: #FCE4EC;
    border: 2px solid #F48FB1;
    border-radius: 18px;
    padding: 28px 44px;
}
"""


class _ProgressRingWidget(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.total_trials     = 25
        self.display_progress = 0.0
        self.countdown_text   = ""
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()

        grad = QLinearGradient(0, 0, w, h)
        grad.setColorAt(0.0, QColor(255, 240, 243))
        grad.setColorAt(1.0, QColor(252, 228, 236))
        painter.fillRect(self.rect(), QBrush(grad))

        size  = min(w, h) - 140
        x     = (w - size) / 2
        y     = (h - size) / 2
        ring_w = max(28, int(size * 0.065))

        # Track
        pen_bg = QPen(QColor(248, 187, 208, 180))
        pen_bg.setWidth(ring_w); pen_bg.setCapStyle(Qt.RoundCap)
        painter.setPen(pen_bg)
        painter.drawEllipse(int(x), int(y), int(size), int(size))

        # Progress arc
        ratio = self.display_progress / self.total_trials if self.total_trials else 0
        pen_prog = QPen(QColor(194, 24, 91))
        pen_prog.setWidth(ring_w); pen_prog.setCapStyle(Qt.RoundCap)
        painter.setPen(pen_prog)
        painter.drawArc(int(x), int(y), int(size), int(size),
                        90 * 16, -int(ratio * 360 * 16))

        # Dot at arc tip
        if ratio > 0.01:
            angle_rad = math.radians(90 - ratio * 360)
            r = size / 2
            cx2 = x + r + r * math.cos(angle_rad)
            cy2 = y + r - r * math.sin(angle_rad)
            dot_r = ring_w // 2 + 4
            painter.setBrush(QBrush(QColor(233, 30, 99, 240)))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(int(cx2 - dot_r), int(cy2 - dot_r), dot_r * 2, dot_r * 2)

        # Countdown overlay
        if self.countdown_text:
            m = int(size * 0.18)
            painter.setBrush(QBrush(QColor(255, 240, 245, 225)))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(int(x + m), int(y + m), int(size - 2 * m), int(size - 2 * m))
            painter.setPen(QColor(173, 20, 87))
            fs = int(size * 0.22) if self.countdown_text != "GO!" else int(size * 0.15)
            painter.setFont(QFont("Segoe UI", fs, QFont.Bold))
            painter.drawText(self.rect(), Qt.AlignCenter, self.countdown_text)


class ChildWindow(QWidget):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Listening Task")
        self.setStyleSheet(CHILD_STYLE)
        self.total_trials     = 25
        self.current_progress = 0
        self.display_progress = 0.0
        self.countdown_text   = ""
        self.stacked_layout   = QStackedLayout()
        self.setLayout(self.stacked_layout)

        self._build_progress_page()
        self._build_great_job_page()
        self._build_ready_page()
        self._build_questionnaire_page()
        self._build_waiting_page()
        self._build_goodbye_page()

        self.stacked_layout.setCurrentWidget(self.progress_page)

        screens = QApplication.screens()
        geo = screens[1].availableGeometry() if len(screens) > 1 else screens[0].availableGeometry()
        self.setGeometry(geo)
        self.show()

    # ── Progress ring page ────────────────────────────────────────────────────

    def _build_progress_page(self):
        self._ring = _ProgressRingWidget()
        self.progress_page = self._ring
        self.stacked_layout.addWidget(self._ring)

    def update_progress(self, trial_number, total_trials):
        self.total_trials     = total_trials
        self.current_progress = trial_number
        self._ring.total_trials = total_trials
        self._animate_progress()

    def _animate_progress(self):
        steps  = 20
        target = float(self.current_progress)
        diff   = target - self.display_progress
        sv     = diff / steps if steps else 0

        def go():
            nonlocal steps
            if steps <= 0:
                self.display_progress    = target
                self._ring.display_progress = target
                self._ring.update()
                return
            self.display_progress       += sv
            self._ring.display_progress  = self.display_progress
            self._ring.update()
            steps -= 1
            QTimer.singleShot(22, go)

        go()

    def show_prepare_sequence(self, on_complete):
        self.sequence = ["3", "2", "1", "GO!"]
        self.index = 0
        self.countdown_complete_callback = on_complete
        self._next_countdown_step()

    def _next_countdown_step(self):
        if self.index >= len(self.sequence):
            self.countdown_text       = ""
            self._ring.countdown_text = ""
            self._ring.update()
            self.countdown_complete_callback()
            return
        self.countdown_text       = self.sequence[self.index]
        self._ring.countdown_text = self.countdown_text
        self.index += 1
        self._ring.update()
        QTimer.singleShot(1000, self._next_countdown_step)

    # ── Great Job page ────────────────────────────────────────────────────────

    def _build_great_job_page(self):
        self.great_job_page = QWidget()
        self.great_job_page.setObjectName("child-page")
        self.great_job_page.setAttribute(Qt.WA_StyledBackground, True)

        l = QVBoxLayout(self.great_job_page)
        l.setAlignment(Qt.AlignCenter); l.setSpacing(24)

        stars = QLabel("★  ★  ★")
        stars.setAlignment(Qt.AlignCenter)
        stars.setStyleSheet("font-size: 56px; color: #E91E63; letter-spacing: 14px;")

        title = QLabel("Great Job!")
        title.setObjectName("great-job-title"); title.setAlignment(Qt.AlignCenter)

        sub = QLabel("You're doing amazing — keep it up!")
        sub.setObjectName("great-job-sub"); sub.setAlignment(Qt.AlignCenter)

        l.addWidget(stars); l.addWidget(title); l.addWidget(sub)
        self.stacked_layout.addWidget(self.great_job_page)

    def show_great_job_screen(self, callback):
        self._pending_questionnaire_callback = callback
        self.stacked_layout.setCurrentWidget(self.great_job_page)
        QTimer.singleShot(2000, self._show_ready_page)

    def _show_ready_page(self):
        self.stacked_layout.setCurrentWidget(self.ready_page)

    # ── Ready page ────────────────────────────────────────────────────────────

    def _build_ready_page(self):
        self.ready_page = QWidget()
        self.ready_page.setObjectName("child-page")
        self.ready_page.setAttribute(Qt.WA_StyledBackground, True)

        l = QVBoxLayout(self.ready_page)
        l.setAlignment(Qt.AlignCenter); l.setSpacing(36)

        emoji = QLabel("🎉")
        emoji.setAlignment(Qt.AlignCenter)
        emoji.setStyleSheet("font-size: 90px;")

        title = QLabel("Ok, now let's answer a few questions!")
        title.setObjectName("ready-title"); title.setAlignment(Qt.AlignCenter)

        sub = QLabel("Press the button when you're ready")
        sub.setObjectName("ready-sub"); sub.setAlignment(Qt.AlignCenter)

        self._ready_btn = QPushButton("I'M READY  ✓")
        self._ready_btn.setObjectName("ready-btn")
        self._ready_btn.setCursor(Qt.PointingHandCursor)
        self._ready_btn.clicked.connect(self._on_ready_pressed)

        l.addWidget(emoji); l.addWidget(title); l.addWidget(sub)
        l.addSpacing(20); l.addWidget(self._ready_btn, alignment=Qt.AlignCenter)
        self.stacked_layout.addWidget(self.ready_page)

    def _on_ready_pressed(self):
        if hasattr(self, "_pending_questionnaire_callback"):
            self._pending_questionnaire_callback()

    # ── Questionnaire page ────────────────────────────────────────────────────

    def _build_questionnaire_page(self):
        self.questionnaire_page = QWidget()
        self.questionnaire_page.setObjectName("child-page")
        self.questionnaire_page.setAttribute(Qt.WA_StyledBackground, True)

        outer = QVBoxLayout(self.questionnaire_page)
        outer.setContentsMargins(80, 50, 80, 50)
        outer.setSpacing(36)
        outer.setAlignment(Qt.AlignCenter)

        self.q_label = QLabel("")
        self.q_label.setObjectName("question-text")
        self.q_label.setAlignment(Qt.AlignCenter)
        self.q_label.setWordWrap(True)
        outer.addWidget(self.q_label)

        # Centred card
        card_wrapper = QHBoxLayout()
        card_wrapper.setAlignment(Qt.AlignCenter)

        card = QFrame()
        card.setObjectName("q-card")
        card.setAttribute(Qt.WA_StyledBackground, True)
        card.setFixedWidth(920)

        cl = QVBoxLayout(card)
        cl.setContentsMargins(32, 40, 32, 40)
        cl.setSpacing(0)
        cl.setAlignment(Qt.AlignCenter)

        band = QHBoxLayout()
        band.setSpacing(0)
        band.setContentsMargins(0, 0, 0, 0)

        # Left image + label
        lc = QVBoxLayout(); lc.setAlignment(Qt.AlignCenter); lc.setSpacing(10)
        self.left_image = QLabel()
        self.left_image.setAlignment(Qt.AlignCenter)
        self.left_image.setFixedSize(140, 140)
        self.left_label = QLabel("")
        self.left_label.setObjectName("anchor-label")
        self.left_label.setAlignment(Qt.AlignCenter)
        self.left_label.setFixedWidth(160)
        self.left_label.setWordWrap(True)
        lc.addWidget(self.left_image); lc.addWidget(self.left_label)

        # Slider
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 100)
        self.slider.setSingleStep(1)
        self.slider.setPageStep(10)
        self.slider.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.slider.setStyleSheet("""
            QSlider { margin: 0px; }
            QSlider::groove:horizontal {
                height: 20px; background: #F8BBD0; border-radius: 10px;
            }
            QSlider::sub-page:horizontal {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #880E4F, stop:1 #E91E63);
                border-radius: 10px; height: 20px;
            }
            QSlider::handle:horizontal {
                background: #C2185B;
                border: 4px solid #FFFFFF;
                width: 44px; height: 44px; margin: -14px 0; border-radius: 22px;
            }
            QSlider::handle:horizontal:hover {
                background: #E91E63; border: 4px solid #FFFFFF;
            }
        """)

        # Right image + label
        rc = QVBoxLayout(); rc.setAlignment(Qt.AlignCenter); rc.setSpacing(10)
        self.right_image = QLabel()
        self.right_image.setAlignment(Qt.AlignCenter)
        self.right_image.setFixedSize(140, 140)
        self.right_label = QLabel("")
        self.right_label.setObjectName("anchor-label")
        self.right_label.setAlignment(Qt.AlignCenter)
        self.right_label.setFixedWidth(160)
        self.right_label.setWordWrap(True)
        rc.addWidget(self.right_image); rc.addWidget(self.right_label)

        band.addLayout(lc)
        band.addSpacing(20)
        band.addWidget(self.slider, alignment=Qt.AlignVCenter)
        band.addSpacing(20)
        band.addLayout(rc)

        cl.addLayout(band)
        card_wrapper.addWidget(card)
        outer.addLayout(card_wrapper)

        self.next_button = QPushButton("NEXT  →")
        self.next_button.setObjectName("next-btn")
        self.next_button.setCursor(Qt.PointingHandCursor)
        self.next_button.clicked.connect(self._next_question)
        outer.addWidget(self.next_button, alignment=Qt.AlignCenter)

        self.stacked_layout.addWidget(self.questionnaire_page)

        self.questions = [
            {
                "text":        "How many words did you get right?",
                "left_label":  "None of them",
                "right_label": "All of them",
                "left_img":    "none.png",
                "right_img":   "tick.png",
            },
            {
                "text":        "How much did you want to do a good job?",
                "left_label":  "I didn't care at all",
                "right_label": "I really, really wanted to do a good job",
                "left_img":    "sad.png",
                "right_img":   "happy.png",
            },
            {
                "text":        "How hard did you have to try to get the words right?",
                "left_label":  "Not hard at all",
                "right_label": "Very, very hard",
                "left_img":    "not hard.png",
                "right_img":   "very hard.png",
            },
            {
                "text":        "How long did that feel?",
                "left_label":  "It felt fast",
                "right_label": "It took forever",
                "left_img":    "fast.png",
                "right_img":   "slow.png",
            },
        ]

    def start_questionnaire(self, on_complete):
        self.answers = []
        self.question_index = 0
        self.question_complete_callback = on_complete
        self._show_question()
        self.stacked_layout.setCurrentWidget(self.questionnaire_page)

    def _show_question(self):
        q = self.questions[self.question_index]
        self.q_label.setText(q["text"])
        self.left_label.setText(q["left_label"])
        self.right_label.setText(q["right_label"])
        for widget, key in [(self.left_image, "left_img"), (self.right_image, "right_img")]:
            path = os.path.join(ASSETS_DIR, q[key])
            if os.path.exists(path):
                pix = QPixmap(path)
                widget.setPixmap(pix.scaled(140, 140, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            else:
                widget.clear()
        self.slider.setValue(50)

    def _next_question(self):
        self.answers.append(self.slider.value())
        self.question_index += 1
        if self.question_index >= len(self.questions):
            self.question_complete_callback(self.answers)
        else:
            self._show_question()

    # ── Waiting page ──────────────────────────────────────────────────────────

    def _build_waiting_page(self):
        self.waiting_page = QWidget()
        self.waiting_page.setObjectName("child-page")
        self.waiting_page.setAttribute(Qt.WA_StyledBackground, True)

        l = QVBoxLayout(self.waiting_page)
        l.setAlignment(Qt.AlignCenter); l.setSpacing(16)

        title = QLabel("Well done!")
        title.setObjectName("waiting-title"); title.setAlignment(Qt.AlignCenter)

        sub = QLabel("Let's listen carefully again…")
        sub.setObjectName("waiting-sub"); sub.setAlignment(Qt.AlignCenter)

        l.addWidget(title); l.addWidget(sub)
        self.stacked_layout.addWidget(self.waiting_page)

    def show_waiting_screen(self):
        self.stacked_layout.setCurrentWidget(self.waiting_page)

    # ── Goodbye page ──────────────────────────────────────────────────────────

    _FUN_FACTS = [
        "Your ears never stop working — even when you're asleep! 😴",
        "Cats can hear sounds that are way too high for humans to hear! 🐱",
        "A blue whale's call is the loudest animal sound on Earth! 🐋",
        "Your ears help you balance — they're like a built-in gyroscope! 🌀",
        "Butterflies hear through sensors on their wings! 🦋",
        "Sound travels about 4× faster through water than through air! 🌊",
        "Elephants can hear sounds too low for humans — through their feet! 🐘",
        "The smallest bones in your body are inside your ear! 🦴",
        "Dolphins use sound to 'see' underwater — it's called echolocation! 🐬",
        "A cricket hears with organs on its front legs! 🦗",
    ]

    def _build_goodbye_page(self):
        self.goodbye_page = QWidget()
        self.goodbye_page.setObjectName("child-page")
        self.goodbye_page.setAttribute(Qt.WA_StyledBackground, True)

        l = QVBoxLayout(self.goodbye_page)
        l.setAlignment(Qt.AlignCenter)
        l.setSpacing(20)
        l.setContentsMargins(80, 60, 80, 60)

        confetti = QLabel("🎉  🌸  🎊  💕  🎈")
        confetti.setObjectName("goodbye-emoji"); confetti.setAlignment(Qt.AlignCenter)

        title = QLabel("Thank You for Coming!")
        title.setObjectName("goodbye-title")
        title.setAlignment(Qt.AlignCenter); title.setWordWrap(True)

        sub = QLabel("You were absolutely amazing today!")
        sub.setObjectName("goodbye-sub"); sub.setAlignment(Qt.AlignCenter)

        fact_label = QLabel("DID YOU KNOW?")
        fact_label.setObjectName("funfact-label"); fact_label.setAlignment(Qt.AlignCenter)

        self._fact_display = QLabel(random.choice(self._FUN_FACTS))
        self._fact_display.setObjectName("funfact-box")
        self._fact_display.setAttribute(Qt.WA_StyledBackground, True)
        self._fact_display.setAlignment(Qt.AlignCenter)
        self._fact_display.setWordWrap(True)
        self._fact_display.setMaximumWidth(900)

        l.addWidget(confetti); l.addWidget(title); l.addWidget(sub)
        l.addSpacing(16); l.addWidget(fact_label); l.addWidget(self._fact_display)
        self.stacked_layout.addWidget(self.goodbye_page)

        self._fact_timer = QTimer(self)
        self._fact_timer.timeout.connect(self._rotate_fact)
        self._fact_timer.start(7000)

    def _rotate_fact(self):
        if hasattr(self, "_fact_display"):
            self._fact_display.setText(random.choice(self._FUN_FACTS))

    def show_goodbye_screen(self):
        self._fact_display.setText(random.choice(self._FUN_FACTS))
        self.stacked_layout.setCurrentWidget(self.goodbye_page)