r"""
Transcreve videos E audios (fala -> texto com tempo) e, nos videos, extrai frames
(a tela em imagens) — pra o Claude "ver/ouvir" sem ninguem digitar o conteudo.

Tudo LOCAL e OFFLINE (faster-whisper + ffmpeg embutido). Nada sobe pra internet.

Como usar:
  1) Jogue os arquivos (video ou audio) em:  entrada\
  2) De 2 cliques no ANALISAR.bat (ou: python transcrever.py)
  3) Saida em:                               saida\
        - <arquivo>.txt          -> transcricao com marcacao de tempo [mm:ss]
        - frames\<video>\*.jpg   -> prints da tela a cada N segundos (so pra video)
  4) Arquivo de origem vai pra processados\ (nao reprocessa na proxima rodada)

Opcoes:
  --interval 4      -> 1 frame a cada 4 segundos (padrao 4)
  --model large-v3  -> small | medium | large-v3 (padrao: large-v3)
  --no-frames       -> nao extrair imagens (so transcricao)
  --cpu             -> forcar CPU (fallback automatico se GPU falhar)
  --srt             -> gerar tambem arquivo .srt (legendas)
"""
import os, subprocess, argparse, glob, shutil

os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

BASE     = os.path.dirname(os.path.abspath(__file__))
IN_DIR   = os.path.join(BASE, "entrada")
OUT_DIR  = os.path.join(BASE, "saida")
PROC_DIR = os.path.join(BASE, "processados")
FRAMES_DIR = os.path.join(OUT_DIR, "frames")

VIDEO_EXTS = (".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v", ".3gp")
AUDIO_EXTS = (".mp3", ".ogg", ".opus", ".oga", ".m4a", ".wav", ".aac", ".amr", ".flac")

# Edite com termos/nomes do seu contexto — melhora muito a grafia de jargao
VOCAB = (
    "Transcricao em portugues brasileiro. "
    "Termos comuns: Scharff, lanches, hamburguer, cardapio, pedido, entrega, WhatsApp, "
    "Instagram, iFood, CS2, Valorant, FACEIT, stream, live, gameplay."
)


def hms(s: float) -> str:
    s = int(s)
    return f"{s // 60:02d}:{s % 60:02d}"


def srt_time(s: float) -> str:
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    ms = int((sec % 1) * 1000)
    return f"{int(h):02d}:{int(m):02d}:{int(sec):02d},{ms:03d}"


def carregar_modelo(model_size: str, device: str):
    from faster_whisper import WhisperModel
    compute = "float16" if device == "cuda" else "int8"
    print(f"  Carregando '{model_size}' em {device} ({compute})...")
    m = WhisperModel(model_size, device=device, compute_type=compute)
    print(f"  Modelo pronto.")
    return m


def transcrever(model, path: str, out_txt: str, out_srt: str | None):
    segments, info = model.transcribe(
        path, language="pt", vad_filter=True,
        initial_prompt=VOCAB, word_timestamps=True
    )

    linhas_txt, texto_corrido, linhas_srt = [], [], []
    idx = 1
    for seg in segments:
        linhas_txt.append(f"[{hms(seg.start)} -> {hms(seg.end)}] {seg.text.strip()}")
        texto_corrido.append(seg.text.strip())
        print(f"    [{hms(seg.start)}] {seg.text.strip()}")
        if out_srt:
            linhas_srt.append(f"{idx}\n{srt_time(seg.start)} --> {srt_time(seg.end)}\n{seg.text.strip()}\n")
            idx += 1

    with open(out_txt, "w", encoding="utf-8") as f:
        f.write(f"# Transcricao: {os.path.basename(path)}\n")
        f.write(f"# Duracao ~{hms(info.duration)} | idioma: {info.language}\n\n")
        f.write("== POR TEMPO ==\n")
        f.write("\n".join(linhas_txt))
        f.write("\n\n== TEXTO CORRIDO ==\n")
        f.write(" ".join(texto_corrido))

    if out_srt:
        with open(out_srt, "w", encoding="utf-8") as f:
            f.write("\n".join(linhas_srt))
        print(f"    SRT salvo: {out_srt}")


