# Nero — Assistente Virtual Conversacional em Python

Assistente virtual acadêmica, controlada por voz, com palavra de ativação
obrigatória ("Nero"). Nenhum comando é executado antes da wake word ser
reconhecida.

Além dos comandos locais, a Nero **conversa sobre qualquer assunto** usando
IA generativa (Google Gemini), **mantém contexto** da conversa (resolve "e
onde ELE nasceu?") e **diferencia pergunta de ação** — perguntas vão para a
IA, comandos executam ações reais no computador.

## 1. Objetivo do projeto

Demonstrar uma assistente de voz completa: máquina de estados para controle
de ativação, STT/TTS, agenda persistida em arquivo texto, calculadora
segura, reconhecimento facial offline, **cérebro conversacional com memória
de contexto**, **roteamento híbrido de intenção (local + IA)** e comandos
utilitários (clima, cotações, YouTube, tocar música, abrir apps/sites,
screenshot, volume).

## 2. Como a Nero decide o que fazer

```
MICROFONE
   -> SPEECH TO TEXT (SpeechRecognition + Google)
   -> DETECTA "NERO" (wake word tolerante a variações)
   -> NORMALIZA TEXTO (minúsculas, sem acento/pontuação)
   -> INTENT ROUTER (assistant/intent_router.py):
        1. matchers estruturais (regex/parser): calculadora, clima, dólar,
           bitcoin, print, volume, tocar música, buscar no YouTube, abrir
           YouTube/navegador/Google/VS Code
        2. guard de discurso: "explique X" / "o que é X" -> CHAT (pergunta)
        3. fuzzy matching (rapidfuzz) vs data/intents.json: data, hora,
           agenda, reconhecimento facial, e as ações acima
        4. se a confiança local ficou baixa E a IA está disponível:
           ai.classify_intent() -> {intent, confidence, parameters},
           VALIDADO contra o enum + allowlist + schema de parâmetros
        5. senão -> CHAT
   -> POLÍTICA DE CONFIANÇA:
        confiança >= 0.80  -> executa a ação
        0.60 <= conf < 0.80 -> "Você quis dizer <X>? Sim ou não?"
        confiança < 0.60   -> conversa com a IA (CHAT)
   -> AÇÃO (handler local)  |  CHAT (Gemini + memória de contexto)
   -> TEXT TO SPEECH (Edge TTS, voz neural pt-BR) -> volta a escutar
```

**A IA nunca executa nada diretamente.** Ela só devolve uma intenção
estruturada; quem valida e executa é o código local (ver seção 12).

## 3. Tecnologias utilizadas e por quê

| Necessidade | Escolha | Motivo |
|---|---|---|
| Reconhecimento de voz (STT) | `SpeechRecognition` + Google Web Speech API | Instalação simples, ótima qualidade em pt-BR, gratuito e sem chave. Depende de internet — ver `--text-mode` como fallback. |
| Síntese de voz (TTS) | **Microsoft Edge TTS** (`edge-tts`) + `pygame` | Voz neural masculina pt-BR (`pt-BR-AntonioNeural`), muito natural, gratuita e sem chave. Depende de internet; se falhar, a assistente só imprime a resposta e continua. |
| Reconhecimento facial | OpenCV: Haar Cascade + LBPH (`opencv-contrib-python`) | Um único pacote pip, sem compilar nada, 100% offline. |
| IA generativa | Google Gemini (`google-generativeai`) | Free tier generoso, SDK simples, resposta em português. Usada para **conversa** e para **classificar** pedidos difíceis. |
| Contexto de conversa | Estrutura própria (`conversation_memory.py`) | Janela deslizante das últimas `CONVERSATION_MAX_MESSAGES` mensagens — não cresce infinitamente. |
| Clima | Open-Meteo (geocoding + forecast) | Gratuito, **sem API key**. |
| Dólar / Bitcoin | AwesomeAPI (`economia.awesomeapi.com.br`) | Gratuita, sem chave. |
| Tocar música / buscar vídeo | `webbrowser` + URL de busca do YouTube | O navegador não pode ser "mandado dar play" de forma confiável; abrimos a busca e a assistente **nunca afirma** que começou a tocar. |
| Abrir apps/sites | `webbrowser` + `os.startfile` sobre um **allowlist fixo** | A IA nunca fornece caminho/URL/comando — só a intenção. |
| Volume | `ctypes` + teclas de mídia do Windows | Stdlib puro, sem `pycaw`/COM. |
| Screenshot | `Pillow` (`ImageGrab`) | Sem lib extra. |
| Reconhecimento de intenção | `rapidfuzz` | MIT, wheel pré-compilada no Windows. Tolera variações naturais de fala. |

## 4. Pré-requisitos

- Windows 10/11
- Python 3.10+ no PATH
- Microfone e webcam (opcionais — o projeto funciona parcialmente sem eles)
- Chave gratuita do Gemini (opcional — sem ela, os comandos locais continuam
  funcionando; só a conversa livre e a classificação por IA ficam desligadas)

## 5. Ambiente virtual e dependências

```powershell
cd "caminho\para\nero-assistente"
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
```

Se o PowerShell bloquear o script de ativação, rode uma vez:
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

**Se `pip install pyaudio` falhar** (erro de compilador):
`pip install pipwin` e depois `pipwin install pyaudio`.

## 6. Configuração do `.env`

```powershell
copy .env.example .env
```

Edite `.env` e cole sua chave (crie em https://aistudio.google.com/apikey):

```env
GEMINI_API_KEY=sua_chave_aqui
GEMINI_MODEL=gemini-2.0-flash
```

**Nunca** coloque a chave no código — `.env` já está no `.gitignore`.

O nome do modelo muda com o tempo. Se o terminal mostrar `404 ... model ...
is no longer available`, troque `GEMINI_MODEL` pelo nome sugerido no erro.

## 7. Microfone e webcam

Confira em Configurações do Windows > Som que o microfone correto é o
dispositivo de entrada padrão, e em Privacidade > Microfone/Câmera que o
acesso está liberado para apps de desktop. Se o microfone não estiver
disponível, a aplicação avisa e continua — use `python main.py --text-mode`.

## 8. Cadastro das faces (reconhecimento facial)

```powershell
python -m vision.capture_faces "Victor"
```

Abre a webcam e salva 20 fotos em `vision/dataset/Victor/`. Repita para cada
pessoa. `q` interrompe antes.

## 9. Execução

```powershell
python main.py                 # voz
python main.py --text-mode     # digitando os comandos (mesma lógica)
python main.py --list-mics     # lista os microfones e sai
```

## 10. Conversa livre e memória de contexto

Qualquer fala pós-"Nero" que não seja um comando conhecido vira **conversa**
com o Gemini. O histórico das últimas mensagens é enviado junto, então:

```
Nero, quem foi Albert Einstein?      -> "Foi um físico alemão..."
Nero, e onde ele nasceu?             -> entende que "ele" = Einstein
Nero, me explique Python.            -> explica
Nero, e Java?                        -> entende que é comparação com Python
```

O sistema de voz recebe a resposta já **limpa para fala** (sem markdown,
sem asteriscos, sem URLs cruas, sem JSON — ver `speech.sanitize_for_speech`).
A instrução de sistema pede respostas curtas (a resposta será falada).

## 11. Lista de comandos

Todos exigem "Nero" antes (na mesma fala ou em falas separadas). **Não é
preciso frase exata** — o roteador reconhece a intenção por trás de várias
formas de pedir a mesma coisa. Exemplos vivem em `data/intents.json`.

| Intenção | Exemplos que funcionam | Ação |
|---|---|---|
| `GET_DATE` | "que dia é hoje", "qual a data de hoje", "hoje é que dia" | Fala a data atual |
| `GET_TIME` | "que horas são", "me fala a hora", "qual o horário atual" | Fala a hora atual |
| `ADD_AGENDA` | "cadastrar evento", "quero colocar um compromisso na agenda" | Pergunta o evento e salva em `data/agenda.txt` (a resposta seguinte NÃO precisa da wake word) |
| `READ_AGENDA` | "leia minha agenda", "quais são meus eventos" | Fala os eventos cadastrados |
| `CLEAR_AGENDA` | "limpar agenda", "apague minha agenda" | Pede confirmação (sim/não) e esvazia `agenda.txt` |
| `CALCULATE` | "quanto é 25 vezes 8", "10 mais 20", "cem dividido por 4" | 4 operações (dígitos, símbolos ou por extenso) |
| `FACE_RECOGNITION` | "quem sou eu", "reconheça meu rosto" | Abre a webcam e identifica a pessoa |
| `WEATHER` | "previsão do tempo para São Paulo", "vai chover" | Consulta o clima (Open-Meteo) |
| `DOLLAR` / `BITCOIN` | "quanto está o dólar", "qual o preço do bitcoin" | Consulta a cotação (AwesomeAPI) |
| `OPEN_YOUTUBE` | "abra o YouTube", "entre no YouTube", "quero assistir algo no YouTube" | Abre o YouTube no navegador |
| `YOUTUBE_SEARCH` | "procure vídeos sobre Python no YouTube", "quero vídeos de programação Python" | Abre a busca do YouTube com a query extraída |
| `PLAY_MUSIC` | "toque Evidências", "coloque uma música do Bruno Mars", "quero ouvir música sertaneja" | Abre a busca do YouTube pela música. **Não afirma** que começou a tocar |
| `OPEN_BROWSER` | "abra o navegador" | Abre o navegador padrão |
| `OPEN_GOOGLE` | "abra o Google" | Abre google.com |
| `OPEN_VSCODE` | "abra o VS Code", "abre o editor de código" | Abre o VS Code (caminho fixo do allowlist) |
| `SCREENSHOT` | "tire um print da tela" | Salva um screenshot com data/hora no nome |
| `VOLUME_UP` / `VOLUME_DOWN` | "aumenta o som", "diminui o volume" | Ajusta o volume do sistema |
| — | "cancelar" (em qualquer pergunta pendente) | Cancela a operação em andamento |
| `CHAT` | qualquer outra pergunta ("o que é uma API", "conte uma piada") | Conversa com o Gemini, com memória de contexto |

**Por que "explique como funciona o reconhecimento facial" não abre a
câmera**: frases que falam *sobre* um assunto ("explique", "o que é", "como
funciona", "fale sobre") são tratadas como pergunta e vão para `CHAT`.

## 12. Segurança: a IA não executa ações

```
Usuário -> IA/Intent Router -> Intent estruturada -> VALIDAÇÃO -> Handler -> Computador
```

- A IA (`ai.classify_intent`) só devolve JSON `{intent, confidence,
  parameters}`. Esse JSON **nunca** é falado.
- `intent_router._ai_match` valida: o nome tem que estar no enum `Intent`
  **e** em `AI_ALLOWED_INTENTS` (agenda e reconhecimento facial ficam de
  fora de propósito). Parâmetros passam por `_sanitize_ai_params`, que só
  copia chaves conhecidas por intent — um dict arbitrário é descartado.
- Ações vindas da IA **não executam "no susto"**: confiança < 0.85 cai na
  faixa de confirmação ("Você quis dizer X?").
- Abrir apps/sites usa um **allowlist fixo** (`settings.WEB_TARGETS`,
  `settings.VSCODE_CANDIDATES`). A IA nunca fornece caminho/URL/comando.
- Não há `subprocess`, `os.system`, `eval` ou `exec` em lugar nenhum
  (`tests/test_ai_safety.py` verifica isso a cada execução dos testes).

## 13. Estrutura do projeto

```
nero-assistente/
├── main.py
├── requirements.txt
├── .env / .env.example
├── data/
│   ├── agenda.txt
│   └── intents.json          # exemplos de fala por intenção (fuzzy + few-shot da IA)
├── config/settings.py        # chaves, allowlists, limites, prompt de sistema
├── assistant/
│   ├── state_machine.py      # Enum de estados + transições
│   ├── assistant.py          # loop principal / máquina de estados / memória
│   ├── conversation_memory.py# janela deslizante de contexto da conversa
│   ├── speech.py             # STT + TTS + sanitize_for_speech()
│   ├── text_normalizer.py    # normalização + wake word tolerante
│   ├── intents.py            # Enum Intent + AI_ALLOWED_INTENTS
│   ├── intent_router.py      # classify(): texto -> IntentMatch (local + IA)
│   ├── parameter_extractors.py # extrai query de música / vídeo
│   ├── commands.py           # COMMAND_REGISTRY: Intent -> handler + política de confiança
│   ├── ai.py                 # ask_chat() (conversa) + classify_intent() (JSON)
│   ├── system_actions.py     # abrir navegador/Google/VS Code (allowlist)
│   ├── youtube.py            # abrir / buscar no YouTube
│   ├── calculator.py         # parser seguro (sem eval)
│   ├── agenda.py · datetime_utils.py · weather.py · finance.py
│   ├── screenshot.py · volume.py
├── vision/
│   ├── face_recognition.py · capture_faces.py · dataset/<nome>/*.jpg
└── tests/
    ├── test_calculator.py · test_agenda.py · test_text_normalizer.py
    ├── test_intent_router.py · test_parameter_extractors.py
    ├── test_conversation_memory.py · test_ai_safety.py
```

## 14. Como adicionar um novo comando

Reconhecimento (`intent_router.py`) e execução (`commands.py`) são
totalmente separados — handlers só recebem `(params, normalized, raw, memory)`.

1. Novo valor em `assistant/intents.py` (`Intent`). Se a IA puder
   classificá-lo, adicione também em `AI_ALLOWED_INTENTS`.
2. `handle_minha_intencao(...)` em `assistant/commands.py` + registro em
   `COMMAND_REGISTRY`.
3. Ensine o roteador:
   - palavra-chave inequívoca / precisa de parâmetro -> regex em
     `_structural_match()` (e um extrator em `parameter_extractors.py`);
   - varia muito de forma -> adicione exemplos em `data/intents.json` (entra
     no fuzzy matching e no few-shot da classificação por IA).
4. Não é preciso tocar em `assistant.py`.

## 15. Solução de problemas

- **PyAudio não instala**: `pipwin install pyaudio`.
- **TTS falha / sem voz**: o Edge TTS precisa de internet; sem ela a
  assistente só imprime a resposta e continua funcionando.
- **"Câmera não disponível"**: feche outros apps usando a câmera e confira
  as permissões de privacidade.
- **STT não entende nada**: confira o microfone padrão e a internet.
- **IA não responde**: confirme `GEMINI_API_KEY` no `.env`. Se o erro for
  `404 ... model ... is no longer available`, troque `GEMINI_MODEL`.
- **Sem internet na apresentação**: `--text-mode` continua demonstrando a
  máquina de estados e todos os comandos locais (agenda, hora, data,
  calculadora, volume, reconhecimento facial).

## 16. Testes

```powershell
pytest
```

Cobre: calculadora (4 operações, divisão por zero, extenso, símbolos),
agenda, normalizador/wake word, roteamento de intenção (dezenas de
variações por intenção, extração de parâmetros, os falsos positivos
"explique/fale sobre X"), extração de query de música/vídeo, memória de
conversa (janela que não cresce, mapeamento de papéis) e **segurança da IA**
(não inventa intenção de shell, não escapa do allowlist, não executa ação
sem confirmação, sem `subprocess`/`eval` no código).
