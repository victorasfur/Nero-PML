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
GEMINI_MODEL=gemini-2.0-flash
```

**Nunca** coloque a chave diretamente no código — `.env` já está no
`.gitignore`.

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

## 12. Lista de comandos

Todos exigem a wake word "Alexa" antes (na mesma fala ou em falas separadas).

| Comando de exemplo | Ação |
|---|---|
| Alexa cadastrar evento na agenda | Pergunta o evento e salva em `data/agenda.txt` |
| Alexa ler agenda | Fala todos os eventos cadastrados |
| Alexa limpar agenda | Pede confirmação (sim/não) e esvazia `agenda.txt` sem excluí-lo |
| Alexa que horas são | Fala a hora atual do sistema |
| Alexa que dia é hoje | Fala a data atual em português |
| Alexa calcular 10 mais 20 | Soma (aceita mais/menos/vezes/dividido por, dígitos ou por extenso) |
| Alexa reconhecer face / Alexa quem sou eu | Abre a webcam e identifica a pessoa |
| Alexa qual a previsão do tempo para São Paulo | Consulta o clima (Open-Meteo) |
| Alexa qual o valor do dólar hoje | Consulta a cotação (AwesomeAPI) |
| Alexa quanto vale um bitcoin hoje | Consulta a cotação (AwesomeAPI) |
| Alexa abrir YouTube | Abre o YouTube no navegador padrão |
| Alexa pesquisar no YouTube vídeos sobre Python | Abre a busca no YouTube |
| Alexa tirar um print da tela | Salva um screenshot com data/hora no nome |
| Alexa aumentar/diminuir o volume | Ajusta o volume do sistema |
| Alexa cancelar | Cancela o cadastro de evento/confirmação em andamento |
| Qualquer outra pergunta | Encaminhada para a IA generativa (Gemini) |

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
│   ├── commands.py          # registro/roteador de comandos
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
    └── test_text_normalizer.py
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
  educadamente mesmo sem IA configurada.
- **Sem internet durante a apresentação**: rode com `--text-mode` para
  digitar os comandos e continuar demonstrando a máquina de estados e os
  comandos locais (agenda, hora, data, calculadora, reconhecimento facial).

## 15. Como adicionar novos comandos

1. Escreva a função de tratamento em `assistant/commands.py` com a
   assinatura `handler(match, normalized_text, raw_text) -> CommandResult`.
2. Adicione uma entrada em `COMMANDS` com um `re.compile(...)` que identifique
   a frase (usando `normalize_text` como referência: minúsculas, sem acento).
3. Não é necessário tocar em `assistant.py` — o roteador (`commands.dispatch`)
   já é chamado tanto para "Alexa, comando" na mesma fala quanto para
   comandos ditos após a ativação.

## Testes

```powershell
pytest
```

Cobre a calculadora (as 4 operações, divisão por zero, números por extenso),
a agenda (criação, escrita, leitura, múltiplos eventos, limpeza sem excluir
o arquivo) e o normalizador de texto/wake word (incluindo o caso de falso
positivo em "fui na loja da alexa").
