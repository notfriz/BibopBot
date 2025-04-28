import discord
from discord.ext import commands
import os
import logging
from utils.audio_processing import transcribe_audio
import config

logger = logging.getLogger('discord-recording-bot.transcription')

class TranscriptionCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @commands.command(name='transcribir', help='Transcribe una grabación de audio a texto')
    async def transcribe(self, ctx, recording_name=None):
        if not recording_name:
            await ctx.send("Por favor, proporciona el nombre de la grabación a transcribir. Ejemplo: `!transcribir mi_grabacion`")
            return
            
        # Buscar la grabación en el directorio de grabaciones
        recording_files = []
        for root, _, files in os.walk(config.RECORDINGS_DIR):
            for file in files:
                if recording_name in file and file.endswith(f".{config.AUDIO_FORMAT}"):
                    recording_files.append(os.path.join(root, file))
        
        if not recording_files:
            await ctx.send(f"No se encontró ninguna grabación con el nombre '{recording_name}'.")
            return
            
        # Si se encontraron múltiples grabaciones, usar la más reciente
        recording_file = max(recording_files, key=os.path.getctime)
        
        await ctx.send(f"Transcribiendo grabación: {os.path.basename(recording_file)}. Esto puede tardar unos minutos...")
        
        try:
            # Mostrar mensaje de que estamos procesando
            message = await ctx.send("Procesando transcripción...")
            
            # Realizar la transcripción
            transcript = await transcribe_audio(recording_file, api=config.TRANSCRIPTION_API)
            
            # Guardar la transcripción en un archivo
            base_name = os.path.basename(recording_file).rsplit('.', 1)[0]
            transcript_file = os.path.join(config.TRANSCRIPTIONS_DIR, f"{base_name}.txt")
            
            os.makedirs(os.path.dirname(transcript_file), exist_ok=True)
            
            with open(transcript_file, 'w', encoding='utf-8') as f:
                f.write(transcript)
                
            # Dividir la transcripción en trozos si es muy larga para Discord
            chunks = [transcript[i:i+1900] for i in range(0, len(transcript), 1900)]
            
            await message.edit(content=f"Transcripción completada para: {os.path.basename(recording_file)}")
            
            # Enviar la transcripción
            for i, chunk in enumerate(chunks):
                if i == 0:
                    await ctx.send(f"**Transcripción (parte {i+1}/{len(chunks)}):**\n```{chunk}```")
                else:
                    await ctx.send(f"**Parte {i+1}/{len(chunks)}:**\n```{chunk}```")
                    
            # Enviar el archivo de transcripción
            await ctx.send(file=discord.File(transcript_file, f"{base_name}.txt"))
            
            logger.info(f'Transcripción completada para {recording_file}')
            
        except Exception as e:
            await ctx.send(f"Error al transcribir el audio: {str(e)}")
            logger.error(f'Error al transcribir audio: {e}')
            
    @commands.command(name='listar', help='Lista todas las grabaciones disponibles')
    async def list_recordings(self, ctx):
        # Verificar si el directorio de grabaciones existe
        if not os.path.exists(config.RECORDINGS_DIR):
            await ctx.send("No hay grabaciones disponibles.")
            return
            
        # Obtener todas las grabaciones
        recordings = []
        for root, _, files in os.walk(config.RECORDINGS_DIR):
            for file in files:
                if file.endswith(f".{config.AUDIO_FORMAT}"):
                    rel_path = os.path.relpath(os.path.join(root, file), config.RECORDINGS_DIR)
                    recordings.append(rel_path)
                    
        if not recordings:
            await ctx.send("No hay grabaciones disponibles.")
            return
            
        # Organizar grabaciones por fecha (asumiendo que están en carpetas con formato de fecha)
        recordings_by_date = {}
        for recording in recordings:
            parts = recording.split(os.sep)
            if len(parts) > 1:
                date = parts[0]
                name = os.path.join(*parts[1:])
                
                if date not in recordings_by_date:
                    recordings_by_date[date] = []
                    
                recordings_by_date[date].append(name)
            else:
                # Para grabaciones sin fecha en la ruta
                if "sin_fecha" not in recordings_by_date:
                    recordings_by_date["sin_fecha"] = []
                    
                recordings_by_date["sin_fecha"].append(recording)
                
        # Construir mensaje
        message = "**Grabaciones disponibles:**\n"
        
        for date, files in sorted(recordings_by_date.items(), reverse=True):
            message += f"\n**{date}:**\n"
            for file in sorted(files):
                # Obtener el nombre base sin extensión
                name = os.path.basename(file).rsplit('.', 1)[0]
                message += f"- {name}\n"
                
        # Dividir el mensaje si es muy largo
        chunks = [message[i:i+1900] for i in range(0, len(message), 1900)]
        
        for i, chunk in enumerate(chunks):
            if i == 0:
                await ctx.send(chunk)
            else:
                await ctx.send(f"...(continuación)...\n{chunk}")

def setup(bot):
    bot.add_cog(TranscriptionCommands(bot))
    logger.info('Módulo de transcripción cargado')