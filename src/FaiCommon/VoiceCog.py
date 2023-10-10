"""
Filename    :   VoiceCog.py
Copyright   :   FoundAItion Inc.
Description :   Voice recognition
Written by  :   Alex Fedosov
Created     :   06/29/2023
Updated     :   06/29/2023
"""

from vosk import Model, KaldiRecognizer

import json
import logging
import os
import pyaudio
import pyttsx3
import queue
import sys
import time
import threading

log = logging.getLogger(__name__)


class VoicePlayerAsync(threading.Thread):
    WAIT_TIMEOUT = 1  # sec

    def __init__(self, *args, **kwargs):
        threading.Thread.__init__(self)
        self.play_queue = queue.Queue()
        self.should_exit = False
        self.args = args
        self.kwargs = kwargs
        self.start()

    def run(self):
        player = VoicePlayer(*self.args, **self.kwargs)

        while not self.should_exit:
            try:
                text = self.play_queue.get(block=True)
                player.play(text)
                self.play_queue.task_done()
            except queue.Empty:
                continue
            except Exception as err:
                log.error(f"Voice player error: {err}")
                continue

    def play(self, text):
        if text:
            self.play_queue.put(text)

    def stop(self):
        self.should_exit = True
        self.play_queue.put("")
        self.join(VoicePlayerAsync.WAIT_TIMEOUT)


class VoicePlayer():
    instance = None

    def __new__(cls, *args, **kwargs):
        """Initialize synchronous player. Singleton class.
        """
        if not isinstance(cls.instance, cls):
            cls.instance = super(VoicePlayer, cls).__new__(cls)
        return cls.instance

    def __init__(self, gender="female", name="") -> None:       
        self.engine = pyttsx3.init()
        voices = self.engine.getProperty("voices")

        for voice in voices:
            if voice.gender == gender or (name and voice.name.find(name) >= 0):
                self.engine.setProperty("voice", voice.id)
                break

    def play(self, text: str) -> None:
        """Voice player
        """
        if text:
            self.engine.say(text)
            self.engine.runAndWait()


class VoiceCog():
    SAMPLING_RATE = 16000
    FRAMES_LIMIT = 4096
    WORD_DELIMITER = " "
    DEFAULT_MODEL = "vosk-model-small-en-us-0.15"

    def __init__(self, model_name=DEFAULT_MODEL) -> None:
        model_path = os.path.join("VoiceCog\models", model_name)
        if getattr(sys, 'frozen', False):
            full_path_to_model = os.path.join(sys._MEIPASS, model_path)
        else:
            full_path_to_model = os.path.join(os.path.dirname(__file__), model_path)

        model = Model(full_path_to_model)
        self.recognizer = KaldiRecognizer(model, VoiceCog.SAMPLING_RATE)
        log.debug(f"Model loaded, {full_path_to_model=}")

    #def __del__(self):
    #    if self.audio != None:
    #        self.audio.terminate()

    def listen(self, time_limit=5.0) -> str:
        """Blocking voice recognition
        returns text
        """
        result = ""

        try:
            audio = pyaudio.PyAudio()
            stream = audio.open(format=pyaudio.paInt16, channels=1, rate=VoiceCog.SAMPLING_RATE, 
                                input=True, frames_per_buffer=8192)
            start_time = time.monotonic()
            tokens = []
            counter = 0

            # Stop on silence or limiter (sometimes hangs?)
            while time.monotonic() - start_time < time_limit and counter < 100:
                data = stream.read(VoiceCog.FRAMES_LIMIT, exception_on_overflow=True)
                if self.recognizer.AcceptWaveform(data):
                    tokens.append(json.loads(self.recognizer.Result()))
                    start_time = time.monotonic()
                else:
                    counter = counter + 1

            tokens.append(json.loads(self.recognizer.FinalResult()))
            result = ""

            for token in tokens:
                text = token["text"]
                if text:
                    result = result + VoiceCog.WORD_DELIMITER + text

            log.debug(f"Voice recognition result: {result}")
            return result
        except KeyboardInterrupt as err:
            log.error(f"Voice recognition interrupt: {err}")
            return ""
        except Exception as err:
            log.error(f"Voice recognition exception: {err}")
            return ""
        finally:
            stream.close()
            audio.terminate()
