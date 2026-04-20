import math
import random

from PySide6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout, QApplication, QPushButton
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import (
    QPainter, QColor, QFont, QPen, QLinearGradient, QBrush, QRadialGradient
)


class LandingWindow(QWidget):
    """
    Main landing screen shown at application start.

    This window serves as the participant entry point:
    - presents the study title,
    - animates the visual background,
    - fades in the session controls,
    - launches the task or exits the application.
    """

    def __init__(self):
        super().__init__()

        # Window title shown in the operating system window frame.
        self.setWindowTitle("DistVRT")

        # Use the primary screen as the landing screen so the window fills the display.
        screen = QApplication.primaryScreen().availableGeometry()
        self.setGeometry(screen)

        # State used for the animated background.
        self._particles = []
        self._dot_angle = 0
        self._ring_angle = 0

        # Callback registered by the main application to start the task flow.
        self._launch_callback = None

        # Initialize decorative animation elements.
        self._init_particles()

        # Apply base window styling and build the interface.
        self._apply_styles()
        self._build_ui()

        # Start all labels invisible so they can fade in sequentially.
        self.title_label.setStyleSheet(
            "color: rgba(255,255,255,0); font-size: 92px; font-weight: 900; letter-spacing: -2px;")
        self.sub_label.setStyleSheet(
            "color: rgba(255,182,193,0); font-size: 15px; letter-spacing: 4px; font-weight: bold;")
        self.lab_label.setStyleSheet(
            "color: rgba(220,160,180,0); font-size: 11px; letter-spacing: 3px;")
        self.launch_full_btn.setStyleSheet(self._btn_hidden())
        self.exit_btn.setStyleSheet(self._exit_hidden())

        # Stagger the fade-in sequence so the landing screen appears gradually.
        QTimer.singleShot(400, self._fade_title)
        QTimer.singleShot(1100, self._fade_sub)
        QTimer.singleShot(1700, self._fade_lab)
        QTimer.singleShot(2300, self._fade_buttons)

        # Timer used to animate the background continuously.
        self._bg_timer = QTimer(self)
        self._bg_timer.timeout.connect(self._tick)
        self._bg_timer.start(30)

        # The landing page is shown full screen.
        self.showFullScreen()

    # ── Particles ─────────────────────────────────────────────────────────────

    def _init_particles(self):
        # Color palette used for the drifting particle background.
        colours = [
            (255, 182, 193),   # blush pink
            (194, 24, 91),     # deep berry
            (255, 143, 171),   # soft rose
            (233, 30, 99),     # vivid raspberry
            (255, 214, 224),   # pale blush
            (173, 20, 87),     # dark berry
            (252, 131, 168),   # coral pink
        ]

        # Create a set of lightweight drifting particles.
        for _ in range(55):
            c = random.choice(colours)
            self._particles.append({
                "x": random.uniform(0, 1), "y": random.uniform(0, 1),
                "vx": random.uniform(-0.00016, 0.00016),
                "vy": random.uniform(-0.00013, 0.00013),
                "r": random.uniform(2.0, 5.5),
                "alpha": random.uniform(0.10, 0.26),
                "rc": c[0], "gc": c[1], "bc": c[2],
            })

    def _tick(self):
        # Advance the rotating accents used in the background artwork.
        self._dot_angle = (self._dot_angle + 0.45) % 360
        self._ring_angle = (self._ring_angle + 0.18) % 360

        # Move particles slightly each frame and wrap them around the screen edges.
        for p in self._particles:
            p["x"] = (p["x"] + p["vx"]) % 1.0
            p["y"] = (p["y"] + p["vy"]) % 1.0

        # Trigger a repaint after each animation step.
        self.update()

    # ── Paint ─────────────────────────────────────────────────────────────────

    def paintEvent(self, event):
        # Custom painting is used for the animated visual background.
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        cx, cy = w // 2, h // 2

        # Background gradient creates the dark berry theme used throughout the application.
        grad = QLinearGradient(0, 0, w, h)
        grad.setColorAt(0.0, QColor(58, 6, 32))
        grad.setColorAt(0.35, QColor(100, 10, 55))
        grad.setColorAt(0.65, QColor(130, 15, 70))
        grad.setColorAt(1.0, QColor(72, 8, 40))
        painter.fillRect(self.rect(), QBrush(grad))

        # Soft central glow keeps the middle of the screen visually prominent.
        rg = QRadialGradient(cx, cy, max(w, h) * 0.52)
        rg.setColorAt(0, QColor(255, 182, 193, 50))
        rg.setColorAt(0.35, QColor(233, 30, 99, 22))
        rg.setColorAt(0.7, QColor(194, 24, 91, 10))
        rg.setColorAt(1, QColor(0, 0, 0, 0))
        painter.setBrush(QBrush(rg))
        painter.setPen(Qt.NoPen)
        painter.drawRect(self.rect())

        # Fine grid overlay adds subtle structure to the background.
        pen_grid = QPen(QColor(255, 150, 180, 18))
        pen_grid.setWidth(1)
        painter.setPen(pen_grid)
        for x in range(0, w, 55):
            painter.drawLine(x, 0, x, h)
        for y in range(0, h, 55):
            painter.drawLine(0, y, w, y)

        # Decorative rings provide a focal design around the center.
        for radius, col in [
            (min(w, h) * 0.38, QColor(255, 182, 193, 30)),
            (min(w, h) * 0.44, QColor(233, 30, 99, 18)),
            (min(w, h) * 0.50, QColor(255, 214, 224, 12)),
        ]:
            pen_ring = QPen(col)
            pen_ring.setWidth(1)
            painter.setPen(pen_ring)
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(int(cx - radius), int(cy - radius),
                                int(radius * 2), int(radius * 2))

        # Animated arc adds movement and gives the page a live, modern feel.
        pen_arc = QPen(QColor(255, 182, 193, 200))
        pen_arc.setWidth(2)
        pen_arc.setCapStyle(Qt.RoundCap)
        painter.setPen(pen_arc)
        radius = min(w, h) * 0.50
        painter.drawArc(int(cx - radius), int(cy - radius),
                        int(radius * 2), int(radius * 2),
                        int(self._ring_angle * 16), 80 * 16)

        # Particle layer sits above the background and behind the text.
        painter.setPen(Qt.NoPen)
        for p in self._particles:
            px, py = int(p["x"] * w), int(p["y"] * h)
            r = p["r"]
            a = int(p["alpha"] * 255)
            painter.setBrush(QBrush(QColor(p["rc"], p["gc"], p["bc"], a)))
            painter.drawEllipse(int(px - r), int(py - r), int(r * 2), int(r * 2))

        # Accent line and moving dot reinforce the animated center focus.
        ay = cy - 155
        pen_acc = QPen(QColor(255, 182, 193, 90))
        pen_acc.setWidth(1)
        painter.setPen(pen_acc)
        painter.drawLine(cx - 280, ay, cx + 280, ay)

        dot_x = cx + int(math.sin(math.radians(self._dot_angle)) * 270)
        painter.setBrush(QBrush(QColor(255, 214, 224, 240)))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(dot_x - 4, ay - 4, 8, 8)

    # ── Styles ────────────────────────────────────────────────────────────────

    def _apply_styles(self):
        # Keep the window transparent so the custom paintEvent background remains visible.
        self.setStyleSheet("QWidget { background-color: transparent; }")

    def _btn_hidden(self):
        # Initial invisible state for the launch button.
        return """QPushButton {
            background-color: rgba(194,24,91,0); color: rgba(255,255,255,0);
            border: 2px solid rgba(255,182,193,0); border-radius: 14px;
            font-size: 17px; font-weight: bold;
            min-height: 62px; min-width: 340px; padding: 0 52px;
        }"""

    def _btn_visible(self):
        # Final visible state for the launch button.
        return """QPushButton {
            background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                stop:0 #AD1457, stop:0.5 #E91E63, stop:1 #F48FB1);
            color: #FFFFFF; border: none; border-radius: 14px;
            font-size: 17px; font-weight: bold; letter-spacing: 2px;
            min-height: 62px; min-width: 340px; padding: 0 52px;
            font-family: "Segoe UI", Arial, sans-serif;
        }
        QPushButton:hover {
            background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                stop:0 #C2185B, stop:0.5 #F06292, stop:1 #FFCDD2);
        }
        QPushButton:pressed { background-color: #880E4F; }"""

    def _exit_hidden(self):
        # Initial invisible state for the exit button.
        return """QPushButton {
            background-color: transparent; color: rgba(255,182,193,0);
            border: 1px solid rgba(255,182,193,0); border-radius: 12px;
            font-size: 14px; min-height: 62px; min-width: 130px; padding: 0 36px;
        }"""

    def _exit_visible(self):
        # Final visible state for the exit button.
        return """QPushButton {
            background-color: transparent; color: rgba(255,182,193,180);
            border: 1px solid rgba(255,182,193,100); border-radius: 12px;
            font-size: 14px; min-height: 62px; min-width: 130px; padding: 0 36px;
            font-family: "Segoe UI", Arial, sans-serif;
        }
        QPushButton:hover {
            color: rgba(255,214,224,230); border-color: rgba(255,182,193,180);
        }"""

    # ── UI layout ─────────────────────────────────────────────────────────────

    def _build_ui(self):
        # Root layout spans the full window and centers the content block vertically.
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addStretch(2)

        centre = QVBoxLayout()
        centre.setSpacing(0)
        centre.setAlignment(Qt.AlignCenter)

        # Lab name appears above the main task title.
        self.sub_label = QLabel("Children's Auditory Research for Educational Success (CARES) Lab")
        self.sub_label.setAlignment(Qt.AlignCenter)
        self.sub_label.setFont(QFont("Segoe UI", 13, QFont.Bold))
        centre.addWidget(self.sub_label)
        centre.addSpacing(16)

        # Main study title.
        self.title_label = QLabel("VRT")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setFont(QFont("Segoe UI", 92, QFont.Bold))
        centre.addWidget(self.title_label)
        centre.addSpacing(10)

        # Small version label used for internal identification.
        self.lab_label = QLabel("VIRTUAL REALITY TASK  ·  v5.0")
        self.lab_label.setAlignment(Qt.AlignCenter)
        self.lab_label.setFont(QFont("Segoe UI", 11))
        centre.addWidget(self.lab_label)
        centre.addSpacing(68)

        # Button row contains the start and exit actions.
        btn_row = QHBoxLayout()
        btn_row.setSpacing(18)
        btn_row.setAlignment(Qt.AlignCenter)

        self.launch_full_btn = QPushButton("▶   Begin Session")
        self.launch_full_btn.setCursor(Qt.PointingHandCursor)
        self.launch_full_btn.clicked.connect(self._on_launch)

        self.exit_btn = QPushButton("Exit")
        self.exit_btn.setCursor(Qt.PointingHandCursor)
        self.exit_btn.clicked.connect(self._on_exit)

        btn_row.addWidget(self.launch_full_btn)
        btn_row.addWidget(self.exit_btn)
        centre.addLayout(btn_row)
        root.addLayout(centre)
        root.addStretch(3)

    # ── Button actions ────────────────────────────────────────────────────────

    def set_launch_callback(self, callback):
        """Register a callable that fires when 'Begin Session' is pressed."""
        self._launch_callback = callback

    def _on_launch(self):
        # Stop the landing animation before transitioning into the task flow.
        self._bg_timer.stop()
        if callable(self._launch_callback):
            self._launch_callback()

    def _on_exit(self):
        # Stop animation and close the application cleanly.
        self._bg_timer.stop()
        QApplication.quit()

    # ── Fade-in animations ────────────────────────────────────────────────────

    def _fade_label(self, label, style_fn, steps=20, interval=28):
        # Generic helper used to gradually reveal labels by updating opacity.
        cur = [0]

        def step():
            cur[0] += 1
            label.setStyleSheet(style_fn(int(cur[0] / steps * 255)))
            if cur[0] < steps:
                QTimer.singleShot(interval, step)

        step()

    def _fade_title(self):
        # Fade in the main title first.
        self._fade_label(self.title_label, lambda a:
            f"color: rgba(255,255,255,{a}); font-size: 92px; font-weight: 900; letter-spacing: -2px;")

    def _fade_sub(self):
        # Fade in the lab name after the title.
        self._fade_label(self.sub_label, lambda a:
            f"color: rgba(255,182,193,{a}); font-size: 15px; letter-spacing: 4px; font-weight: bold;")

    def _fade_lab(self):
        # Fade in the version label next.
        self._fade_label(self.lab_label, lambda a:
            f"color: rgba(220,160,180,{a}); font-size: 11px; letter-spacing: 3px;")

    def _fade_buttons(self):
        # Fade in the action buttons last so the start screen appears in stages.
        steps, interval, cur = 22, 24, [0]

        def step():
            cur[0] += 1
            a = int(cur[0] / steps * 255)

            # Gradually reveal the launch button.
            self.launch_full_btn.setStyleSheet(f"""QPushButton {{
                background: rgba(194,24,91,{a}); color: rgba(255,255,255,{a});
                border: none; border-radius: 14px;
                font-size: 17px; font-weight: bold; letter-spacing: 2px;
                min-height: 62px; min-width: 340px; padding: 0 52px;
            }}""")

            # Gradually reveal the exit button.
            self.exit_btn.setStyleSheet(f"""QPushButton {{
                background-color: transparent; color: rgba(255,182,193,{a});
                border: 1px solid rgba(255,182,193,{a}); border-radius: 12px;
                font-size: 14px; min-height: 62px; min-width: 130px; padding: 0 36px;
            }}""")

            if cur[0] < steps:
                QTimer.singleShot(interval, step)
            else:
                # Restore the final stylesheet state once fading is complete.
                self.launch_full_btn.setStyleSheet(self._btn_visible())
                self.exit_btn.setStyleSheet(self._exit_visible())

        step()
