import asyncio
import os
import tempfile

import speech_recognition as sr
import edge_tts
import pygame

from config import settings
from .speech_sanitizer import sanitize_for_speech

__all__ = ["InputClosed", "SpeechEngine", "sanitize_for_speech"]


class InputClosed(Exception):
    """Sinaliza que a fonte de entrada acabou (EOF no --text-mode ou Ctrl+C)."""



class SpeechEngine:
    """Encapsula reconhecimento de voz (STT) e síntese de voz (TTS).

    STT:
        SpeechRecognition + Google

    TTS:
        Microsoft Edge TTS com voz masculina neural em português do Brasil.
    """

    # Voz masculina brasileira do NERO
    VOICE = "pt-BR-AntonioNeural"

    # Ajustes da personalidade da voz
    RATE = "-5%"
    VOLUME = "+0%"
    PITCH = "-2Hz"

    def __init__(self, text_mode: bool = False, mic_index: int = None):
        self.text_mode = text_mode

        # device_index efetivo do microfone:
        #   1) --mic-index na linha de comando (se informado) tem prioridade;
        #   2) senão, o valor fixo e editável settings.MIC_DEVICE_INDEX;
        #   3) se ambos forem None, usa o microfone padrão do Windows.
        self.mic_index = (
            mic_index
            if mic_index is not None
            else settings.MIC_DEVICE_INDEX
        )

        self.recognizer = None
        self.microphone = None
        self._mic_available = False

        self._init_microphone()
        self._init_tts()

    # ------------------------------------------------------------------
    # MICROFONE / SPEECH-TO-TEXT
    # ------------------------------------------------------------------

    def _init_microphone(self) -> None:
        if self.text_mode:
            return

        try:
            self.recognizer = sr.Recognizer()

            device_names = sr.Microphone.list_microphone_names()

            if not device_names:
                print(
                    "[AVISO] Nenhum microfone foi detectado pelo Windows. "
                    "Conecte um microfone ou defina um dispositivo de entrada padrão em "
                    "Configurações > Som. Rode com --text-mode enquanto isso."
                )

                self._mic_available = False
                return

            # Ordem de tentativa dos device_index:
            #   1) o índice pedido (--mic-index / MIC_DEVICE_INDEX), se houver;
            #   2) senão, o dispositivo padrão do Windows (None) e, em seguida,
            #      cada entrada de captura detectada — o "Grupo de microfones
            #      (Realtek(R) Audio)" costuma aparecer em vários índices e
            #      só alguns aceitam abrir em modo compartilhado.
            candidates = self._candidate_mic_indices(device_names)

            ultimo_erro = None
            for device_index in candidates:
                try:
                    self._open_and_calibrate(device_index, device_names)
                    self.mic_index = device_index
                    self._mic_available = True
                    return

                except Exception as e:
                    ultimo_erro = e
                    rotulo = (
                        f"índice {device_index}"
                        if device_index is not None
                        else "dispositivo padrão do Windows"
                    )
                    print(
                        f"[AVISO] Microfone no {rotulo} não pôde ser aberto "
                        f"({e}). Tentando o próximo..."
                    )

            # Nenhum candidato funcionou.
            raise ultimo_erro if ultimo_erro is not None else RuntimeError(
                "nenhum dispositivo de entrada pôde ser aberto"
            )

        except Exception as e:
            root_cause = (
                e.__context__
                if e.__context__ is not None
                else e
            )

            print(
                f"[AVISO] Microfone indisponível ({root_cause}).\n"
                f"        Causas comuns em notebooks Lenovo (Realtek(R) Audio):\n"
                f"        - Outro app segurou o microfone em modo exclusivo "
                f"(Teams, Zoom, Meet, navegador, ou a própria janela do NERO "
                f"em outra execução). Feche-os e tente de novo.\n"
                f"        - O 'Grupo de microfones (Realtek(R) Audio)' não é o "
                f"dispositivo padrão: rode `python main.py --list-mics` e defina "
                f"MIC_DEVICE_INDEX em config/settings.py (ou use --mic-index).\n"
                f"        - Permissão de microfone desativada em Configurações > "
                f"Privacidade e segurança > Microfone.\n"
                f"        Enquanto isso, rode com --text-mode."
            )

            self._mic_available = False

    def _candidate_mic_indices(self, device_names) -> list:
        """Lista ordenada de device_index para tentar abrir."""

        if self.mic_index is not None:
            return [self.mic_index]

        candidates = [None]

        try:
            pa = sr.Microphone.get_pyaudio().PyAudio()
            try:
                for i in range(pa.get_device_count()):
                    info = pa.get_device_info_by_index(i)
                    if info.get("maxInputChannels", 0) > 0:
                        candidates.append(i)
            finally:
                pa.terminate()

        except Exception:
            # Sem PyAudio utilizável aqui: cai só no dispositivo padrão e
            # deixa o erro real aparecer na tentativa de abertura.
            for i in range(len(device_names)):
                candidates.append(i)

        return candidates

    def _open_and_calibrate(self, device_index, device_names) -> None:
        """Abre o microfone e calibra o ruído ambiente.

        Tudo que precisa de uma fonte de áudio ativa — ``adjust_for_ambient_noise``
        e a leitura de ``energy_threshold`` — fica OBRIGATORIAMENTE dentro do
        bloco ``with sr.Microphone(...) as source:``. Fora desse ``with`` o
        SpeechRecognition levanta "Audio source must be entered before adjusting,
        see documentation for AudioSource".
        """

        self.microphone = sr.Microphone(device_index=device_index)

        with self.microphone as source:
            # speech_recognition 3.17: Microphone.__enter__ ENGOLE a exceção do
            # PyAudio quando o dispositivo está ocupado/incompatível e deixa
            # source.stream == None, o que faz adjust_for_ambient_noise falhar
            # com a mensagem enganosa "Audio source must be entered before
            # adjusting". Detectamos isso aqui e trocamos pelo erro real.
            if getattr(source, "stream", None) is None:
                raise OSError(self._descrever_falha_de_abertura(source))

            self.recognizer.adjust_for_ambient_noise(
                source,
                duration=1
            )

            if (
                self.recognizer.energy_threshold
                > settings.MIC_ENERGY_THRESHOLD_CEILING
            ):
                print(
                    f"[AVISO] Limiar de energia calibrado muito alto "
                    f"({self.recognizer.energy_threshold:.0f}); "
                    f"usando um valor mais sensível "
                    f"({settings.MIC_ENERGY_THRESHOLD_FALLBACK}) "
                    f"para não perder fala."
                )

                self.recognizer.energy_threshold = (
                    settings.MIC_ENERGY_THRESHOLD_FALLBACK
                )

            self.recognizer.dynamic_energy_threshold = True

        used_index = (
            device_index
            if device_index is not None
            else "padrão do Windows"
        )

        used_name = (
            device_names[device_index]
            if device_index is not None and device_index < len(device_names)
            else ""
        )

        print(
            f"Microfone em uso: "
            f"{used_name or '(dispositivo padrão)'} "
            f"[index={used_index}] | "
            f"limiar de energia: "
            f"{self.recognizer.energy_threshold:.0f}"
        )

    @staticmethod
    def _descrever_falha_de_abertura(source) -> str:
        """Reabre a stream do PyAudio à mão só para capturar a mensagem de erro
        verdadeira que o speech_recognition escondeu."""

        try:
            pa = sr.Microphone.get_pyaudio().PyAudio()
            try:
                stream = pa.open(
                    input_device_index=source.device_index,
                    channels=1,
                    format=source.format,
                    rate=source.SAMPLE_RATE,
                    frames_per_buffer=source.CHUNK,
                    input=True,
                )
                stream.close()
                return (
                    "o driver aceitou abrir agora mas recusou na primeira "
                    "tentativa (dispositivo ocupado de forma intermitente)"
                )
            finally:
                pa.terminate()

        except Exception as e:
            return str(e)

    # ------------------------------------------------------------------
    # TEXT-TO-SPEECH
    # ------------------------------------------------------------------

    def _init_tts(self) -> None:
        try:
            pygame.mixer.init()

            print(
                f"Voz do NERO: {self.VOICE}"
            )

        except Exception as e:
            print(
                f"[AVISO] Não foi possível iniciar o sistema de áudio: {e}"
            )

    async def _generate_speech(self, text: str, output_file: str) -> None:
        communicate = edge_tts.Communicate(
            text,
            self.VOICE,
            rate=self.RATE,
            volume=self.VOLUME,
            pitch=self.PITCH,
        )

        await communicate.save(output_file)

    def speak(self, text: str) -> None:
        text = sanitize_for_speech(text)
        if not text:
            return
        print(f"[NERO] {text}")

        try:
            with tempfile.NamedTemporaryFile(
                suffix=".mp3",
                delete=False
            ) as temp:
                audio_file = temp.name

            asyncio.run(
                self._generate_speech(
                    text,
                    audio_file
                )
            )

            pygame.mixer.music.load(audio_file)
            pygame.mixer.music.play()

            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(20)

            pygame.mixer.music.unload()

            try:
                os.remove(audio_file)
            except OSError:
                pass

        except Exception as e:
            print(
                f"[AVISO] Falha ao sintetizar voz: {e}"
            )

    # ------------------------------------------------------------------
    # SPEECH-TO-TEXT
    # ------------------------------------------------------------------

    def listen(self):
        """Retorna o texto transcrito.

        Retorna:
            texto transcrito
            "" se ouviu algo mas não entendeu
            None se não houve captura
        """

        if self.text_mode:
            try:
                text = input("Você (texto): ").strip()

            except EOFError:
                raise InputClosed(
                    "entrada de texto encerrada (EOF)"
                )

            except KeyboardInterrupt:
                raise InputClosed(
                    "interrompido pelo usuário"
                )

            return text or None

        if not self._mic_available:
            return None

        # A abertura da fonte (with) e a captura (listen) ficam SEMPRE no mesmo
        # bloco with: o SpeechRecognition exige a fonte "entrada" para ouvir.
        try:
            with self.microphone as source:
                audio = self.recognizer.listen(
                    source,
                    timeout=settings.LISTEN_TIMEOUT_SECONDS,
                    phrase_time_limit=settings.LISTEN_PHRASE_TIME_LIMIT,
                )

        except sr.WaitTimeoutError:
            return None

        except OSError as e:
            print(
                f"[ERRO] Problema ao acessar o microfone: {e}"
            )
            return None

        except Exception as e:
            # Driver da Realtek falhou no meio da sessão, ou Teams/Zoom/navegador
            # assumiu o microfone em modo exclusivo depois que o NERO já estava
            # rodando. Não derruba o programa; apenas pula este ciclo de escuta.
            print(
                f"[AVISO] Falha ao capturar áudio do microfone ({e}). "
                f"Outro programa (Teams, Zoom, navegador) pode ter assumido o "
                f"dispositivo. Feche-o e o NERO volta a ouvir sozinho."
            )
            return None

        try:
            return self.recognizer.recognize_google(
                audio,
                language="pt-BR"
            )

        except sr.UnknownValueError:
            return ""

        except sr.RequestError as e:
            print(
                "[ERRO] Falha ao contatar o serviço de "
                f"reconhecimento de voz (verifique a internet): {e}"
            )
            return None