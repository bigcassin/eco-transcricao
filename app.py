"""
Eco — Transcrição de Áudio e Vídeo
Interface gráfica para faster-whisper — 100% local e offline.
"""
__version__ = "1.0.0"
import sys
import json
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QProgressBar, QTextEdit, QComboBox,
    QCheckBox, QFileDialog, QListWidget, QListWidgetItem, QFrame,
    QMessageBox, QDialog,
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QFont

# ── Config ────────────────────────────────────────────────────────────────────
CONFIG_DIR  = Path.home() / ".eco"
CONFIG_FILE = CONFIG_DIR / "config.json"

MODEL_REPOS = {
    "large-v3": "Systran/faster-whisper-large-v3",
    "medium":   "Systran/faster-whisper-medium",
    "small":    "Systran/faster-whisper-small",
}

# Tamanho esperado de cada modelo em bytes (para barra de progresso)
MODEL_SIZES = {
    "large-v3": 3_100_000_000,
    "medium":   1_500_000_000,
    "small":      490_000_000,
}

VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v", ".3gp"}
AUDIO_EXTS = {".mp3", ".ogg", ".opus", ".oga", ".m4a", ".wav", ".aac", ".amr", ".flac"}
ALL_EXTS   = VIDEO_EXTS | AUDIO_EXTS

VOCAB = (
    "Transcricao em portugues brasileiro. "
    "Termos comuns: Scharff, lanches, hamburguer, cardapio, pedido, entrega, WhatsApp, "
    "Instagram, iFood, CS2, Valorant, FACEIT, stream, live, gameplay."
)


def load_config() -> dict:
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text())
    return {}


def save_config(data: dict):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(data, indent=2))


def detect_gpu() -> bool:
    try:
        import ctranslate2
        return ctranslate2.get_cuda_device_count() > 0
    except Exception:
        return False


# ── Setup Worker ──────────────────────────────────────────────────────────────
class SetupWorker(QThread):
    status   = Signal(str)
    progress = Signal(int)   # 0-100, -1 = indeterminate
    done     = Signal(str)   # model_size chosen
    error    = Signal(str)

    def __init__(self, model_size: str):
        super().__init__()
        self.model_size = model_size

    def run(self):
        try:
            from huggingface_hub import snapshot_download
            repo_id = MODEL_REPOS[self.model_size]
            self.status.emit(f"Conectando…")
            self.progress.emit(-1)
            # Download limpo — progresso é monitorado externamente via cache dir
            snapshot_download(repo_id=repo_id)
            self.progress.emit(100)
            self.status.emit("Modelo pronto!")
            self.done.emit(self.model_size)
        except Exception as e:
            self.error.emit(str(e))


