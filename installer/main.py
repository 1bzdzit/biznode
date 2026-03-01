"""
BizNode Installer GUI
=====================
PySide6 wizard with 6 pages:
  0 – Welcome
  1 – System Diagnostics
  2 – Service Detection & Port Assignment
  3 – Configuration (.env form)
  4 – Deploy (local / USB)
  5 – Complete
"""

import os
import sys
import subprocess
import threading
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, List

from PySide6.QtCore import Qt, QThread, Signal, QTimer, QSize
from PySide6.QtGui import QFont, QColor, QPalette, QIcon, QPixmap, QTextCursor
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QComboBox, QSpinBox, QCheckBox,
    QTextEdit, QProgressBar, QStackedWidget, QFrame, QScrollArea,
    QGridLayout, QFileDialog, QMessageBox, QGroupBox, QSizePolicy,
    QRadioButton, QButtonGroup, QFormLayout, QSplitter,
)

# ---------------------------------------------------------------------------
# Shared installer config (passed between pages)
# ---------------------------------------------------------------------------

@dataclass
class InstallerConfig:
    # Detected state
    ollama_detected:  bool = False
    qdrant_detected:  bool = False
    docker_running:   bool = False
    gpu_available:    bool = False

    # Port assignments
    ollama_port:      int  = 11434
    qdrant_port:      int  = 6333
    dashboard_port:   int  = 7777

    # Deployment mode
    mode:             str  = "isolated"   # "shared" | "isolated"
    include_ollama:   bool = True
    include_qdrant:   bool = True

    # .env values
    telegram_token:   str  = ""
    owner_id:         str  = ""
    agent_name:       str  = "BizNode"
    llm_model:        str  = "qwen2.5"
    embed_model:      str  = "nomic-embed-text"
    owner_email:      str  = ""
    smtp_host:        str  = "smtp.gmail.com"
    smtp_port:        str  = "587"
    smtp_user:        str  = ""
    smtp_password:    str  = ""
    node_password:    str  = ""

    # Deploy target
    deploy_target:    str  = "local"   # "local" | "usb"
    usb_path:         str  = ""
    data_dir:         str  = "./memory"

    def to_env_dict(self) -> Dict[str, str]:
        base_url = f"http://localhost:{self.ollama_port}"
        return {
            "TELEGRAM_BOT_TOKEN": self.telegram_token,
            "OWNER_TELEGRAM_ID":  self.owner_id,
            "OLLAMA_URL":         f"{base_url}/api/generate",
            "OLLAMA_EMBED_URL":   f"{base_url}/api/embeddings",
            "QDRANT_HOST":        "localhost",
            "QDRANT_PORT":        str(self.qdrant_port),
            "LLM_MODEL":          self.llm_model,
            "EMBEDDING_MODEL":    self.embed_model,
            "AGENT_NAME":         self.agent_name,
            "OWNER_EMAIL":        self.owner_email,
            "SMTP_HOST":          self.smtp_host,
            "SMTP_PORT":          self.smtp_port,
            "SMTP_USER":          self.smtp_user,
            "SMTP_PASSWORD":      self.smtp_password,
            "NODE_PASSWORD":      self.node_password,
            "SQLITE_PATH":        "memory/biznode.db",
        }


# ---------------------------------------------------------------------------
# Colour palette & stylesheet
# ---------------------------------------------------------------------------

_BG     = "#0f1117"
_PANEL  = "#1a1d27"
_BORDER = "#2a2d3a"
_ACCENT = "#6366f1"
_GREEN  = "#22c55e"
_AMBER  = "#f59e0b"
_RED    = "#ef4444"
_TEXT   = "#e5e7eb"
_MUTED  = "#9ca3af"

_QSS = f"""
QWidget {{
    background-color: {_BG};
    color: {_TEXT};
    font-family: "Segoe UI", sans-serif;
    font-size: 13px;
}}
QMainWindow {{
    background-color: {_BG};
}}
QPushButton {{
    background-color: {_PANEL};
    color: {_TEXT};
    border: 1px solid {_BORDER};
    border-radius: 6px;
    padding: 6px 16px;
    font-size: 13px;
}}
QPushButton:hover {{
    background-color: {_BORDER};
}}
QPushButton#primary {{
    background-color: {_ACCENT};
    border: none;
    color: white;
    font-weight: bold;
}}
QPushButton#primary:hover {{
    background-color: #4f52c0;
}}
QPushButton#primary:disabled {{
    background-color: #3a3d6a;
    color: #6b7280;
}}
QPushButton#danger {{
    background-color: #7f1d1d;
    border: none;
    color: #fca5a5;
}}
QLineEdit, QSpinBox, QComboBox {{
    background-color: {_PANEL};
    border: 1px solid {_BORDER};
    border-radius: 6px;
    padding: 6px 10px;
    color: {_TEXT};
    font-size: 13px;
}}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus {{
    border: 1px solid {_ACCENT};
}}
QTextEdit {{
    background-color: {_BG};
    border: 1px solid {_BORDER};
    border-radius: 6px;
    color: {_TEXT};
    font-family: "Cascadia Code", "Consolas", monospace;
    font-size: 12px;
}}
QScrollBar:vertical {{
    background: {_PANEL};
    width: 6px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {_BORDER};
    border-radius: 3px;
    min-height: 20px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QGroupBox {{
    background-color: {_PANEL};
    border: 1px solid {_BORDER};
    border-radius: 8px;
    margin-top: 12px;
    padding: 8px;
    font-weight: bold;
}}
QGroupBox::title {{
    color: {_ACCENT};
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 4px;
}}
QCheckBox::indicator {{
    width: 14px;
    height: 14px;
    border: 1px solid {_BORDER};
    border-radius: 3px;
    background: {_PANEL};
}}
QCheckBox::indicator:checked {{
    background-color: {_ACCENT};
    border-color: {_ACCENT};
}}
QRadioButton::indicator {{
    width: 14px;
    height: 14px;
    border: 1px solid {_BORDER};
    border-radius: 7px;
    background: {_PANEL};
}}
QRadioButton::indicator:checked {{
    background-color: {_ACCENT};
    border-color: {_ACCENT};
}}
QProgressBar {{
    background-color: {_PANEL};
    border: 1px solid {_BORDER};
    border-radius: 4px;
    text-align: center;
    color: {_TEXT};
}}
QProgressBar::chunk {{
    background-color: {_ACCENT};
    border-radius: 3px;
}}
"""

