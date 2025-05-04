import discord
from discord.ext import commands
import asyncio
import datetime
import os
import logging
from utils.audio_processing import AudioRecorder
from utils.file_management import save_recording
import config

logger = logging.getLogger('discord-recording-bot.recording')

class RecordingCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_recordings = {}  # {guild_id: {channel_id: recorder}}

    @commands.command(name='grabar', help='Comienza a grabar audio en el canal de voz actual')
    async def start_recording(self, ctx):
        # Verificar si el usuario está en un canal de voz
        if not ctx.author.voice and not hasattr(ctx, 'channel'):
            await ctx.send("Debes estar en un canal de voz para usar este comando.")
            return

        # Obtener el canal de voz
        voice_channel = ctx.author.voice.channel if hasattr(ctx.author, 'voice') and ctx.author.voice else ctx.channel

        # Verificar si ya estamos grabando en este canal
        guild_id = ctx.guild.id
        channel_id = voice_channel.id

        if guild_id in self.active_recordings and channel_id in self.active_recordings[guild_id]:
            await ctx.send("Ya estoy grabando en este canal. Usa `!detener [nombre_grabación]` para detener la grabación actual.")
            return

        # Verificar si el bot ya está conectado al canal de voz
        if ctx.voice_client and ctx.voice_client.channel.id == voice_channel.id:
            voice_client = ctx.voice_client
        else:
            # Conectar al canal de voz
            try:
                voice_client = await voice_channel.connect()
            except Exception as e:
                await ctx.send(f"Error al conectar al canal de voz: {str(e)}")
                logger.error(f'Error al conectar al canal de voz: {e}')
                return

        # Iniciar la grabación
        try:
            recorder = AudioRecorder(voice_client) # Simplified AudioRecorder initialization
            recorder.start()

            # Guardar la referencia a la grabación activa
            if guild_id not in self.active_recordings:
                self.active_recordings[guild_id] = {}

            self.active_recordings[guild_id][channel_id] = {
                'recorder': recorder,
                'start_time': datetime.datetime.now(),
                'voice_client': voice_client
            }

            await ctx.send(f"Grabación iniciada en {voice_channel.name}. Usa `!detener [nombre_grabación]` cuando quieras finalizar.")
            logger.info(f'Grabación iniciada en canal {voice_channel.name} del servidor {ctx.guild.name}')

        except Exception as e:
            await ctx.send(f"Error al iniciar la grabación: {str(e)}")
            logger.error(f'Error al iniciar grabación: {e}')

    @commands.command(name='detener', help='Detiene la grabación actual y la guarda con un nombre opcional')
    async def stop_recording(self, ctx, recording_name=None):
        if ctx.author.bot:
            return
            
        guild_id = ctx.guild.id

        # Verificar si hay grabaciones activas en este servidor
        if guild_id not in self.active_recordings or not self.active_recordings[guild_id]:
            await ctx.send("No hay grabaciones activas en este servidor.")
            return

        # Si el usuario está en un canal de voz, intentar detener la grabación de ese canal
        channel_id = ctx.author.voice.channel.id if ctx.author.voice else None

        # Si no se especificó un canal, o el canal especificado no tiene grabación activa,
        # usar la primera grabación activa del servidor
        if channel_id is None or channel_id not in self.active_recordings[guild_id]:
            channel_id = next(iter(self.active_recordings[guild_id]))

        # Detener la grabación
        try:
            recording_info = self.active_recordings[guild_id][channel_id]
            recorder = recording_info['recorder']
            voice_client = recording_info['voice_client']
            start_time = recording_info['start_time']

            # Obtener los datos de audio
            audio_data = recorder.stop()

            # Verificar si hay datos de audio
            if not audio_data:
                await ctx.send("No se capturaron datos de audio. La grabación no se guardará.")
                logger.warning("No se capturaron datos de audio. La grabación no se guardará.")
                del self.active_recordings[guild_id][channel_id]
                if not self.active_recordings[guild_id]:
                    del self.active_recordings[guild_id]
                if voice_client.is_connected():
                    await voice_client.disconnect()
                return

            # Generar nombre de archivo si no se proporcionó
            if not recording_name:
                recording_name = f"grabacion_{ctx.guild.id}_{channel_id}_{int(datetime.datetime.now().timestamp())}"

            # Guardar la grabación
            date_str = start_time.strftime("%Y-%m-%d")
            file_path = save_recording(
                audio_data,
                recording_name,
                date=date_str,
                sample_rate=config.SAMPLE_RATE,
                channels=config.CHANNELS
            )

            # Eliminar la grabación de las activas
            del self.active_recordings[guild_id][channel_id]
            if not self.active_recordings[guild_id]:
                del self.active_recordings[guild_id]

            # Desconectar el cliente de voz si no hay más grabaciones activas
            if voice_client.is_connected():
                await voice_client.disconnect()

            duration = datetime.datetime.now() - start_time
            hours, remainder = divmod(duration.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)

            await ctx.send(
                f"Grabación guardada como `{recording_name}` ({hours:02}:{minutes:02}:{seconds:02}).\n"
                f"Archivo guardado en: {file_path}"
            )
            logger.info(f'Grabación finalizada y guardada como {recording_name} en {file_path}')

            # Ofrecer transcripción
            await ctx.send(
                f"Puedes transcribir esta grabación usando `!transcribir {recording_name}`"
            )

        except Exception as e:
            await ctx.send(f"Error al detener la grabación: {str(e)}")
            logger.error(f'Error al detener grabación: {e}')


    @commands.command(name='salir', help='Desconecta el bot del canal de voz actual')
    async def leave_voice(self, ctx):
        guild_id = ctx.guild.id

        # Detener todas las grabaciones activas en este servidor
        if guild_id in self.active_recordings:
            for channel_id, recording_info in list(self.active_recordings[guild_id].items()):
                try:
                    recorder = recording_info['recorder']
                    recorder.stop()

                    # No guardamos la grabación al salir forzadamente
                    del self.active_recordings[guild_id][channel_id]
                except Exception as e:
                    logger.error(f'Error al detener grabación al salir: {e}')

            # Eliminar el servidor si no quedan grabaciones
            if not self.active_recordings[guild_id]:
                del self.active_recordings[guild_id]

        # Desconectar el cliente de voz
        if ctx.voice_client:
            await ctx.voice_client.disconnect()
            await ctx.send("Me he desconectado del canal de voz.")

    @commands.command(name='status', help='Muestra el estado de las grabaciones activas')
    async def recording_status(self, ctx):
        guild_id = ctx.guild.id

        if guild_id not in self.active_recordings or not self.active_recordings[guild_id]:
            await ctx.send("No hay grabaciones activas en este servidor.")
            return

        status_message = "Grabaciones activas:\n"

        for channel_id, recording_info in self.active_recordings[guild_id].items():
            channel = self.bot.get_channel(channel_id)
            start_time = recording_info['start_time']
            duration = datetime.datetime.now() - start_time
            hours, remainder = divmod(duration.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)

            status_message += f"- {channel.name}: {hours:02}:{minutes:02}:{seconds:02}\n"

        await ctx.send(status_message)

async def setup(bot):
    await bot.add_cog(RecordingCommands(bot))
    logger.info('Módulo de grabación cargado')