# ── Setup Dialog ──────────────────────────────────────────────────────────────
class SetupDialog(QDialog):
    setup_complete = Signal(str)  # model_size

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Eco — Configuração inicial")
        self.setFixedSize(480, 340)
        self.setWindowFlag(Qt.WindowCloseButtonHint, False)
        self.worker: SetupWorker | None = None
        self._has_gpu = detect_gpu()
        self._model = "large-v3" if self._has_gpu else "small"
        self._build_ui()
        self._apply_style()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(32, 28, 32, 28)
        lay.setSpacing(14)

        # Logo / título
        title = QLabel("🎙️  Eco")
        title.setObjectName("setupTitle")
        title.setAlignment(Qt.AlignCenter)
        lay.addWidget(title)

        sub = QLabel("Transcrição de Áudio e Vídeo")
        sub.setObjectName("setupSub")
        sub.setAlignment(Qt.AlignCenter)
        lay.addWidget(sub)

        # Detecção de hardware
        gpu_icon = "✅" if self._has_gpu else "💻"
        gpu_text = "GPU detectada" if self._has_gpu else "Sem GPU — usando CPU"
        model_text = f"Modelo selecionado: <b>{self._model}</b>"
        size_text  = "(~1.5 GB)" if self._model == "large-v3" else "(~500 MB)"

        self.hw_lbl = QLabel(f"{gpu_icon}  {gpu_text}  •  {model_text}  {size_text}")
        self.hw_lbl.setObjectName("setupHw")
        self.hw_lbl.setAlignment(Qt.AlignCenter)
        self.hw_lbl.setWordWrap(True)
        lay.addWidget(self.hw_lbl)

        info = QLabel(
            "O Eco precisa baixar o modelo de IA uma única vez.\n"
            "Depois disso funciona 100% offline."
        )
        info.setObjectName("setupInfo")
        info.setAlignment(Qt.AlignCenter)
        info.setWordWrap(True)
        lay.addWidget(info)

        # Barra de progresso
        self.prog = QProgressBar()
        self.prog.setFixedHeight(20)
        self.prog.setRange(0, 100)
        self.prog.setValue(0)
        self.prog.setFormat("Aguardando…")
        lay.addWidget(self.prog)

        self.status_lbl = QLabel("")
        self.status_lbl.setObjectName("setupStatus")
        self.status_lbl.setAlignment(Qt.AlignCenter)
        lay.addWidget(self.status_lbl)

        lay.addStretch()

        # Botão
        self.btn = QPushButton("Baixar e começar")
        self.btn.setObjectName("btnSetup")
        self.btn.setFixedHeight(40)
        self.btn.clicked.connect(self._start_download)
        lay.addWidget(self.btn)

    def _apply_style(self):
        self.setStyleSheet("""
        QDialog { background: #1a1a2e; }
        QLabel { color: #ccc; font-family: 'Segoe UI', Arial, sans-serif; }
        QLabel#setupTitle { font-size: 28px; font-weight: 800; color: #fff; }
        QLabel#setupSub   { font-size: 13px; color: #666; margin-bottom: 4px; }
        QLabel#setupHw    { font-size: 13px; color: #aaa; }
        QLabel#setupInfo  { font-size: 12px; color: #666; line-height: 1.6; }
        QLabel#setupStatus{ font-size: 12px; color: #888; }
        QProgressBar {
            background: #16213e; border: 1px solid #2a2a4a;
            border-radius: 6px; text-align: center; color: #aaa; font-size: 11px;
        }
        QProgressBar::chunk {
            background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                stop:0 #0078d4, stop:1 #00bcf2);
            border-radius: 5px;
        }
        QPushButton#btnSetup {
            background: #0078d4; color: white; border: none;
            border-radius: 8px; font-size: 14px; font-weight: 700;
            font-family: 'Segoe UI', Arial, sans-serif;
        }
        QPushButton#btnSetup:hover { background: #1084de; }
        QPushButton#btnSetup:disabled { background: #252540; color: #555; }
        """)

    def _cache_dir(self) -> Path:
        name = MODEL_REPOS[self._model].replace("/", "--")
        return Path.home() / ".cache" / "huggingface" / "hub" / f"models--{name}"

    def _cache_size(self) -> int:
        d = self._cache_dir()
        if not d.exists():
            return 0
        total = 0
        for f in d.rglob("*"):
            try:
                if f.is_file():
                    total += f.stat().st_size
            except Exception:
                pass
        return total

    def _start_download(self):
        self.btn.setEnabled(False)
        self.btn.setText("Baixando…")
        self.prog.setRange(0, 100)
        self.prog.setValue(0)

        # Timer que monitora o cache a cada segundo
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._poll_progress)
        self._timer.start()

        self.worker = SetupWorker(self._model)
        self.worker.status.connect(self.status_lbl.setText)
        self.worker.progress.connect(self._on_progress)
        self.worker.done.connect(self._on_done)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _poll_progress(self):
        downloaded = self._cache_size()
        expected   = MODEL_SIZES.get(self._model, 1)
        pct = min(int(downloaded / expected * 100), 99)
        self.prog.setValue(pct)
        mb = downloaded / 1_000_000
        total_mb = expected / 1_000_000
        self.prog.setFormat(f"{mb:.0f} MB / {total_mb:.0f} MB  ({pct}%)")
        self.status_lbl.setText(f"Baixando modelo {self._model}…")

    def _on_progress(self, pct: int):
        if pct == -1:
            self.prog.setRange(0, 0)
            self.prog.setFormat("Conectando…")
        else:
            self.prog.setRange(0, 100)

    def _on_done(self, model_size: str):
        if hasattr(self, "_timer"):
            self._timer.stop()
        self.prog.setRange(0, 100)
        self.prog.setValue(100)
        self.prog.setFormat("✅ Pronto!")
        self.btn.setText("Abrindo Eco…")
        save_config({"model": model_size, "device": "cuda" if self._has_gpu else "cpu"})
        self.setup_complete.emit(model_size)
        self.accept()

    def _on_error(self, msg: str):
        if hasattr(self, "_timer"):
            self._timer.stop()
        self.btn.setEnabled(True)
        self.btn.setText("Tentar novamente")
        self.status_lbl.setText(f"Erro: {msg}")
        self.prog.setRange(0, 100)
        self.prog.setValue(0)
        self.prog.setFormat("Erro — tente novamente")


