import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Token de Discord
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')

#Obtener el directorio base del script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Prefijo para comandos
COMMAND_PREFIX = '!'

# Directorio para almacenar grabaciones
RECORDINGS_DIR = os.path.join(BASE_DIR, 'recordings')
if not os.path.exists(RECORDINGS_DIR):
    os.makedirs(RECORDINGS_DIR)

# Directorio para almacenar transcripciones
TRANSCRIPTIONS_DIR = os.path.join(BASE_DIR, 'transcriptions')
if not os.path.exists(TRANSCRIPTIONS_DIR):
    os.makedirs(TRANSCRIPTIONS_DIR)

# Configuración de audio
AUDIO_FORMAT = 'wav'
AUDIO_BITRATE = '128k'
SAMPLE_RATE = 48000
CHANNELS = 2

# Tiempo máximo de grabación (en segundos)
MAX_RECORDING_TIME = 3600*3  # 3 horas

# API de transcripción (google o speech_recognition)
TRANSCRIPTION_API = 'speech_recognition'

# Configuración para API de Google Cloud Speech-to-Text
GOOGLE_APPLICATION_CREDENTIALS = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
if not GOOGLE_APPLICATION_CREDENTIALS:
    raise ValueError("La variable de entorno GOOGLE_APPLICATION_CREDENTIALS no está configurada.")