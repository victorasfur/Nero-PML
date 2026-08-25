# Alexa — Assistente Virtual em Python

Assistente virtual acadêmica, controlada por voz, com palavra de ativação
obrigatória ("Alexa"). Nenhum comando é executado antes da wake word ser
reconhecida.

## 1. Objetivo do projeto

Demonstrar, em um projeto acadêmico, uma assistente de voz completa:
máquina de estados para controle de ativação, reconhecimento e síntese de
voz, agenda persistida em arquivo texto, calculadora segura, reconhecimento
facial offline, integração com IA generativa e comandos utilitários extras
(clima, cotações, YouTube, screenshot, volume).

## 2. Tecnologias utilizadas e por quê

| Necessidade | Escolha | Motivo |
|---|---|---|
| Reconhecimento de voz (STT) | `SpeechRecognition` + Google Web Speech API | Instalação mais simples do mercado, ótima qualidade em pt-BR, gratuito e sem chave. Depende de internet — ver `--text-mode` abaixo como fallback de demonstração. |
| Síntese de voz (TTS) | `pyttsx3` | Offline (SAPI5 do Windows), sem depender de internet para os comandos locais. |
| Reconhecimento facial | OpenCV: Haar Cascade + LBPH (`opencv-contrib-python`) | Único pacote pip, sem compilar nada, 100% offline, bem documentado. Alternativas como `face_recognition`/dlib exigem CMake + Visual Studio Build Tools e quebram com frequência no Windows; `DeepFace` é pesado (TensorFlow) e lento — inadequados para uma demo acadêmica. |
| IA generativa | Google Gemini (`google-generativeai`) | Free tier generoso, SDK simples, resposta em português. |
| Clima | Open-Meteo (geocoding + forecast) | Gratuito, **sem necessidade de API key**, resposta em JSON estável. |
| Dólar / Bitcoin | AwesomeAPI (`economia.awesomeapi.com.br`) | Gratuita, sem chave, endpoint único por par de moeda. |
| Volume | `ctypes` + teclas de mídia do Windows | Stdlib puro — evita os problemas de instalação e compatibilidade do `pycaw`/COM entre versões do Windows. |
| Screenshot | `Pillow` (`ImageGrab`) | Já é dependência natural do projeto, sem lib extra. |
| Terminal colorido | `colorama` | Compatibilidade de cores ANSI no console do Windows. |
| Reconhecimento de intenção | `rapidfuzz` | MIT, mantido, wheel pré-compilada no Windows (sem compilador). Usado para tolerar variações naturais de fala ("qual a data de hoje" vs. "que dia é hoje") — ver seção 12. |

## 3. Pré-requisitos

- Windows 10/11
- Python 3.10+ instalado e no PATH
- Microfone e webcam (opcionais — o projeto funciona parcialmente sem eles, ver seção de solução de problemas)
- Conta Google para gerar uma chave gratuita do Gemini (opcional, só para o comando de IA)

## 4. Instalação do Python

Baixe em https://www.python.org/downloads/windows/ e, durante a instalação,
marque **"Add python.exe to PATH"**. Confirme no terminal:

```powershell
python --version
```

## 5. Criação do ambiente virtual