# ── Transcription Worker ──────────────────────────────────────────────────────
class TranscriptionWorker(QThread):
    progress = Signal(int, int)
    segment  = Signal(str, str)
    log      = Signal(str)
    finished = Signal(dict)
    error    = Signal(str)

    def __init__(self, files, model_size, device="cuda"):
        super().__init__()
        self.files = files
        self.model_size = model_size
        self.device = device
        self._stop = False

    def stop(self):
        self._stop = True

    def run(self):
        try:
            from faster_whisper import WhisperModel
            compute = "float16" if self.device == "cuda" else "int8"
            self.log.emit(f"Carregando {self.model_size}…")
            try:
                model = WhisperModel(self.model_size, device=self.device, compute_type=compute)
            except Exception as e:
                if any(k in str(e).lower() for k in ("cuda", "cublas", "cudnn", "gpu")):
                    self.log.emit("GPU indisponível — usando CPU…")
                    model = WhisperModel(self.model_size, device="cpu", compute_type="int8")
                else:
                    raise

            self.log.emit("Modelo pronto. Iniciando…")
            results = {}

            for idx, path in enumerate(self.files):
                if self._stop:
                    break
                fname = Path(path).name
                self.progress.emit(idx, len(self.files))
                self.log.emit(f"Transcrevendo: {fname}")

                segments, info = model.transcribe(
                    path, language="pt", vad_filter=True,
                    initial_prompt=VOCAB, word_timestamps=True,
                )
                lines, words = [], []
                for seg in segments:
                    if self._stop:
                        break
                    s = int(seg.start)
                    line = f"[{s//60:02d}:{s%60:02d}] {seg.text.strip()}"
                    lines.append(line)
                    words.append(seg.text.strip())
                    self.segment.emit(fname, line)

                results[fname] = {"lines": lines, "text": " ".join(words), "path": path}

            self.progress.emit(len(self.files), len(self.files))
            self.finished.emit(results)

        except Exception as e:
            self.error.emit(str(e))


# ── Drop Zone ─────────────────────────────────────────────────────────────────
class DropZone(QFrame):
    files_dropped = Signal(list)

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setMinimumHeight(110)
        self.setCursor(Qt.PointingHandCursor)
        self.setObjectName("dropZone")
        lay = QVBoxLayout(self)
        lay.setAlignment(Qt.AlignCenter)
        lay.setSpacing(4)
        icon = QLabel("🎙️")
        icon.setFont(QFont("Segoe UI Emoji", 28))
        icon.setAlignment(Qt.AlignCenter)
        self.lbl = QLabel("Arraste arquivos aqui  ou  clique para selecionar")
        self.lbl.setObjectName("dropMain")
        self.lbl.setAlignment(Qt.AlignCenter)
        hint = QLabel("MP3 · OGG · OPUS · WAV · M4A · FLAC · MP4 · MKV · e mais")
        hint.setObjectName("dropHint")
        hint.setAlignment(Qt.AlignCenter)
        lay.addWidget(icon)
        lay.addWidget(self.lbl)
        lay.addWidget(hint)

    def _valid(self, mime):
        return [u.toLocalFile() for u in mime.urls()
                if Path(u.toLocalFile()).suffix.lower() in ALL_EXTS]

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls() and self._valid(e.mimeData()):
            e.acceptProposedAction()
            self.setProperty("hover", "true"); self._refresh()
        else:
            e.ignore()

    def dragLeaveEvent(self, e):
        self.setProperty("hover", "false"); self._refresh()

    def dropEvent(self, e):
        self.setProperty("hover", "false"); self._refresh()
        paths = self._valid(e.mimeData())
        if paths:
            self.files_dropped.emit(paths)

    def mousePressEvent(self, e):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Selecionar arquivos",
            str(Path.home()),
            "Áudio / Vídeo (*.mp3 *.ogg *.opus *.m4a *.wav *.aac *.flac "
            "*.mp4 *.mov *.mkv *.avi *.webm);;Todos os arquivos (*)",
        )
        if paths:
            self.files_dropped.emit(paths)

    def _refresh(self):
        self.style().unpolish(self); self.style().polish(self)