# ---------------------------------------------------------------------------
# Helper widgets
# ---------------------------------------------------------------------------

def _label(text: str, bold: bool = False, size: int = 13,
           color: str = _TEXT) -> QLabel:
    lbl = QLabel(text)
    font = QFont()
    font.setPointSize(size)
    font.setBold(bold)
    lbl.setFont(font)
    lbl.setStyleSheet(f"color: {color}; background: transparent;")
    lbl.setWordWrap(True)
    return lbl


def _hline() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.HLine)
    f.setStyleSheet(f"color: {_BORDER}; background: {_BORDER};")
    f.setFixedHeight(1)
    return f


def _card(child: QWidget) -> QWidget:
    card = QWidget()
    card.setObjectName("card")
    card.setStyleSheet(
        f"#card {{ background-color: {_PANEL}; border: 1px solid {_BORDER}; border-radius: 8px; }}"
    )
    lay = QVBoxLayout(card)
    lay.setContentsMargins(16, 12, 16, 12)
    lay.addWidget(child)
    return card


class StatusRow(QWidget):
    """One check result row: icon + label + detail."""

    def __init__(self, label: str = "", detail: str = "",
                 ok: bool = True, warn: bool = False):
        super().__init__()
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 2, 0, 2)

        icon = "✓" if ok and not warn else ("⚠" if warn else "✗")
        color = _GREEN if ok and not warn else (_AMBER if warn else _RED)

        self._icon_lbl = QLabel(icon)
        self._icon_lbl.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 14px; background: transparent;")
        self._icon_lbl.setFixedWidth(22)

        self._name_lbl = QLabel(label)
        self._name_lbl.setStyleSheet(f"color: {_TEXT}; font-weight: bold; background: transparent;")
        self._name_lbl.setFixedWidth(200)

        self._detail_lbl = QLabel(detail)
        self._detail_lbl.setStyleSheet(f"color: {_MUTED}; background: transparent;")

        lay.addWidget(self._icon_lbl)
        lay.addWidget(self._name_lbl)
        lay.addWidget(self._detail_lbl)
        lay.addStretch()

    def update_result(self, ok: bool, warn: bool, label: str, detail: str):
        icon  = "✓" if ok and not warn else ("⚠" if warn else "✗")
        color = _GREEN if ok and not warn else (_AMBER if warn else _RED)
        self._icon_lbl.setText(icon)
        self._icon_lbl.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 14px; background: transparent;")
        self._name_lbl.setText(label)
        self._detail_lbl.setText(detail)


# ---------------------------------------------------------------------------
# Background worker thread
# ---------------------------------------------------------------------------

class Worker(QThread):
    progress = Signal(str)   # log line
    finished = Signal(bool)  # success flag

    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self._fn = fn
        self._args = args
        self._kwargs = kwargs

    def run(self):
        try:
            self._fn(*self._args, **self._kwargs,
                     log=lambda m: self.progress.emit(m))
            self.finished.emit(True)
        except Exception as e:
            self.progress.emit(f"✗ Error: {e}")
            self.finished.emit(False)


# ---------------------------------------------------------------------------
# PAGE 0 – Welcome
# ---------------------------------------------------------------------------

class WelcomePage(QWidget):
    def __init__(self, cfg: InstallerConfig):
        super().__init__()
        self.cfg = cfg
        lay = QVBoxLayout(self)
        lay.setContentsMargins(60, 40, 60, 40)
        lay.setAlignment(Qt.AlignCenter)

        # Logo / title block
        logo = _label("⬡", bold=True, size=52, color=_ACCENT)
        logo.setAlignment(Qt.AlignCenter)
        lay.addWidget(logo)

        title = _label("BizNode Installer", bold=True, size=24, color=_TEXT)
        title.setAlignment(Qt.AlignCenter)
        lay.addWidget(title)

        sub = _label("Autonomous AI Business Operator — Desktop Setup Wizard",
                     size=12, color=_MUTED)
        sub.setAlignment(Qt.AlignCenter)
        lay.addSpacing(6)
        lay.addWidget(sub)
        lay.addSpacing(32)

        # Feature bullets
        features = [
            ("📡", "Telegram bot — your agent's control channel"),
            ("🧠", "Ollama LLM — on-device AI, no cloud required"),
            ("🗄️", "Qdrant — vector memory for semantic recall"),
            ("🔍", "Auto-detects running services and free ports"),
            ("💾", "Deploys locally or to a USB portable node"),
            ("🐳", "Builds your Docker stack with one click"),
        ]
        grid = QWidget()
        grid_lay = QGridLayout(grid)
        grid_lay.setHorizontalSpacing(24)
        grid_lay.setVerticalSpacing(10)
        for i, (icon, text) in enumerate(features):
            row, col = i // 2, i % 2
            row_w = QWidget()
            row_w.setStyleSheet(f"background: {_PANEL}; border-radius: 8px;")
            rlay = QHBoxLayout(row_w)
            rlay.setContentsMargins(12, 8, 12, 8)
            rlay.addWidget(_label(icon, size=16))
            rlay.addWidget(_label(text, size=12, color=_MUTED))
            rlay.addStretch()
            grid_lay.addWidget(row_w, row, col)

        lay.addWidget(grid)
        lay.addStretch()

        # Version / license note
        note = _label(
            "Open-source under Apache 2.0  ·  BizNode v2  ·  1BZ DZIT DAO LLC",
            size=10, color=_MUTED
        )
        note.setAlignment(Qt.AlignCenter)
        lay.addWidget(note)


