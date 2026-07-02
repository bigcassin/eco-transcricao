# Notas pessoais — Claude Code (não é sobre o projeto Eco)

> Este arquivo não documenta o `eco-transcricao` em si — é uma nota pessoal do dono do
> repo sobre como usar o Claude Code entre PC e celular. Está aqui porque o git deste
> repositório é o único jeito confiável de fazer essa informação "atravessar" de uma
> sessão pra outra (sessões do Claude Code são isoladas entre si — ver `CLAUDE.md` /
> `REVISAO.md` pra contexto de por quê).

## Como conectar o PC ao celular via Remote Control

Fonte oficial: https://code.claude.com/docs/en/remote-control.md

### Pré-requisitos (checar uma vez)
- Claude Code **v2.1.51 ou mais recente** no PC — conferir com `claude --version`.
- Plano **Pro, Max, Team ou Enterprise** (chave de API pura não funciona com Remote Control).
- Login feito com `claude auth login` usando a conta **claude.ai** (não o Console da API).
- Ter rodado `claude` pelo menos uma vez na pasta do projeto no PC, pra aceitar o "workspace trust".
- Se a conta for Team/Enterprise: um admin precisa ativar o toggle **"Remote Control"** em
  `claude.ai/admin-settings/claude-code`.
- **Não funciona** com Bedrock, Vertex AI, Foundry, nem com `ANTHROPIC_BASE_URL` customizada.

### Passo a passo — no PC
1. Abra o terminal na pasta do projeto que você quer trabalhar.
2. Rode:
   ```bash
   claude remote-control
   ```
   (Esse é o modo "server": fica rodando esperando conexão, sem precisar digitar nada
   localmente. Alternativas: `claude --remote-control "Nome do Projeto"` pra já abrir uma
   sessão interativa usável dos dois lados, ou `/remote-control` — atalho `/rc` — de dentro
   de uma sessão já em andamento, que leva o histórico da conversa atual junto.)
3. Uma **URL da sessão** aparece no terminal.
4. Aperte a **barra de espaço** pra trocar a URL por um **QR code**.

### Passo a passo — no celular
5. Abra a câmera / o app oficial do Claude e escaneie o QR code — ou abra o link direto
   no navegador em `claude.ai/code`.
6. Não precisa instalar nada além do app oficial do Claude (iOS/Android) ou usar o
   navegador mesmo. Se não tiver o app ainda, dá pra rodar `/mobile` no PC pra gerar um
   QR code de instalação do app.
7. A sessão do celular passa a ser a mesma do PC — dá pra digitar dos dois lados, em
   tempo real, e o contexto é compartilhado (não é preciso git pra sincronizar nada
   nesse modo).

### Importante: não fica pareado permanentemente
- **Cada vez que quiser usar**, o PC precisa estar com `claude remote-control` rodando.
  Fechou o terminal → a sessão remota encerra.
- Não existe "lembrar o celular" de uma vez pra sempre — é sempre: liga o PC, roda o
  comando, conecta do celular daquela vez.
- Se a rede cair por ~10 minutos, a sessão expira por timeout. Se o notebook for pra
  suspensão/sleep, reconecta sozinho quando ele acorda.
- Não precisa abrir porta nenhuma no roteador — a conexão é toda via HTTPS de saída
  (outbound) para a API da Anthropic.

### Segurança
- O link/QR expira junto com a sessão (quando o terminal fecha).
- Qualquer pessoa com o link/QR **enquanto ele for válido** consegue entrar na sessão —
  é um token de curta duração, não uma senha. Não compartilhar o QR/link com ninguém.
- Tráfego todo passa por TLS via `api.anthropic.com`.
- Existe um recurso "Trusted Devices" (beta, só Team/Enterprise) que exige cadastro do
  aparelho + reautenticação a cada 18h — não se aplica a conta pessoal Pro/Max.

### Deixar sempre ativado por padrão
- Não há uma opção pra isso em `settings.json`.
- Dá pra ativar "Enable Remote Control for all sessions" no comando `/config` dentro do
  Claude Code, pra toda sessão interativa já nascer com Remote Control disponível — mas
  ainda assim, o PC precisa estar ligado e a sessão ativa na hora que você for acessar
  do celular.

### Resumindo o fluxo do dia a dia
No PC: `claude remote-control` (ou `/rc` numa sessão já aberta) → aperta espaço → escaneia
o QR no celular. Sempre que quiser continuar de outro dispositivo, repete esse processo —
não é um pareamento permanente tipo Bluetooth.
