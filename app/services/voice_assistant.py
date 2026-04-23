"""
voice_assistant.py
Voice assistant: Hands-free chat, uploads, and compliance queries.
"""

import speech_recognition as sr
from typing import Callable

class VoiceAssistant:
    def __init__(self):
        self.recognizer = sr.Recognizer()

    def listen(self, callback: Callable[[str], None]):
        with sr.Microphone() as source:
            print("Listening...")
            audio = self.recognizer.listen(source)
            try:
                text = self.recognizer.recognize_google(audio)
                callback(text)
            except Exception as e:
                print(f"Voice recognition error: {e}")

voice_assistant = VoiceAssistant()

# Example usage:
# voice_assistant.listen(lambda text: print(f"You said: {text}"))
