import asyncio
import os
import tempfile

import speech_recognition as sr
import edge_tts
import pygame

from config import settings


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
        self.mic_index = mic_index

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

            self.microphone = sr.Microphone(
                device_index=self.mic_index
            )

            with self.microphone as source:
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
                self.mic_index
                if self.mic_index is not None
                else "padrão do Windows"
            )

            used_name = (
                device_names[self.mic_index]
                if self.mic_index is not None
                else ""
            )

            print(
                f"Microfone em uso: "
                f"{used_name or '(dispositivo padrão)'} "
                f"[index={used_index}] | "
                f"limiar de energia: "
                f"{self.recognizer.energy_threshold:.0f}"
            )

            self._mic_available = True

        except Exception as e:
            root_cause = (
                e.__context__
                if e.__context__ is not None
                else e
            )

            print(
                f"[AVISO] Microfone indisponível ({root_cause}). "
                f"Provavelmente outro aplicativo está usando o microfone "
                f"em modo exclusivo (Teams, Zoom, navegador, etc.) ou "
                f"o dispositivo de entrada padrão do Windows mudou. "
                f"Feche outros apps que usam o microfone e tente novamente, "
                f"ou rode com --text-mode."
            )

            self._mic_available = False

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
        print(f"Nero: {text}")

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