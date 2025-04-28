import discord
from discord.ext import commands
import asyncio
import logging
import config
from modules.recording import setup as setup_recording
from modules.transcription import setup as setup_transcription
from modules.help import setup as setup_help

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('discord-recording-bot')

# Intents necesarios para el bot
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.guild_messages = True

# Crear el bot
bot = commands.Bot(command_prefix=config.COMMAND_PREFIX, intents=intents)

# Variable para almacenar los canales activos
active_voice_channels = {}


@bot.event
async def on_ready():
    logger.info(f'Bot conectado como {bot.user.name}')
    logger.info(f'ID del bot: {bot.user.id}')
    logger.info(f'Prefijo de comandos: {config.COMMAND_PREFIX}')

    # Establecer estado de "escuchando"
    await bot.change_presence(
        activity=discord.Activity(type=discord.ActivityType.listening,
                                  name=f"{config.COMMAND_PREFIX}help"))


@bot.event
async def on_voice_state_update(member, before, after):
    # Ignorar actualizaciones del propio bot
    if member.id == bot.user.id:
        return

    # Si un usuario se unió a un canal de voz
    if before.channel is None and after.channel is not None:
        channel = after.channel
        # Verificar si el bot ya está en este canal
        voice_client = discord.utils.get(bot.voice_clients,
                                         guild=channel.guild)

        if voice_client is None:
            # Conectar al canal si no está ya conectado
            try:
                voice_client = await channel.connect()
                logger.info(
                    f'Bot conectado al canal {channel.name} en {channel.guild.name}'
                )

                # Verificar si ya hay una grabación activa en este canal
                recording_cog = bot.get_cog('RecordingCommands')
                if recording_cog:
                    guild_id = channel.guild.id
                    channel_id = channel.id

                    if guild_id in recording_cog.active_recordings and channel_id in recording_cog.active_recordings[
                            guild_id]:
                        logger.info(
                            f"Ya hay una grabación activa en el canal {channel.name}. No se iniciará una nueva grabación."
                        )
                        return

                    # Iniciar grabación automáticamente
                    ctx = await bot.get_context(
                        await channel.guild.system_channel.send(f""))
                    ctx.voice_client = voice_client
                    ctx.channel = channel
                    await recording_cog.start_recording(ctx)
            except Exception as e:
                logger.error(f'Error al conectar al canal de voz: {e}')


async def setup_cogs():
    # Registrar los módulos (cogs)
    setup_recording(bot)
    setup_transcription(bot)
    setup_help(bot)

    logger.info('Módulos cargados correctamente')


def main():
    # Registrar los módulos (cogs)
    asyncio.run(setup_cogs())

    # Iniciar el bot
    bot.run(config.DISCORD_TOKEN)


if __name__ == "__main__":
    main()