# ---------------------------------------------------------------------------
# PAGE 1 – System Diagnostics
# ---------------------------------------------------------------------------

class _DiagWorker(QThread):
    """Runs all system checks and emits each result to the main thread."""
    check_result = Signal(int, bool, bool, str, str)  # index, ok, warn, label, detail
    finished = Signal(bool)

    def run(self):
        try:
            from installer.core.diagnostics import run_all_checks
            results = run_all_checks()
            for i, res in enumerate(results):
                self.check_result.emit(
                    i,
                    bool(res["ok"]),
                    bool(res.get("warn", False)),
                    str(res["label"]),
                    str(res["detail"]),
                )
            self.finished.emit(True)
        except Exception as e:
            self.finished.emit(False)


class DiagnosticsPage(QWidget):
    def __init__(self, cfg: InstallerConfig):
        super().__init__()
        self.cfg = cfg
        self._rows: List[StatusRow] = []
        self._worker: Optional[_DiagWorker] = None
        self._total_checks = 10

        outer = QVBoxLayout(self)
        outer.setContentsMargins(40, 24, 40, 24)

        outer.addWidget(_label("System Diagnostics", bold=True, size=18))
        outer.addWidget(_label(
            "Checking prerequisites before installation.",
            size=12, color=_MUTED))
        outer.addSpacing(16)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        outer.addWidget(self.progress_bar)
        outer.addSpacing(12)

        # Check rows
        check_names = [
            "Python ≥ 3.10",
            "Docker installed",
            "Docker daemon running",
            "WSL2 available",
            "RAM ≥ 8 GB",
            "Disk space ≥ 10 GB free",
            "NVIDIA GPU",
            "Port 11434 (Ollama)",
            "Port 6333 (Qdrant)",
            "Port 7777 (Dashboard)",
        ]
        self._total_checks = len(check_names)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        inner = QWidget()
        inner_lay = QVBoxLayout(inner)
        inner_lay.setContentsMargins(0, 0, 0, 0)
        inner_lay.setSpacing(4)

        for name in check_names:
            row = StatusRow(label=name, detail="Pending…", ok=True, warn=True)
            self._rows.append(row)
            inner_lay.addWidget(row)

        inner_lay.addStretch()
        scroll.setWidget(inner)
        outer.addWidget(scroll)
        outer.addSpacing(12)

        # Recheck button
        self.recheck_btn = QPushButton("↺  Re-run Checks")
        self.recheck_btn.clicked.connect(self.run_checks)
        outer.addWidget(self.recheck_btn)

        self.result_label = _label("", size=12, color=_AMBER)
        outer.addWidget(self.result_label)

    def run_checks(self):
        # Guard: don't start a second run while one is in progress
        if self._worker and self._worker.isRunning():
            return

        self.recheck_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        self.result_label.setText("")
        for row in self._rows:
            row.update_result(True, True, row._name_lbl.text(), "Checking…")

        self._worker = _DiagWorker()
        self._worker.check_result.connect(self._on_check_result)
        self._worker.finished.connect(self._on_done)
        self._worker.start()

    def _on_check_result(self, idx: int, ok: bool, warn: bool, label: str, detail: str):
        """Called on the main thread for each completed check."""
        if idx < len(self._rows):
            self._rows[idx].update_result(ok=ok, warn=warn, label=label, detail=detail)
        pct = int(((idx + 1) / self._total_checks) * 100)
        self.progress_bar.setValue(pct)
        # Update config flags
        if "Docker daemon" in label:
            self.cfg.docker_running = ok
        if "NVIDIA" in label:
            self.cfg.gpu_available = ok and not warn

    def _on_done(self, success: bool):
        self.recheck_btn.setEnabled(True)
        fails = [r for r in self._rows if r._icon_lbl.text() == "✗"]
        warns = [r for r in self._rows if r._icon_lbl.text() == "⚠"]
        if fails:
            self.result_label.setStyleSheet(f"color: {_RED};")
            self.result_label.setText(
                f"{len(fails)} check(s) failed. Resolve them or proceed with caution.")
        elif warns:
            self.result_label.setStyleSheet(f"color: {_AMBER};")
            self.result_label.setText(
                f"{len(warns)} warning(s). You can still proceed.")
        else:
            self.result_label.setStyleSheet(f"color: {_GREEN};")
            self.result_label.setText("All checks passed. Ready to install.")

    def on_show(self):
        self.run_checks()


# ---------------------------------------------------------------------------
# PAGE 2 – Service Detection & Port Assignment
# ---------------------------------------------------------------------------

class _ServicesWorker(QThread):
    """Runs detect_all() in background and emits the full result to the main thread."""
    detected = Signal(object)   # emits the dict returned by detect_all()
    finished = Signal(bool)

    def __init__(self, dashboard_port: int):
        super().__init__()
        self._dashboard_port = dashboard_port

    def run(self):
        try:
            from installer.core.service_detector import detect_all
            result = detect_all(self._dashboard_port)
            self.detected.emit(result)
            self.finished.emit(True)
        except Exception as e:
            self.detected.emit({})
            self.finished.emit(False)