def extrair_frames(ffmpeg: str, video_path: str, dest: str, interval: int):
    os.makedirs(dest, exist_ok=True)
    cmd = [ffmpeg, "-y", "-i", video_path, "-vf",
           f"fps=1/{interval},scale=1280:-1", "-q:v", "3",
           os.path.join(dest, "f_%04d.jpg")]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    frames = sorted(glob.glob(os.path.join(dest, "f_*.jpg")))
    for i, fp in enumerate(frames):
        t = i * interval
        os.replace(fp, os.path.join(dest, f"t{t // 60:02d}m{t % 60:02d}s.jpg"))
    print(f"    {len(frames)} frames -> {dest}")


def arquivar(p: str):
    os.makedirs(PROC_DIR, exist_ok=True)
    base = os.path.basename(p)
    dest = os.path.join(PROC_DIR, base)
    if os.path.exists(dest):
        nome, ext = os.path.splitext(base)
        i = 2
        while os.path.exists(os.path.join(PROC_DIR, f"{nome} ({i}){ext}")):
            i += 1
        dest = os.path.join(PROC_DIR, f"{nome} ({i}){ext}")
    shutil.move(p, dest)
    print(f"    Arquivado -> processados/{os.path.basename(dest)}")


def processar(model, arquivos, ffmpeg, interval, srt):
    for p in arquivos:
        nome = os.path.splitext(os.path.basename(p))[0]
        eh_video = p.lower().endswith(VIDEO_EXTS)
        print(f"\n>>> {os.path.basename(p)} ({'video' if eh_video else 'audio'})")
        out_txt = os.path.join(OUT_DIR, f"{nome}.txt")
        out_srt = os.path.join(OUT_DIR, f"{nome}.srt") if srt else None
        transcrever(model, p, out_txt, out_srt)
        if eh_video and ffmpeg:
            extrair_frames(ffmpeg, p, os.path.join(FRAMES_DIR, nome), interval)
        arquivar(p)


def eh_erro_gpu(e: Exception) -> bool:
    return any(k in str(e).lower() for k in ("cublas", "cudnn", "cuda", "gpu", "device"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--interval", type=int, default=4)
    ap.add_argument("--model", default="large-v3")
    ap.add_argument("--no-frames", action="store_true")
    ap.add_argument("--cpu", action="store_true")
    ap.add_argument("--srt", action="store_true")
    args = ap.parse_args()

    os.makedirs(IN_DIR, exist_ok=True)
    os.makedirs(OUT_DIR, exist_ok=True)

    arquivos = [p for p in glob.glob(os.path.join(IN_DIR, "*"))
                if p.lower().endswith(VIDEO_EXTS + AUDIO_EXTS)]
    if not arquivos:
        print(f"Nenhum arquivo em entrada/\nColoque os videos/audios la e rode de novo.")
        return

    n_vid = sum(1 for p in arquivos if p.lower().endswith(VIDEO_EXTS))
    print(f"{len(arquivos)} arquivo(s): {n_vid} video(s), {len(arquivos) - n_vid} audio(s).")

    ffmpeg = None
    if not args.no_frames:
        import imageio_ffmpeg
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

    device = "cpu" if args.cpu else "cuda"
    print("Carregando modelo...")
    try:
        model = carregar_modelo(args.model, device)
        processar(model, arquivos, ffmpeg, args.interval, args.srt)
    except Exception as e:
        if device == "cuda" and eh_erro_gpu(e):
            print(f"\n  GPU indisponivel ({str(e)[:90]}). Caindo pra CPU...\n")
            model = carregar_modelo(args.model, "cpu")
            processar(model, arquivos, ffmpeg, args.interval, args.srt)
        else:
            raise

    print(f"\nPronto. Saida em: saida/")
    print("Avise o Claude que os arquivos estao prontos.")


if __name__ == "__main__":
    main()
