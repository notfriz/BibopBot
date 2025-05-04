import asyncio
import discord
import wave
import logging
import os
import speech_recognition as sr
import threading
import numpy as np
from array import array
from io import BytesIO
import config

logger = logging.getLogger('discord-recording-bot.audio_processing')

class AudioSink(discord.AudioSink):
    def __init__(self, recorder):
        self.recorder = recorder

    def write(self, data):
        self.recorder._write_audio(data.data)

class AudioRecorder:
    def __init__(self, voice_client, sample_rate=48000, channels=2):
        self.voice_client = voice_client
        self.sample_rate = sample_rate
        self.channels = channels
        self.recording = False
        self.audio_data = BytesIO()
        self.wav_header_written = False
        self.sink = AudioSink(self)

    def _write_wav_header(self):
        """Escribe el encabezado WAV en el buffer de audio."""
        with wave.open(self.audio_data, 'wb') as wav_file:
            wav_file.setnchannels(self.channels)
            wav_file.setsampwidth(2)  # 16-bit audio
            wav_file.setframerate(self.sample_rate)
        self.wav_header_written = True

    def _write_audio(self, data):
        """Escribe datos de audio al buffer."""
        if self.recording:
            try:
                if not self.wav_header_written:
                    self._write_wav_header()
                self.audio_data.write(data)
            except Exception as e:
                logger.error(f"Error writing audio data: {e}")

    def start(self):
        """Inicia la grabación."""
        self.recording = True
        self.audio_data = BytesIO()
        self.wav_header_written = False
        self.voice_client.start_recording(self.sink, encoding='wav', sample_rate=self.sample_rate)
        logger.info("Recording started")

    def stop(self):
        """Detiene la grabación y retorna los datos de audio."""
        if not self.recording:
            return None

        self.recording = False
        self.voice_client.stop_recording()

        # Get the audio data
        audio_data = self.audio_data.getvalue()
        self.audio_data.close()

        return audio_data

async def transcribe_audio(file_path, api='speech_recognition'):
    """Transcribe audio file to text."""
    if api == 'speech_recognition':
        recognizer = sr.Recognizer()
        with sr.AudioFile(file_path) as source:
            audio = recognizer.record(source)
            try:
                return recognizer.recognize_google(audio)
            except sr.UnknownValueError:
                return "Google Speech Recognition could not understand audio"
            except sr.RequestError as e:
                return f"Could not request results from Google Speech Recognition service; {e}"
    else:
        raise ValueError(f"Unsupported transcription API: {api}")