```powershell
cd "caminho\para\alexa-assistente"
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Se o PowerShell bloquear a execução do script de ativação, rode uma vez:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

## 6. Instalação das dependências

```powershell
pip install --upgrade pip
pip install -r requirements.txt
```

**Se `pip install pyaudio` falhar no Windows** (erro de compilador), use:

```powershell
pip install pipwin
pipwin install pyaudio
```

## 7. Configuração do `.env`

```powershell
copy .env.example .env
```

Edite `.env` e cole sua chave gratuita do Gemini (crie em
https://aistudio.google.com/apikey):

```env
GEMINI_API_KEY=sua_chave_aqui
GEMINI_MODEL=gemini-3.6-flash
```

**Nunca** coloque a chave diretamente no código — `.env` já está no
`.gitignore`.

O nome do modelo do Gemini muda com o tempo (a Google aposenta versões
antigas). Se a IA começar a responder "Desculpe, não consegui obter uma
resposta..." e o terminal mostrar um erro `404 ... model ... is no longer
available`, atualize `GEMINI_MODEL` no `.env` para o modelo sugerido na
própria mensagem de erro.

## 8. Configuração do microfone

Verifique em Configurações do Windows > Sistema > Som que o microfone
correto está selecionado como dispositivo de entrada padrão e com permissão
de acesso liberada para aplicativos de desktop (Configurações > Privacidade >
Microfone).

Se o microfone não estiver disponível, a aplicação avisa no terminal e
continua rodando — use `python main.py --text-mode` para digitar os comandos.

## 9. Configuração da webcam

Garanta que nenhum outro aplicativo está usando a câmera e que o acesso a
ela está liberado em Configurações > Privacidade > Câmera. Se a câmera não
abrir, o comando de reconhecimento facial responde "Câmera não disponível."
sem derrubar a aplicação.

## 10. Cadastro das faces

Antes de usar "Alexa reconhecer face" ou "Alexa quem sou eu", cadastre pelo
menos uma pessoa com o utilitário de captura (não é um comando de voz):

```powershell
python -m vision.capture_faces "Victor"
```

Isso abre a webcam, detecta o rosto e salva 20 fotos automaticamente em
`vision/dataset/Victor/`. Pressione `q` a qualquer momento para parar antes.
Repita para cada pessoa que quiser cadastrar. A pasta `vision/dataset/desconhecido/`
é só ilustrativa — o reconhecedor a ignora como rótulo válido.

## 11. Execução

```powershell
python main.py
```

Modo texto (fallback sem microfone/internet, mesma lógica de comandos):

```powershell
python main.py --text-mode
```

## 12. Reconhecimento de intenção e lista de comandos

Todos exigem a wake word "Alexa" antes (na mesma fala ou em falas separadas).
A partir daí, a assistente **não exige uma frase exata** — ela reconhece a
intenção por trás de várias formas naturais de pedir a mesma coisa (ver
`assistant/intent_router.py`):

```
STT → normalização → matchers estruturais (regex: calculadora, clima,
      dólar, bitcoin, youtube, print, volume) → guard de discurso ("fale
      sobre X" ≠ comando X) → fuzzy matching (rapidfuzz) contra frases de
      referência → política de confiança:

        confiança ≥ 0.80  → executa direto
        0.60 ≤ conf < 0.80 → "Você quis dizer <X>? Sim ou não?"
        confiança < 0.60  → encaminha para a IA (Gemini)
```

| Intenção | Exemplos que funcionam | Ação |
|---|---|---|
| `ADD_AGENDA` | "cadastrar evento na agenda", "quero colocar um compromisso na minha agenda", "marque um compromisso" | Pergunta o evento e salva em `data/agenda.txt` (a resposta seguinte NÃO precisa da wake word) |
| `READ_AGENDA` | "ler agenda", "quais são meus eventos", "o que tenho na agenda" | Fala todos os eventos cadastrados |
| `CLEAR_AGENDA` | "limpar agenda", "apague minha agenda", "remova tudo da agenda" | Pede confirmação (sim/não) e esvazia `agenda.txt` sem excluí-lo |
| `GET_TIME` | "que horas são", "qual é a hora", "você sabe me dizer a hora atual" | Fala a hora atual do sistema |
| `GET_DATE` | "que dia é hoje", "qual a data de hoje", "hoje é que dia" | Fala a data atual em português |
| `CALCULATE` | "calcular 10 mais 20", "quanto é 10 + 20", "calcule 8 vezes 7", "100 dividido por 5" | Soma/subtrai/multiplica/divide (dígitos, símbolos ou por extenso) |
| `FACE_RECOGNITION` | "reconhecer face", "quem sou eu", "identificar pessoa" | Abre a webcam e identifica a pessoa |
| `WEATHER` | "previsão do tempo para São Paulo", "como está o tempo" | Consulta o clima (Open-Meteo) |
| `DOLLAR` | "qual o valor do dólar hoje" | Consulta a cotação (AwesomeAPI) |
| `BITCOIN` | "quanto vale um bitcoin hoje" | Consulta a cotação (AwesomeAPI) |
| `OPEN_YOUTUBE` | "abrir YouTube" | Abre o YouTube no navegador padrão |
| `YOUTUBE_SEARCH` | "pesquisar no YouTube vídeos sobre Python" | Abre a busca no YouTube |
| `SCREENSHOT` | "tirar um print da tela" | Salva um screenshot com data/hora no nome |
| `VOLUME_UP` / `VOLUME_DOWN` | "aumentar/diminuir o volume" | Ajusta o volume do sistema |
| — | "cancelar" (em qualquer pergunta pendente) | Cancela o cadastro de evento/confirmação em andamento |
| `ASK_AI` | qualquer outra pergunta ("explique o que é Python") | Encaminhada para a IA generativa (Gemini), sem a palavra "Alexa" |

**Por que "fale sobre reconhecimento facial" não abre a câmera**: frases que
falam *sobre* um assunto ("fale sobre", "explique", "o que é", "como
funciona") são tratadas como pergunta, não como comando, e vão direto para a
IA — mesmo que o assunto mencionado seja parecido com uma intenção real.

## 13. Estrutura do projeto

```
alexa-assistente/
├── main.py
├── requirements.txt
├── .env / .env.example
├── .gitignore
├── README.md
├── data/agenda.txt
├── config/settings.py
├── assistant/
│   ├── state_machine.py     # Enum de estados + transições
│   ├── assistant.py         # loop principal / máquina de estados
│   ├── speech.py            # STT + TTS
│   ├── text_normalizer.py   # normalização + wake word tolerante
│   ├── intents.py           # Enum Intent (GET_DATE, CALCULATE, ...)
│   ├── intent_router.py     # classify(): texto -> IntentMatch (intenção+confiança+params)
│   ├── commands.py          # command_registry: Intent -> handler + política de confiança
│   ├── calculator.py        # parser seguro (sem eval)
│   ├── agenda.py            # agenda.txt
│   ├── datetime_utils.py
│   ├── ai.py                # ask_ai() via Gemini
│   ├── weather.py           # Open-Meteo
│   ├── finance.py           # AwesomeAPI
│   ├── youtube.py
│   ├── screenshot.py
│   └── volume.py
├── vision/
│   ├── face_recognition.py  # Haar Cascade + LBPH
│   ├── capture_faces.py     # utilitário de cadastro
│   └── dataset/<nome>/*.jpg
└── tests/
    ├── test_calculator.py
    ├── test_agenda.py
    ├── test_text_normalizer.py
    └── test_intent_router.py
```

## 14. Solução de problemas

- **PyAudio não instala**: use `pipwin install pyaudio` (seção 6).
- **Assistente fala em inglês/voz robótica**: instale um pacote de voz
  pt-BR em Configurações > Hora e Idioma > Voz; o terminal avisa quando
  nenhuma voz pt-BR foi encontrada.
- **"Câmera não disponível"**: feche outros apps usando a câmera e confira
  as permissões de privacidade do Windows.
- **Reconhecimento de voz não entende nada**: confira o microfone padrão e
  a conexão com a internet (o STT usa a Google Web Speech API).
- **API do Gemini falha**: confirme a chave em `.env`; a assistente responde
  educadamente mesmo sem IA configurada. Se o erro no terminal for `404 ...
  model ... is no longer available`, o modelo configurado em `GEMINI_MODEL`
  foi aposentado — troque pelo nome sugerido na própria mensagem de erro.
- **Sem internet durante a apresentação**: rode com `--text-mode` para
  digitar os comandos e continuar demonstrando a máquina de estados e os
  comandos locais (agenda, hora, data, calculadora, reconhecimento facial).

## 15. Como adicionar novos comandos

Handlers não sabem nada sobre COMO a intenção foi reconhecida — só recebem
`(params, normalized_text, raw_text)`. Isso separa completamente reconhecimento
(`intent_router.py`) de execução (`commands.py`).

1. Adicione o novo valor em `assistant/intents.py` (`Intent`).
2. Escreva `handle_minha_intencao(params, normalized, raw) -> CommandResult`
   em `assistant/commands.py` e registre em `COMMAND_REGISTRY`.
3. Ensine o `intent_router.py` a reconhecer a intenção:
   - Se tem uma palavra-chave praticamente inequívoca e/ou precisa extrair
     parâmetros (como clima/cidade, YouTube/busca): adicione um regex em
     `_structural_match()`.
   - Se varia muito de forma de falar (como data/hora/agenda): adicione uma
     lista de frases de referência em `REFERENCE_PHRASES` — não precisa
     cobrir toda variação possível, o fuzzy matching (rapidfuzz) tolera
     pequenas diferenças de transcrição e reordenação de palavras.
4. Não é necessário tocar em `assistant.py` — `commands.dispatch()` já é
   chamado tanto para "Alexa, comando" na mesma fala quanto para comandos
   ditos após a ativação, e já aplica a política de confiança (executar /
   confirmar / encaminhar para IA).

## Testes

```powershell
pytest
```

Cobre a calculadora (as 4 operações, divisão por zero, números por extenso,
símbolos "+ - * /"), a agenda (criação, escrita, leitura, múltiplos eventos,
limpeza sem excluir o arquivo), o normalizador de texto/wake word (incluindo
o falso positivo em "fui na loja da alexa"), e o reconhecimento de intenção
(`test_intent_router.py`): dezenas de variações naturais por intenção, o
diálogo de exemplo completo executando sem pedir confirmação, extração de
parâmetros (cidade, expressão de cálculo, busca do YouTube), e os três
falsos positivos citados no enunciado ("conte uma história sobre um dia...",
"explique como funciona uma agenda", "fale sobre reconhecimento facial").