class ServicesPage(QWidget):
    def __init__(self, cfg: InstallerConfig):
        super().__init__()
        self.cfg = cfg
        self._worker: Optional[_ServicesWorker] = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(40, 24, 40, 24)
        outer.setSpacing(12)

        outer.addWidget(_label("Service Detection", bold=True, size=18))
        outer.addWidget(_label(
            "BizNode detected the following services on your system.",
            size=12, color=_MUTED))

        # Detect button
        self.detect_btn = QPushButton("⚡  Detect Services Now")
        self.detect_btn.setObjectName("primary")
        self.detect_btn.clicked.connect(self.detect)
        outer.addWidget(self.detect_btn)

        # Results group
        res_grp = QGroupBox("Detected Services")
        res_lay = QVBoxLayout(res_grp)

        self.ollama_row  = StatusRow("Ollama",  "Not checked", True, True)
        self.qdrant_row  = StatusRow("Qdrant",  "Not checked", True, True)
        self.docker_row  = StatusRow("Docker",  "Not checked", True, True)
        self.biznode_row = StatusRow("BizNode", "Not checked", True, True)

        for r in (self.ollama_row, self.qdrant_row,
                  self.docker_row, self.biznode_row):
            res_lay.addWidget(r)
        outer.addWidget(res_grp)

        # Mode selection
        mode_grp = QGroupBox("Deployment Mode")
        mode_lay = QVBoxLayout(mode_grp)

        self.mode_shared = QRadioButton(
            "🔵  Shared Mode — reuse existing Ollama / Qdrant (lightweight)")
        self.mode_isolated = QRadioButton(
            "🔴  Isolated Mode — install dedicated containers (full independence)")
        self.mode_isolated.setChecked(True)
        self.mode_shared.toggled.connect(self._update_mode)

        btn_grp = QButtonGroup(self)
        btn_grp.addButton(self.mode_shared)
        btn_grp.addButton(self.mode_isolated)

        mode_lay.addWidget(self.mode_shared)
        mode_lay.addWidget(self.mode_isolated)
        outer.addWidget(mode_grp)

        # Port assignment
        ports_grp = QGroupBox("Port Assignment")
        ports_form = QFormLayout(ports_grp)
        ports_form.setLabelAlignment(Qt.AlignRight)

        self.ollama_port_spin = QSpinBox()
        self.ollama_port_spin.setRange(1024, 65535)
        self.ollama_port_spin.setValue(11434)
        self.ollama_port_spin.valueChanged.connect(
            lambda v: setattr(self.cfg, "ollama_port", v))

        self.qdrant_port_spin = QSpinBox()
        self.qdrant_port_spin.setRange(1024, 65535)
        self.qdrant_port_spin.setValue(6333)
        self.qdrant_port_spin.valueChanged.connect(
            lambda v: setattr(self.cfg, "qdrant_port", v))

        self.dash_port_spin = QSpinBox()
        self.dash_port_spin.setRange(1024, 65535)
        self.dash_port_spin.setValue(7777)
        self.dash_port_spin.valueChanged.connect(
            lambda v: setattr(self.cfg, "dashboard_port", v))

        self.auto_btn = QPushButton("Auto-assign free ports")
        self.auto_btn.clicked.connect(self._auto_assign_ports)

        ports_form.addRow("Ollama port:",    self.ollama_port_spin)
        ports_form.addRow("Qdrant port:",    self.qdrant_port_spin)
        ports_form.addRow("Dashboard port:", self.dash_port_spin)
        ports_form.addRow("",               self.auto_btn)
        outer.addWidget(ports_grp)

        outer.addStretch()

    def detect(self):
        # Guard: don't start a second scan while one is in progress
        if self._worker and self._worker.isRunning():
            return

        self.detect_btn.setEnabled(False)
        for row in (self.ollama_row, self.qdrant_row,
                    self.docker_row, self.biznode_row):
            row.update_result(True, True, row._name_lbl.text(), "Scanning…")

        self._worker = _ServicesWorker(self.cfg.dashboard_port)
        self._worker.detected.connect(self._on_detected)
        self._worker.finished.connect(lambda _: self.detect_btn.setEnabled(True))
        self._worker.start()

    def _on_detected(self, found: dict):
        """Called on the main thread with the full detect_all() result."""
        if not found:
            for row in (self.ollama_row, self.qdrant_row,
                        self.docker_row, self.biznode_row):
                row.update_result(False, False, row._name_lbl.text(), "Detection failed")
            return

        ol = found.get("ollama", {})
        self.cfg.ollama_detected = bool(ol.get("running"))
        self.ollama_row.update_result(
            ok=True, warn=ol.get("running", False),
            label="Ollama",
            detail=(f"Running on :{ol['port']} — models: {', '.join(ol.get('models', [])) or 'none'}"
                    if ol.get("running") else "Not detected")
        )

        qd = found.get("qdrant", {})
        self.cfg.qdrant_detected = bool(qd.get("running"))
        self.qdrant_row.update_result(
            ok=True, warn=qd.get("running", False),
            label="Qdrant",
            detail=(f"Running on :{qd['port']} — collections: {len(qd.get('collections', []))}"
                    if qd.get("running") else "Not detected")
        )

        bn = found.get("biznode", {}) or {}
        self.biznode_row.update_result(
            ok=True, warn=bn.get("running", False),
            label="BizNode",
            detail=(f"Dashboard running on :{bn['port']}"
                    if bn.get("running") else "Not detected")
        )

        self.docker_row.update_result(
            ok=self.cfg.docker_running,
            warn=not self.cfg.docker_running,
            label="Docker",
            detail="Running" if self.cfg.docker_running else "Not running"
        )

        # Suggest shared mode if both Ollama and Qdrant are already running
        if ol.get("running") and qd.get("running"):
            self.mode_shared.setChecked(True)

        # Auto-assign ports based on what's running
        self._auto_assign_ports()

    def _update_mode(self, shared: bool):
        self.cfg.mode = "shared" if shared else "isolated"
        self.cfg.include_ollama = not (shared and self.cfg.ollama_detected)
        self.cfg.include_qdrant = not (shared and self.cfg.qdrant_detected)

    def _auto_assign_ports(self):
        from installer.core.service_detector import assign_ports
        ports = assign_ports(
            want_ollama_port=self.ollama_port_spin.value(),
            want_qdrant_port=self.qdrant_port_spin.value(),
            want_dashboard_port=self.dash_port_spin.value(),
            ollama_running=self.cfg.ollama_detected and self.cfg.mode == "shared",
            qdrant_running=self.cfg.qdrant_detected and self.cfg.mode == "shared",
        )
        self.ollama_port_spin.setValue(ports["ollama"])
        self.qdrant_port_spin.setValue(ports["qdrant"])
        self.dash_port_spin.setValue(ports["dashboard"])

    def on_show(self):
        self.detect()


