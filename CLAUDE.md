# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

"Eco" is a local/offline audio-video transcription tool built on `faster-whisper`. There is no shared package structure — the repo is two independent, self-contained Python scripts that each implement their own transcription logic:

- **`app.py`** — a PySide6 desktop GUI ("Eco"). Drag-and-drop files, live transcription preview, per-app config at `~/.eco/config.json`.
- **`transcrever.py`** — a CLI batch tool ("Scharff Transcrição"). Watches an `entrada/` (input) folder, writes to `saida/` (output), archives processed sources to `processados/`. Launched on Windows via **`ANALISAR.bat`**. Its docstring states its purpose explicitly: it exists so Claude can "see/hear" audio/video content by reading the generated transcript (and, for video, extracted frame images) instead of a person needing to describe them.

There is no `requirements.txt`, `pyproject.toml`, test suite, linter config, or CI — dependencies are only discoverable via `import` statements in the two scripts.

## Running the tools

```bash
# GUI app
python app.py

# CLI batch tool (processes everything currently in entrada/)
python transcrever.py
python transcrever.py --model medium --interval 4 --srt
python transcrever.py --cpu          # force CPU instead of CUDA
python transcrever.py --no-frames    # skip video frame extraction
```

On Windows, `ANALISAR.bat` is the intended entry point for `transcrever.py` (sets UTF-8 code page, cds into the script dir, runs it, pauses on exit).

There are no build, lint, or test commands in this repo — none are configured.

### Runtime dependencies (inferred from imports, not pinned anywhere)

`PySide6`, `faster-whisper`, `huggingface_hub`, `ctranslate2`, `imageio_ffmpeg`. When adding a dependency, there's no manifest to update — just the imports.

## Architecture notes

- **The two entry points do not share code.** Constants and logic like `VOCAB` (the Portuguese `initial_prompt` used to bias Whisper's output), the video/audio extension sets, and the GPU-detection/CPU-fallback pattern are each duplicated between `app.py` and `transcrever.py`. If you change transcription behavior (vocab hints, extensions, model repos, fallback logic), check whether the same change is needed in both files.
- **GPU-first with automatic CPU fallback**: both scripts try CUDA first (`float16` compute) and catch exceptions, inspecting the error string for keywords (`cuda`, `cublas`, `cudnn`, `gpu`) to decide whether to retry on CPU (`int8` compute) rather than fail. Preserve this pattern rather than hard-failing on GPU errors.
- **`app.py` structure** (PySide6, threaded via `QThread`):
  - `SetupDialog`/`SetupWorker` — first-run only, shown when `~/.eco/config.json` has no `model` key. Downloads the chosen model via `huggingface_hub.snapshot_download`, monkey-patching `tqdm` to report progress into the UI. Writes `{"model", "device"}` to config on success.
  - `TranscriptionWorker` — runs `faster_whisper.WhisperModel.transcribe` off the UI thread, emitting per-segment results (`segment` signal) so the transcript streams into the UI live.
  - `DropZone` — drag-and-drop + click-to-browse file picker, filters by `ALL_EXTS`.
  - `MainWindow` — wires everything together; supports saving results as `.txt` or `.srt`.
  - Styling is inline Qt stylesheets (`setStyleSheet`) per widget class, not an external `.qss` file.
- **`transcrever.py` structure** (procedural CLI, folder-driven):
  - `entrada/`, `saida/`, `saida/frames/<video>/`, `processados/` are created relative to the script's own directory (`BASE = dirname(__file__)`), not the CWD.
  - `processar()` is the per-run pipeline: for each file in `entrada/`, transcribe → (if video) extract frames via the `ffmpeg` binary bundled by `imageio_ffmpeg` → move source into `processados/` (de-duplicating filenames with `(2)`, `(3)`, ... suffixes).
  - Frame extraction shells out to `ffmpeg` via `subprocess.run` (`fps=1/interval` sampling), then renames frames to `t<MM>m<SS>s.jpg` for readability.
  - Files already in `processados/` are never reprocessed on subsequent runs since `processar()` only globs `entrada/`.

## Conventions

- **User-facing strings, CLI help text, code comments, and variable/function names are Brazilian Portuguese** (e.g. `carregar_modelo`, `arquivar`, `eh_erro_gpu`). Match this when editing these files.
- Model sizes are one of `large-v3` (default, ~1.5GB), `medium`, `small`, mapped to `Systran/faster-whisper-<size>` on the Hugging Face Hub (see `MODEL_REPOS` in `app.py`).
- Transcription is hardcoded to Portuguese (`language="pt"`) with `vad_filter=True` and `word_timestamps=True` in both scripts.
- `.gitignore` implies packaging with PyInstaller (`dist/`, `build/`, `*.spec`) even though no spec file is currently checked in.

## Commit convention: mark the device of origin

The repo owner works from both a phone and a home PC. **Every commit made by Claude Code must include a trailer line identifying which device the session ran on**, so it's traceable in `git log`.

Detect the device from the `CLAUDE_CODE_ENTRYPOINT` environment variable at the start of the session:
- Contains `mobile` → append `Origem: 📱 Celular`
- Otherwise (desktop app, CLI, web) → append `Origem: 💻 PC`

Add this as the last line of the commit message body (after any `Co-Authored-By`/session trailers already required by the harness), e.g.:

```
fix: corrige extração de frames em vídeos .webm

Origem: 📱 Celular
```
