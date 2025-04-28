import os
import wave
import datetime
import logging
import config

logger = logging.getLogger('discord-recording-bot.file_management')

def save_recording(audio_data, name, date=None, sample_rate=48000, channels=2):
    """
    Guarda los datos de audio en un archivo WAV
    
    Args:
        audio_data: Datos binarios del audio en formato WAV
        name: Nombre base para el archivo
        date: Fecha para organizar las grabaciones (formato YYYY-MM-DD)
        sample_rate: Frecuencia de muestreo del audio
        channels: Número de canales de audio
        
    Returns:
        Ruta al archivo guardado
    """
    try:
        # Sanitizar el nombre del archivo
        name = sanitize_filename(name)
        
        # Si no se proporciona fecha, usar la actual
        if not date:
            date = datetime.datetime.now().strftime("%Y-%m-%d")
            
        # Crear directorio para la fecha si no existe
        dir_path = os.path.join(config.RECORDINGS_DIR, date)
        os.makedirs(dir_path, exist_ok=True)
        
        # Crear ruta completa
        timestamp = datetime.datetime.now().strftime("%H%M%S")
        file_path = os.path.join(dir_path, f"{name}_{timestamp}.{config.AUDIO_FORMAT}")
        
        # Guardar el archivo si los datos son un BytesIO
        with open(file_path, 'wb') as f:
            f.write(audio_data)
            
        logger.info(f"Grabación guardada en {file_path}")
        return file_path
        
    except Exception as e:
        logger.error(f"Error al guardar la grabación: {e}")
        raise

def sanitize_filename(filename):
    """
    Elimina caracteres no válidos para nombres de archivo
    
    Args:
        filename: Nombre de archivo a sanitizar
        
    Returns:
        Nombre sanitizado
    """
    # Caracteres no permitidos en nombres de archivo
    invalid_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
    
    # Reemplazar caracteres no válidos
    for char in invalid_chars:
        filename = filename.replace(char, '_')
        
    # Limitar longitud
    if len(filename) > 100:
        filename = filename[:100]
        
    return filename

def get_recording_path(name):
    """
    Busca un archivo de grabación por nombre
    
    Args:
        name: Nombre de la grabación a buscar
        
    Returns:
        Ruta al archivo o None si no se encuentra
    """
    for root, _, files in os.walk(config.RECORDINGS_DIR):
        for file in files:
            if name in file and file.endswith(f".{config.AUDIO_FORMAT}"):
                return os.path.join(root, file)
                
    return None

def list_recordings():
    """
    Lista todas las grabaciones disponibles
    
    Returns:
        Lista de diccionarios con información de las grabaciones
    """
    recordings = []
    
    for root, _, files in os.walk(config.RECORDINGS_DIR):
        for file in files:
            if file.endswith(f".{config.AUDIO_FORMAT}"):
                # Extraer fecha de la ruta
                rel_path = os.path.relpath(root, config.RECORDINGS_DIR)
                
                # Si la ruta relativa es ".", estamos en el directorio base
                date = rel_path if rel_path != "." else "sin_fecha"
                
                # Extraer nombre base (sin extensión)
                name = os.path.splitext(file)[0]
                
                # Obtener fecha de creación del archivo
                file_path = os.path.join(root, file)
                created_time = datetime.datetime.fromtimestamp(os.path.getctime(file_path))
                
                recordings.append({
                    'name': name,
                    'date': date,
                    'path': file_path,
                    'created': created_time,
                    'size': os.path.getsize(file_path)
                })
                
    return recordings

def delete_recording(name):
    """
    Elimina una grabación por nombre
    
    Args:
        name: Nombre de la grabación a eliminar
        
    Returns:
        True si se eliminó correctamente, False en caso contrario
    """
    path = get_recording_path(name)
    
    if path and os.path.exists(path):
        try:
            os.remove(path)
            
            # Eliminar transcripción si existe
            transcript_path = os.path.join(
                config.TRANSCRIPTIONS_DIR,
                os.path.splitext(os.path.basename(path))[0] + ".txt"
            )
            
            if os.path.exists(transcript_path):
                os.remove(transcript_path)
                
            return True
        except Exception as e:
            logger.error(f"Error al eliminar grabación: {e}")
            
    return False