# ---------------------------------------------------------------------------
# PAGE 3 – Configuration (.env form)
# ---------------------------------------------------------------------------

class ConfigPage(QWidget):
    def __init__(self, cfg: InstallerConfig):
        super().__init__()
        self.cfg = cfg

        outer = QVBoxLayout(self)
        outer.setContentsMargins(40, 24, 40, 24)
        outer.addWidget(_label("Configure BizNode", bold=True, size=18))
        outer.addWidget(_label(
            "These values are saved to .env in the project root.",
            size=12, color=_MUTED))
        outer.addSpacing(12)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        inner = QWidget()
        lay = QVBoxLayout(inner)
        lay.setContentsMargins(0, 0, 8, 0)
        lay.setSpacing(12)

        # ── Telegram ──────────────────────────────────
        tg = QGroupBox("📡  Telegram Bot  (required)")
        tg_f = QFormLayout(tg)
        self.token_edit  = self._secret_field()
        self.ownerid_edit = QLineEdit()
        self.ownerid_edit.setPlaceholderText("e.g. 123456789  — get from @userinfobot")
        tg_f.addRow("Bot Token ★:", self.token_edit)
        tg_f.addRow("Owner Telegram ID ★:", self.ownerid_edit)

        self.test_tg_btn = QPushButton("Test Telegram →")
        self.test_tg_btn.clicked.connect(self._test_telegram)
        self.test_tg_lbl = _label("", size=11, color=_MUTED)
        tg_f.addRow("", self.test_tg_btn)
        tg_f.addRow("", self.test_tg_lbl)
        lay.addWidget(tg)

        # ── Agent identity ─────────────────────────────
        ag = QGroupBox("🤖  Agent Identity")
        ag_f = QFormLayout(ag)
        self.name_edit  = QLineEdit("BizNode")
        self.model_edit = QLineEdit("qwen2.5")
        self.embed_edit = QLineEdit("nomic-embed-text")
        ag_f.addRow("Agent Name:",       self.name_edit)
        ag_f.addRow("LLM Model:",        self.model_edit)
        ag_f.addRow("Embedding Model:",  self.embed_edit)
        lay.addWidget(ag)

        # ── Email (optional) ──────────────────────────
        em = QGroupBox("📧  Email / SMTP  (optional)")
        em_f = QFormLayout(em)
        self.owner_email_edit = QLineEdit()
        self.agent_email_edit = QLineEdit()
        self.smtp_host_edit = QLineEdit("smtp.gmail.com")
        self.smtp_port_edit = QLineEdit("587")
        self.smtp_user_edit = QLineEdit()
        self.smtp_pass_edit = self._secret_field()
        em_f.addRow("Owner Email:",  self.owner_email_edit)
        em_f.addRow("Agent Email:",  self.agent_email_edit)
        em_f.addRow("SMTP Host:",    self.smtp_host_edit)
        em_f.addRow("SMTP Port:",    self.smtp_port_edit)
        em_f.addRow("SMTP User:",    self.smtp_user_edit)
        em_f.addRow("SMTP Password:", self.smtp_pass_edit)
        lay.addWidget(em)

        # ── Security (optional) ───────────────────────
        sec = QGroupBox("🔐  Security  (optional)")
        sec_f = QFormLayout(sec)
        self.node_pass_edit = self._secret_field()
        self.node_pass_edit.setPlaceholderText("Set once — encrypts node identity")
        sec_f.addRow("Node Password:", self.node_pass_edit)
        lay.addWidget(sec)

        lay.addStretch()
        scroll.setWidget(inner)
        outer.addWidget(scroll)

    @staticmethod
    def _secret_field() -> QLineEdit:
        e = QLineEdit()
        e.setEchoMode(QLineEdit.Password)
        e.setPlaceholderText("Paste here…")
        return e

    def _test_telegram(self):
        token = self.token_edit.text().strip()
        if not token:
            self.test_tg_lbl.setStyleSheet(f"color: {_RED};")
            self.test_tg_lbl.setText("Enter bot token first.")
            return
        self.test_tg_lbl.setStyleSheet(f"color: {_AMBER};")
        self.test_tg_lbl.setText("Testing…")

        def _check(log=None):
            import requests
            try:
                r = requests.get(
                    f"https://api.telegram.org/bot{token}/getMe", timeout=6)
                data = r.json()
                if data.get("ok"):
                    bot = data["result"]
                    self.test_tg_lbl.setStyleSheet(f"color: {_GREEN};")
                    self.test_tg_lbl.setText(
                        f"✓ Connected: @{bot.get('username')} ({bot.get('first_name')})")
                else:
                    self.test_tg_lbl.setStyleSheet(f"color: {_RED};")
                    self.test_tg_lbl.setText(
                        f"✗ {data.get('description', 'Invalid token')}")
            except Exception as e:
                self.test_tg_lbl.setStyleSheet(f"color: {_RED};")
                self.test_tg_lbl.setText(f"✗ {e}")

        Worker(_check).start()

    def sync_to_config(self):
        self.cfg.telegram_token = self.token_edit.text().strip()
        self.cfg.owner_id       = self.ownerid_edit.text().strip()
        self.cfg.agent_name     = self.name_edit.text().strip() or "BizNode"
        self.cfg.llm_model      = self.model_edit.text().strip() or "qwen2.5"
        self.cfg.embed_model    = self.embed_edit.text().strip() or "nomic-embed-text"
        self.cfg.owner_email    = self.owner_email_edit.text().strip()
        self.cfg.smtp_host      = self.smtp_host_edit.text().strip()
        self.cfg.smtp_port      = self.smtp_port_edit.text().strip()
        self.cfg.smtp_user      = self.smtp_user_edit.text().strip()
        self.cfg.smtp_password  = self.smtp_pass_edit.text().strip()
        self.cfg.node_password  = self.node_pass_edit.text().strip()