# ── Main Window ───────────────────────────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self, config: dict):
        super().__init__()
        self.files: list[str] = []
        self.worker: TranscriptionWorker | None = None
        self.results: dict = {}
        self.cfg = config
        self._build_ui()
        self._apply_style()
        self.setWindowTitle(f"Eco v{__version__} — Transcrição de Áudio e Vídeo")
        self.setMinimumSize(740, 640)
        self.resize(820, 720)

    def _build_ui(self):
        root_w = QWidget()
        self.setCentralWidget(root_w)
        lay = QVBoxLayout(root_w)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(10)

        hdr = QHBoxLayout()
        title = QLabel("🎙️  Eco")
        title.setObjectName("title")
        hdr.addWidget(title)
        hdr.addStretch()
        device_tag = "GPU" if self.cfg.get("device") == "cuda" else "CPU"
        model_tag = self.cfg.get("model", "large-v3")
        tag = QLabel(f"v{__version__}  ·  {device_tag}  ·  {model_tag}")
        tag.setObjectName("tag")
        hdr.addWidget(tag)
        lay.addLayout(hdr)

        self.drop = DropZone()
        self.drop.files_dropped.connect(self.add_files)
        lay.addWidget(self.drop)

        self.file_list = QListWidget()
        self.file_list.setObjectName("fileList")
        self.file_list.setFixedHeight(110)
        lay.addWidget(self.file_list)

        ctrl = QHBoxLayout()
        ctrl.setSpacing(10)
        ctrl.addWidget(QLabel("Modelo:"))
        self.model_combo = QComboBox()
        self.model_combo.addItems(["large-v3", "medium", "small"])
        self.model_combo.setCurrentText(self.cfg.get("model", "large-v3"))
        self.model_combo.setFixedWidth(120)
        ctrl.addWidget(self.model_combo)
        self.srt_check = QCheckBox("Gerar .srt")
        ctrl.addWidget(self.srt_check)
        ctrl.addStretch()
        self.btn_clear = QPushButton("Limpar")
        self.btn_clear.setObjectName("btnSec")
        self.btn_clear.clicked.connect(self.clear_files)
        ctrl.addWidget(self.btn_clear)
        self.btn_start = QPushButton("▶  Transcrever")
        self.btn_start.setObjectName("btnPrimary")
        self.btn_start.setFixedHeight(36)
        self.btn_start.clicked.connect(self.toggle_transcription)
        ctrl.addWidget(self.btn_start)
        lay.addLayout(ctrl)

        self.progress = QProgressBar()
        self.progress.setFormat("Aguardando arquivos…")
        self.progress.setValue(0)
        self.progress.setFixedHeight(22)
        lay.addWidget(self.progress)

        self.status_lbl = QLabel("")
        self.status_lbl.setObjectName("statusLbl")
        lay.addWidget(self.status_lbl)

        res_hdr = QLabel("RESULTADO")
        res_hdr.setObjectName("secLabel")
        lay.addWidget(res_hdr)

        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setObjectName("resultText")
        self.result_text.setPlaceholderText("A transcrição aparece aqui em tempo real…")
        lay.addWidget(self.result_text, stretch=1)

        act = QHBoxLayout()
        self.btn_copy = QPushButton("📋  Copiar texto")
        self.btn_copy.setObjectName("btnAct")
        self.btn_copy.clicked.connect(self.copy_text)
        self.btn_copy.setEnabled(False)
        act.addWidget(self.btn_copy)
        self.btn_save = QPushButton("💾  Salvar .txt")
        self.btn_save.setObjectName("btnAct")
        self.btn_save.clicked.connect(self.save_txt)
        self.btn_save.setEnabled(False)
        act.addWidget(self.btn_save)
        self.btn_save_srt = QPushButton("💾  Salvar .srt")
        self.btn_save_srt.setObjectName("btnAct")
        self.btn_save_srt.clicked.connect(self.save_srt)
        self.btn_save_srt.setEnabled(False)
        act.addWidget(self.btn_save_srt)
        act.addStretch()
        lay.addLayout(act)

    def _apply_style(self):
        self.setStyleSheet("""
        QMainWindow, QWidget {
            background: #1a1a2e; color: #e0e0e0;
            font-family: 'Segoe UI', Arial, sans-serif; font-size: 13px;
        }
        QLabel { color: #c0c0c0; }
        QLabel#title { font-size: 17px; font-weight: 700; color: #fff; }
        QLabel#tag { font-size: 11px; color: #555; }
        QLabel#secLabel { font-size: 10px; font-weight: 700; color: #555; letter-spacing: 1.5px; }
        QLabel#statusLbl { font-size: 12px; color: #888; }
        QFrame#dropZone {
            border: 2px dashed #35355a; border-radius: 12px; background: #16213e;
        }
        QFrame#dropZone[hover="true"] { border-color: #0078d4; background: #0d1e35; }
        QFrame#dropZone:hover { border-color: #46466a; }
        QLabel#dropMain { font-size: 13px; font-weight: 600; color: #ccc; }
        QLabel#dropHint { font-size: 11px; color: #555; }
        QListWidget#fileList {
            background: #16213e; border: 1px solid #2a2a4a;
            border-radius: 8px; color: #ccc; padding: 4px;
        }
        QListWidget#fileList::item { padding: 5px 8px; border-radius: 4px; }
        QListWidget#fileList::item:selected { background: #0078d4; color: #fff; }
        QListWidget#fileList::item:hover { background: #1e2e4a; }
        QComboBox {
            background: #16213e; border: 1px solid #2a2a4a;
            border-radius: 6px; padding: 5px 10px; color: #ddd;
        }
        QComboBox::drop-down { border: none; width: 20px; }
        QComboBox QAbstractItemView {
            background: #1e2040; border: 1px solid #3a3a6a; color: #ddd;
        }
        QComboBox QAbstractItemView::item:selected { background: #0078d4; }
        QCheckBox { color: #bbb; spacing: 6px; }
        QCheckBox::indicator {
            width: 15px; height: 15px; border: 1px solid #3a3a5a;
            border-radius: 3px; background: #16213e;
        }
        QCheckBox::indicator:checked { background: #0078d4; border-color: #0078d4; }
        QProgressBar {
            background: #16213e; border: 1px solid #2a2a4a;
            border-radius: 6px; text-align: center; color: #aaa; font-size: 11px;
        }
        QProgressBar::chunk {
            background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                stop:0 #0078d4, stop:1 #00bcf2);
            border-radius: 5px;
        }
        QTextEdit#resultText {
            background: #16213e; border: 1px solid #2a2a4a;
            border-radius: 8px; color: #ddd; padding: 10px;
            font-family: 'Consolas', 'Courier New', monospace; font-size: 13px;
        }
        QPushButton#btnPrimary {
            background: #0078d4; color: #fff; border: none;
            border-radius: 6px; padding: 8px 22px; font-weight: 700;
        }
        QPushButton#btnPrimary:hover { background: #1084de; }
        QPushButton#btnPrimary:pressed { background: #006cbd; }
        QPushButton#btnPrimary:disabled { background: #252540; color: #555; }
        QPushButton#btnSec {
            background: #252545; color: #bbb; border: 1px solid #35355a;
            border-radius: 6px; padding: 6px 14px;
        }
        QPushButton#btnSec:hover { background: #2d2d55; }
        QPushButton#btnAct {
            background: #1e1e3a; color: #bbb; border: 1px solid #2a2a4a;
            border-radius: 6px; padding: 6px 14px;
        }
        QPushButton#btnAct:hover { background: #252550; color: #fff; }
        QPushButton#btnAct:disabled { color: #3a3a5a; border-color: #1e1e35; }
        QScrollBar:vertical { background: #16213e; width: 8px; }
        QScrollBar::handle:vertical {
            background: #35355a; border-radius: 4px; min-height: 24px;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
        """)

    def add_files(self, paths):
        existing = set(self.files)
        for p in paths:
            if p not in existing:
                self.files.append(p); existing.add(p)
                icon = "🎬" if Path(p).suffix.lower() in VIDEO_EXTS else "🎵"
                self.file_list.addItem(QListWidgetItem(f"{icon}  {Path(p).name}"))
        self.status_lbl.setText(f"{len(self.files)} arquivo(s) na fila.")
        self.progress.setFormat(f"{len(self.files)} arquivo(s) prontos")

    def clear_files(self):
        self.files.clear(); self.file_list.clear()
        self.status_lbl.setText("")
        self.progress.setValue(0)
        self.progress.setFormat("Aguardando arquivos…")

    def toggle_transcription(self):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.btn_start.setText("▶  Transcrever")
            self.status_lbl.setText("Interrompido.")
            return
        if not self.files:
            QMessageBox.information(self, "Sem arquivos",
                "Adicione arquivos de áudio ou vídeo antes de transcrever.")
            return
        self.result_text.clear(); self.results = {}
        self.progress.setValue(0); self.progress.setMaximum(len(self.files))
        self.btn_start.setText("⏹  Parar")
        self.btn_copy.setEnabled(False)
        self.btn_save.setEnabled(False)
        self.btn_save_srt.setEnabled(False)
        self.worker = TranscriptionWorker(
            files=list(self.files),
            model_size=self.model_combo.currentText(),
            device=self.cfg.get("device", "cuda"),
        )
        self.worker.progress.connect(lambda c, t: (
            self.progress.setValue(c),
            self.progress.setFormat(f"Arquivo {c+1} de {t}…"),
        ))
        self.worker.segment.connect(lambda fn, ln: (
            self.result_text.append(
                f'<span style="color:#555;font-size:11px">{fn}</span><br>'
                f'<span style="color:#ddd">{ln}</span><br>'
            ),
            self.result_text.ensureCursorVisible(),
        ))
        self.worker.log.connect(self.status_lbl.setText)
        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _on_finished(self, results):
        self.results = results
        self.progress.setFormat(f"✅  {len(results)} arquivo(s) transcritos")
        self.progress.setValue(self.progress.maximum())
        self.status_lbl.setText(f"Concluído — {len(results)} arquivo(s).")
        self.btn_start.setText("▶  Transcrever")
        self.btn_copy.setEnabled(True)
        self.btn_save.setEnabled(True)
        self.btn_save_srt.setEnabled(self.srt_check.isChecked())

    def _on_error(self, msg):
        self.status_lbl.setText(f"Erro: {msg}")
        self.btn_start.setText("▶  Transcrever")
        QMessageBox.critical(self, "Erro na transcrição", msg)

    def copy_text(self):
        QApplication.clipboard().setText(self.result_text.toPlainText())
        self.status_lbl.setText("Texto copiado.")

    def save_txt(self):
        if not self.results: return
        path, _ = QFileDialog.getSaveFileName(
            self, "Salvar transcrição", str(Path.home() / "transcricao.txt"),
            "Arquivo de texto (*.txt)")
        if not path: return
        with open(path, "w", encoding="utf-8") as f:
            for fname, data in self.results.items():
                f.write(f"# {fname}\n\n")
                f.write("\n".join(data["lines"]))
                f.write("\n\n== TEXTO CORRIDO ==\n")
                f.write(data["text"])
                f.write("\n\n" + "─" * 60 + "\n\n")
        self.status_lbl.setText(f"Salvo: {Path(path).name}")

    def save_srt(self):
        if not self.results: return
        path, _ = QFileDialog.getSaveFileName(
            self, "Salvar legenda", str(Path.home() / "transcricao.srt"),
            "Legenda SRT (*.srt)")
        if not path: return
        def ts(s):
            h, r = divmod(float(s.split(":")[0])*60 + float(s.split(":")[1]), 60)
            return f"00:{int(h):02d}:{int(r):02d},000"
        with open(path, "w", encoding="utf-8") as f:
            idx = 1
            for data in self.results.values():
                for line in data["lines"]:
                    f.write(f"{idx}\n00:00:00,000 --> 00:00:05,000\n{line}\n\n")
                    idx += 1
        self.status_lbl.setText(f"Salvo: {Path(path).name}")

    def closeEvent(self, e):
        if self.worker and self.worker.isRunning():
            self.worker.stop(); self.worker.wait(3000)
        e.accept()


# ── Entry point ───────────────────────────────────────────────────────────────
def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Eco")

    config = load_config()

    if "model" not in config:
        # Primeira execução — mostra setup
        dlg = SetupDialog()
        if dlg.exec() != QDialog.Accepted:
            sys.exit(0)
        config = load_config()

    win = MainWindow(config)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
