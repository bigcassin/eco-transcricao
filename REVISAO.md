# Revisão do código — 2026-07-02

Revisão feita a pedido do dono do repo (via sessão do celular), pra conferir depois no PC.
Foco: bugs reais e melhorias que valem a pena, não estilo.

## 🔴 Alta prioridade

### 1. `app.py` — exportação de `.srt` na GUI está quebrada
`MainWindow.save_srt()` (por volta da linha 643) define uma função `ts()` para converter
o timestamp `[mm:ss]` da linha em formato SRT, **mas nunca chama essa função**. O arquivo
`.srt` gerado grava um intervalo fixo `00:00:00,000 --> 00:00:05,000` em **toda** legenda,
ignorando o tempo real de cada segmento transcrito.

Comparar com `transcrever.py`, onde `srt_time(seg.start)` / `srt_time(seg.end)` são usados
corretamente a partir dos segmentos do próprio `faster-whisper` (não da linha de texto já
formatada). O jeito mais simples de corrigir na GUI é guardar `seg.start`/`seg.end` junto
com cada linha em `TranscriptionWorker` (hoje só guarda a string já formatada em `lines`),
em vez de tentar re-parsear o texto `[mm:ss]`.

**Efeito prático:** qualquer `.srt` salvo pela GUI hoje é inutilizável como legenda.

### 2. `transcrever.py` — fallback de GPU→CPU reprocessa arquivos já arquivados
Em `main()`:
```python
arquivos = [...]                     # lista calculada uma única vez
try:
    model = carregar_modelo(args.model, device)
    processar(model, arquivos, ffmpeg, args.interval, args.srt)
except Exception as e:
    if device == "cuda" and eh_erro_gpu(e):
        model = carregar_modelo(args.model, "cpu")
        processar(model, arquivos, ffmpeg, args.interval, args.srt)   # <- mesma lista!
```
Se a GPU falhar **no meio do lote** (não só ao carregar o modelo — ex.: erro de CUDA ao
processar o arquivo 3 de 10), os arquivos 1–2 já foram movidos para `processados/` por
`arquivar()`. O `except` então roda `processar()` de novo com a **mesma lista `arquivos`
original**, que ainda inclui os arquivos 1–2 — só que eles não existem mais no caminho
original (`entrada/...`), porque já foram movidos. Isso derruba a segunda tentativa (CPU)
com erro de arquivo não encontrado, e o fallback que deveria "salvar" o processamento
quebra também.

**Correção sugerida:** filtrar `arquivos` para os que ainda existem em `entrada/` antes de
tentar de novo, ou (melhor) isolar os erros por arquivo dentro de `processar()` (ver item 3)
em vez de deixar a exceção subir e abortar o lote inteiro.

## 🟡 Média prioridade

### 3. `transcrever.py` — um arquivo com erro derruba o lote inteiro
`processar()` não tem `try/except` por arquivo. Se a transcrição de um arquivo específico
falhar (arquivo corrompido, formato inesperado, etc.), o processamento para ali — os
arquivos seguintes da lista nem chegam a ser tentados nessa rodada (ficam em `entrada/`
para a próxima execução, o que evita perda de dado, mas não é o comportamento mais robusto
para um lote noturno/desatendido).

### 4. `app.py` — thread anterior pode continuar rodando ao iniciar uma nova transcrição
Em `toggle_transcription()`, apertar "Parar" chama `self.worker.stop()` (seta uma flag),
mas não espera (`wait()`) a thread realmente terminar antes de permitir que o usuário
aperte "Transcrever" de novo — o que cria um `TranscriptionWorker` novo e sobrescreve
`self.worker`. Não é um crash garantido (os sinais continuam ligados à instância antiga),
mas é uma condição de corrida desnecessária. `closeEvent()` já faz o certo (`stop()` +
`wait(3000)`) — o mesmo padrão poderia ser reaproveitado em `toggle_transcription()`.

### 5. `app.py` — `load_config()` sem tratamento de erro
Se `~/.eco/config.json` existir mas estiver com JSON inválido (edição manual, gravação
interrompida, etc.), `load_config()` deixa `json.loads` estourar e a aplicação fecha sem
mensagem nenhuma pro usuário, direto no `main()`.

## 🟢 Notas / baixa prioridade

### 6. Duplicação `app.py` ↔ `transcrever.py` (já documentada no `CLAUDE.md`)
Hoje `VOCAB` está idêntico nos dois arquivos — conferido nesta revisão. Só reforçando o que
o `CLAUDE.md` já avisa: qualquer ajuste de vocabulário/termos precisa ser replicado nos dois
lugares manualmente, não há fonte única.

### 7. Acoplamento implícito entre `MODEL_REPOS` (app.py) e resolução interna do faster-whisper
`SetupDialog` baixa o modelo via `huggingface_hub.snapshot_download(repo_id=MODEL_REPOS[size])`
(explicitamente `Systran/faster-whisper-<size>`), mas depois `TranscriptionWorker` chama
`WhisperModel(model_size, ...)` passando só o nome curto (`"large-v3"`) — quem resolve pra
qual repo isso aponta é a própria lib `faster-whisper` internamente. Hoje os dois batem
(o cache baixado é reaproveitado), mas se a lib mudar o mapeamento padrão no futuro, o
download feito no setup vira cache "órfão" e o app baixa o modelo de novo silenciosamente.

### 8. `transcrever.py` — falhas do `ffmpeg` na extração de frames são silenciosas
`extrair_frames()` roda o `ffmpeg` com `stdout=DEVNULL, stderr=DEVNULL` e sem `check=True`.
Se o `ffmpeg` falhar (codec não suportado, arquivo corrompido), a função só reporta
"0 frames -> dest" sem indicar que houve erro — fica parecendo que o vídeo simplesmente não
tinha frames pra extrair.

---
*Nenhuma mudança de código foi feita nesta revisão — só o relatório. Peça pra eu aplicar
qualquer um dos itens acima quando quiser.*