# ---------------------------------------------------------------------------
# PAGE 4 – Deploy
# ---------------------------------------------------------------------------

class DeployPage(QWidget):
    def __init__(self, cfg: InstallerConfig):
        super().__init__()
        self.cfg = cfg
        self._worker: Optional[Worker] = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(40, 24, 40, 24)
        outer.setSpacing(12)

        outer.addWidget(_label("Install & Launch", bold=True, size=18))
        outer.addWidget(_label(
            "Choose your deployment target and click Install.",
            size=12, color=_MUTED))

        # Target selection
        tgt_grp = QGroupBox("Deployment Target")
        tgt_lay = QVBoxLayout(tgt_grp)

        self.local_radio = QRadioButton("💻  This machine — generate docker-compose.yml + .env and start")
        self.usb_radio   = QRadioButton("💾  USB portable — copy full stack to a removable drive")
        self.local_radio.setChecked(True)
        self.local_radio.toggled.connect(self._toggle_usb)

        btn_grp = QButtonGroup(self)
        btn_grp.addButton(self.local_radio)
        btn_grp.addButton(self.usb_radio)
        tgt_lay.addWidget(self.local_radio)
        tgt_lay.addWidget(self.usb_radio)

        # USB path row
        self.usb_row = QWidget()
        usb_row_lay = QHBoxLayout(self.usb_row)
        usb_row_lay.setContentsMargins(20, 0, 0, 0)
        self.usb_combo = QComboBox()
        self.usb_combo.setMinimumWidth(180)
        self.refresh_usb_btn = QPushButton("↺ Refresh")
        self.refresh_usb_btn.clicked.connect(self._refresh_usb)
        usb_row_lay.addWidget(_label("Drive:", size=12))
        usb_row_lay.addWidget(self.usb_combo)
        usb_row_lay.addWidget(self.refresh_usb_btn)
        usb_row_lay.addStretch()
        self.usb_row.setVisible(False)
        tgt_lay.addWidget(self.usb_row)
        outer.addWidget(tgt_grp)

        # Options
        opt_grp = QGroupBox("Options")
        opt_lay = QVBoxLayout(opt_grp)
        self.pull_models_chk = QCheckBox("Pull LLM models after start (Ollama must be running)")
        self.pull_models_chk.setChecked(True)
        self.start_after_chk = QCheckBox("Start Docker stack after generating config")
        self.start_after_chk.setChecked(True)
        opt_lay.addWidget(self.pull_models_chk)
        opt_lay.addWidget(self.start_after_chk)
        outer.addWidget(opt_grp)

        # Progress + log
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        outer.addWidget(self.progress)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMinimumHeight(180)
        outer.addWidget(self.log)

        # Install button
        self.install_btn = QPushButton("🚀  Install BizNode")
        self.install_btn.setObjectName("primary")
        self.install_btn.clicked.connect(self.install)
        outer.addWidget(self.install_btn)

        self._refresh_usb()

    def _toggle_usb(self, local: bool):
        self.usb_row.setVisible(not local)
        self.cfg.deploy_target = "local" if local else "usb"

    def _refresh_usb(self):
        self.usb_combo.clear()
        from installer.core.usb_deployer import list_removable_drives
        drives = list_removable_drives()
        if drives:
            self.usb_combo.addItems(drives)
        else:
            self.usb_combo.addItem("No removable drives found")

    def _log(self, msg: str):
        self.log.append(msg)
        self.log.moveCursor(QTextCursor.End)

    def install(self):
        self.install_btn.setEnabled(False)
        self.log.clear()
        self.progress.setValue(0)

        # Sync USB path
        if not self.local_radio.isChecked():
            self.cfg.usb_path = self.usb_combo.currentText()
            self.cfg.deploy_target = "usb"
        else:
            self.cfg.deploy_target = "local"

        pull   = self.pull_models_chk.isChecked()
        launch = self.start_after_chk.isChecked()

        def _do_install(log=None):
            import os, sys
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

            def _l(m): log(m); self.progress.setValue(min(self.progress.value() + 8, 95))

            # 1. Write .env
            _l("Writing .env…")
            from installer.core.env_writer import write_env
            env_path = os.path.join(project_root, ".env")
            write_env(env_path, self.cfg.to_env_dict())
            _l(f"  ✓ Written: {env_path}")

            # 2. Generate docker-compose.yml
            _l("Generating docker-compose.yml…")
            from installer.core.compose_builder import build_compose, write_compose
            compose = build_compose(
                ollama_port=self.cfg.ollama_port,
                qdrant_port=self.cfg.qdrant_port,
                dashboard_port=self.cfg.dashboard_port,
                data_dir=self.cfg.data_dir,
                include_ollama=self.cfg.include_ollama,
                include_qdrant=self.cfg.include_qdrant,
                use_gpu=self.cfg.gpu_available,
            )
            compose_path = os.path.join(project_root, "docker-compose.yml")
            write_compose(compose_path, compose)
            _l(f"  ✓ Written: {compose_path}")

            # 3. Save services registry
            _l("Saving service registry…")
            from installer.core.service_detector import save_registry
            registry_path = os.path.join(project_root, "services.json")
            save_registry(registry_path, {
                "ollama_port":    self.cfg.ollama_port,
                "qdrant_port":    self.cfg.qdrant_port,
                "dashboard_port": self.cfg.dashboard_port,
                "mode":           self.cfg.mode,
            })
            _l(f"  ✓ Written: {registry_path}")

            # 4. USB deploy
            if self.cfg.deploy_target == "usb":
                _l(f"\nDeploying to USB: {self.cfg.usb_path}…")
                from installer.core.usb_deployer import deploy_to_usb
                deploy_to_usb(
                    source_dir=project_root,
                    usb_path=self.cfg.usb_path,
                    config={
                        **self.cfg.to_env_dict(),
                        "ollama_port":    self.cfg.ollama_port,
                        "qdrant_port":    self.cfg.qdrant_port,
                        "dashboard_port": self.cfg.dashboard_port,
                        "include_ollama": self.cfg.include_ollama,
                        "include_qdrant": self.cfg.include_qdrant,
                    },
                    log=_l,
                )

            # 5. Docker compose up
            if launch and self.cfg.deploy_target == "local":
                _l("\nStarting Docker stack…")
                try:
                    proc = subprocess.Popen(
                        ["docker", "compose", "up", "-d", "--build"],
                        cwd=project_root,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                    )
                    for line in proc.stdout:
                        _l(line.rstrip())
                    proc.wait()
                    if proc.returncode == 0:
                        _l("✓ Docker stack started.")
                    else:
                        _l(f"⚠ docker compose exited with code {proc.returncode}")
                except FileNotFoundError:
                    _l("⚠ Docker not found. Start the stack manually: docker compose up -d")
                except Exception as e:
                    _l(f"⚠ {e}")

            # 6. Pull models
            if pull and self.cfg.include_ollama:
                for model in [self.cfg.llm_model, self.cfg.embed_model]:
                    if not model:
                        continue
                    _l(f"\nPulling model: {model}…")
                    try:
                        proc = subprocess.Popen(
                            ["docker", "exec", "-i",
                             "biznode_fixed_ollama_1",
                             "ollama", "pull", model],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                            text=True,
                        )
                        for line in proc.stdout:
                            _l(line.rstrip())
                        _l(f"✓ {model} ready." if proc.returncode == 0
                           else f"⚠ Pull exited with {proc.returncode}")
                    except Exception as e:
                        _l(f"⚠ Could not pull {model}: {e}")

            self.progress.setValue(100)

        self._worker = Worker(_do_install)
        self._worker.progress.connect(self._log)
        self._worker.finished.connect(self._on_done)
        self._worker.start()

    def _on_done(self, ok: bool):
        self.install_btn.setEnabled(True)
        if ok:
            self._log("\n✅  Installation complete!")
        else:
            self._log("\n❌  Installation encountered errors. See log above.")


