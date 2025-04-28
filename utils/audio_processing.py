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

class AudioRecorder:
    def __init__(self, voice_client, sample_rate=48000, channels=2):
        self.voice_client = voice_client
        self.sample_rate = sample_rate
        self.channels = channels
        self.recording = False
        self.audio_data = BytesIO()
        self.wav_header_written = False

    def _write_wav_header(self):
        """Escribe el encabezado WAV en el buffer de audio."""
        with wave.open(self.audio_data, 'wb') as wav_file:
            wav_file.setnchannels(self.channels)
            wav_file.setsampwidth(2)  # 16-bit audio
            wav_file.setframerate(self.sample_rate)
            # No escribimos datos aún, solo el encabezado
        self.wav_header_written = True

    def callback(self, data):
        """Callback para procesar datos de audio recibidos."""
        if self.recording:
            try:
                if not self.wav_header_written:
                    self._write_wav_header()

                # Convertir datos de audio a PCM
                audio_array = array('h', data)  # 16-bit PCM
                self.audio_data.write(audio_array.tobytes())
            except Exception as e:
                logger.error(f"Error en el callback de audio: {e}")

    def start(self):
        """Inicia la grabación."""
        self.recording = True
        self.audio_data = BytesIO()
        self.wav_header_written = False

        # Configurar el sink para recibir audio
        self.voice_client.listen(self.callback)
        logger.info("Grabación iniciada")

    def stop(self):
        """Detiene la grabación y devuelve los datos de audio."""
        if not self.recording:
            return None

        self.recording = False
        if hasattr(self.voice_client, 'stop_listening'):
            self.voice_client.stop_listening()

        logger.info("Grabación detenida")

        if not self.wav_header_written:
            return None

        # Actualizar el encabezado WAV con el tamaño correcto
        current_pos = self.audio_data.tell()
        file_size = current_pos
        data_size = file_size - 44  # Tamaño del encabezado WAV

        # Actualizar encabezado
        self.audio_data.seek(4)
        self.audio_data.write((file_size - 8).to_bytes(4, byteorder='little'))
        self.audio_data.seek(40)
        self.audio_data.write(data_size.to_bytes(4, byteorder='little'))

        self.audio_data.seek(0)
        return self.audio_data.getvalue()
    
    
async def transcribe_audio(audio_file, api='speech_recognition'):
    """Transcribe un archivo de audio a texto"""
    logger.info(f"Transcribiendo archivo: {audio_file} usando API: {api}")
    
    try:
        if api == 'speech_recognition':
            return await _transcribe_with_sr(audio_file)
        elif api == 'google':
            return await _transcribe_with_google(audio_file)
        else:
            raise ValueError(f"API de transcripción no soportada: {api}")
    except Exception as e:
        logger.error(f"Error en transcripción: {e}")
        raise

async def _transcribe_with_sr(audio_file):
    """Transcribir usando la biblioteca SpeechRecognition"""
    recognizer = sr.Recognizer()
    
    # Ejecutar reconocimiento en un thread separado para no bloquear
    def recognize_thread():
        nonlocal transcript, error
        try:
            with sr.AudioFile(audio_file) as source:
                # Ajustar para ruido ambiental
                recognizer.adjust_for_ambient_noise(source)
                
                # Procesar en segmentos para archivos grandes
                audio_length = source.DURATION
                segment_length = 30  # segundos
                
                full_transcript = []
                
                for i in range(0, int(audio_length), segment_length):
                    # Leer segmento
                    source.stream.seek(int(source.SAMPLE_RATE * i * source.SAMPLE_WIDTH))
                    segment_audio = recognizer.record(source, duration=min(segment_length, audio_length - i))
                    
                    try:
                        # Usar Google Speech Recognition (no requiere API key para uso básico)
                        segment_text = recognizer.recognize_google(segment_audio, language="es-ES")
                        full_transcript.append(segment_text)
                    except sr.UnknownValueError:
                        full_transcript.append("[Inaudible]")
                    except Exception as e:
                        full_transcript.append(f"[Error en transcripción: {str(e)}]")
                
                transcript = " ".join(full_transcript)
        except Exception as e:
            error = str(e)
    
    # Inicializar variables para el thread
    transcript = ""
    error = None
    
    # Ejecutar reconocimiento en un thread
    thread = threading.Thread(target=recognize_thread)
    thread.start()
    
    # Esperar a que termine sin bloquear el event loop
    while thread.is_alive():
        await asyncio.sleep(0.1)
    
    if error:
        raise Exception(f"Error en transcripción con SpeechRecognition: {error}")
    
    return transcript

async def _transcribe_with_google(audio_file):
    """Transcribir usando Google Cloud Speech-to-Text API"""
    try:
        from google.cloud import speech
        
        # Verificar credenciales
        if not config.GOOGLE_APPLICATION_CREDENTIALS:
            raise ValueError("No se encontraron credenciales para Google Cloud Speech-to-Text")
        
        client = speech.SpeechClient()
        
        # Leer el archivo de audio
        with open(audio_file, "rb") as audio_file:
            content = audio_file.read()
        
        audio = speech.RecognitionAudio(content=content)
        
        # Configurar reconocimiento
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=config.SAMPLE_RATE,
            language_code="es-ES",
            enable_automatic_punctuation=True,
        )
        
        # Detectar operación larga
        operation = client.long_running_recognize(config=config, audio=audio)
        
        # Convertir a tarea asíncrona
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, operation.result)
        
        transcript = ""
        for result in response.results:
            transcript += result.alternatives[0].transcript + " "
        
        return transcript
        
    except Exception as e:
        logger.error(f"Error en transcripción con Google: {e}")
        raise Exception(f"Error en transcripción con Google Cloud: {str(e)}")
    #except ImportError:
    #    logger.error("Google Cloud Speech-to-Text no está instalado. Instala google-cloud-speech para usar esta función.") 