# ---------------------------------------------------------------------------
# PAGE 5 – Complete
# ---------------------------------------------------------------------------

class CompletePage(QWidget):
    def __init__(self, cfg: InstallerConfig):
        super().__init__()
        self.cfg = cfg

        lay = QVBoxLayout(self)
        lay.setContentsMargins(60, 60, 60, 60)
        lay.setAlignment(Qt.AlignCenter)

        icon = _label("✅", size=48, color=_GREEN)
        icon.setAlignment(Qt.AlignCenter)
        lay.addWidget(icon)
        lay.addSpacing(12)

        lay.addWidget(_label("BizNode Installed!", bold=True, size=22))
        lay.addSpacing(8)

        self.summary = _label("", size=12, color=_MUTED)
        self.summary.setAlignment(Qt.AlignCenter)
        lay.addWidget(self.summary)
        lay.addSpacing(24)

        # Action buttons
        btn_row = QWidget()
        btn_lay = QHBoxLayout(btn_row)
        btn_lay.setAlignment(Qt.AlignCenter)
        btn_lay.setSpacing(12)

        self.open_btn = QPushButton("🌐  Open Dashboard")
        self.open_btn.setObjectName("primary")
        self.open_btn.clicked.connect(self._open_dashboard)
        btn_lay.addWidget(self.open_btn)

        self.close_btn = QPushButton("Close Installer")
        self.close_btn.clicked.connect(QApplication.instance().quit)
        btn_lay.addWidget(self.close_btn)
        lay.addWidget(btn_row)

    def on_show(self):
        self.summary.setText(
            f"Dashboard: http://localhost:{self.cfg.dashboard_port}\n"
            f"Mode: {self.cfg.mode.title()}\n"
            f"Ollama port: {self.cfg.ollama_port}   "
            f"Qdrant port: {self.cfg.qdrant_port}"
        )

    def _open_dashboard(self):
        import webbrowser
        webbrowser.open(f"http://localhost:{self.cfg.dashboard_port}")


# ---------------------------------------------------------------------------
# Main window
# ---------------------------------------------------------------------------

_STEPS = [
    "Welcome",
    "Diagnostics",
    "Services",
    "Configure",
    "Install",
    "Complete",
]


class InstallerWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.cfg = InstallerConfig()
        self.setWindowTitle("BizNode Installer")
        self.setMinimumSize(900, 640)
        self.resize(960, 680)

        # Central splitter: sidebar | content
        root = QWidget()
        self.setCentralWidget(root)
        root_lay = QHBoxLayout(root)
        root_lay.setContentsMargins(0, 0, 0, 0)
        root_lay.setSpacing(0)

        # ── Sidebar ──
        self._sidebar = QWidget()
        self._sidebar.setFixedWidth(168)
        self._sidebar.setStyleSheet(f"background-color: {_PANEL}; border-right: 1px solid {_BORDER};")
        sb_lay = QVBoxLayout(self._sidebar)
        sb_lay.setContentsMargins(12, 20, 12, 20)
        sb_lay.setSpacing(6)

        brand = _label("⬡ BizNode", bold=True, size=14, color=_ACCENT)
        sb_lay.addWidget(brand)
        sb_lay.addWidget(_hline())
        sb_lay.addSpacing(8)

        self._step_btns: List[QPushButton] = []
        for i, name in enumerate(_STEPS):
            btn = QPushButton(f"  {i + 1}. {name}")
            btn.setCheckable(True)
            btn.setStyleSheet("""
                QPushButton { text-align: left; border: none; border-radius: 6px;
                              padding: 8px 10px; color: #9ca3af; background: transparent; }
                QPushButton:checked { background-color: #6366f1; color: white; font-weight: bold; }
                QPushButton:hover:!checked { background-color: #2a2d3a; }
            """)
            btn.setEnabled(False)
            self._step_btns.append(btn)
            sb_lay.addWidget(btn)

        sb_lay.addStretch()
        ver_lbl = _label("v2.0  ·  Apache 2.0", size=9, color=_MUTED)
        ver_lbl.setAlignment(Qt.AlignCenter)
        sb_lay.addWidget(ver_lbl)

        root_lay.addWidget(self._sidebar)

        # ── Right side: pages + bottom bar ──
        right = QWidget()
        right_lay = QVBoxLayout(right)
        right_lay.setContentsMargins(0, 0, 0, 0)
        right_lay.setSpacing(0)

        self._stack = QStackedWidget()
        self._pages = [
            WelcomePage(self.cfg),
            DiagnosticsPage(self.cfg),
            ServicesPage(self.cfg),
            ConfigPage(self.cfg),
            DeployPage(self.cfg),
            CompletePage(self.cfg),
        ]
        for p in self._pages:
            self._stack.addWidget(p)

        right_lay.addWidget(self._stack)

        # Bottom bar
        bar = QWidget()
        bar.setStyleSheet(f"background-color: {_PANEL}; border-top: 1px solid {_BORDER};")
        bar.setFixedHeight(56)
        bar_lay = QHBoxLayout(bar)
        bar_lay.setContentsMargins(20, 8, 20, 8)

        self.back_btn = QPushButton("← Back")
        self.back_btn.setFixedWidth(90)
        self.back_btn.clicked.connect(self.prev_page)

        self.next_btn = QPushButton("Next →")
        self.next_btn.setObjectName("primary")
        self.next_btn.setFixedWidth(110)
        self.next_btn.clicked.connect(self.next_page)

        bar_lay.addWidget(self.back_btn)
        bar_lay.addStretch()
        bar_lay.addWidget(self.next_btn)
        right_lay.addWidget(bar)
        root_lay.addWidget(right)

        self._current = 0
        self._go_to(0)

    # ------------------------------------------------------------------
    def _go_to(self, idx: int):
        self._current = idx
        self._stack.setCurrentIndex(idx)

        # Sidebar highlights
        for i, btn in enumerate(self._step_btns):
            btn.setChecked(i == idx)
            btn.setEnabled(i <= idx)

        self.back_btn.setEnabled(idx > 0)
        self.next_btn.setText("Finish" if idx == len(_STEPS) - 1 else "Next →")
        self.next_btn.setEnabled(idx < len(_STEPS) - 1 or idx == len(_STEPS) - 1)

        # Call on_show if page defines it
        page = self._pages[idx]
        if hasattr(page, "on_show"):
            page.on_show()

    def next_page(self):
        # Sync config before leaving ConfigPage
        if self._current == 3:
            self._pages[3].sync_to_config()

        if self._current < len(_STEPS) - 1:
            self._go_to(self._current + 1)
        else:
            QApplication.instance().quit()

    def prev_page(self):
        if self._current > 0:
            self._go_to(self._current - 1)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    from installer.core.instance_guard import InstanceGuard
    guard = InstanceGuard()
    if not guard.acquire():
        app_check = QApplication.instance() or QApplication(sys.argv)
        QMessageBox.warning(
            None,
            "BizNode Installer",
            "Another instance of the BizNode Installer is already running.",
        )
        sys.exit(1)

    app = QApplication(sys.argv)
    app.setApplicationName("BizNode Installer")
    app.setStyleSheet(_QSS)

    window = InstallerWindow()
    window.show()

    ret = app.exec()
    guard.release()
    sys.exit(ret)


if __name__ == "__main__":
    main()
