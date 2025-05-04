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
    if member.id == bot.user.id:
        return

    if before.channel is None and after.channel is not None:
        channel = after.channel
        voice_client = discord.utils.get(bot.voice_clients, guild=channel.guild)

        if voice_client is None:
            try:
                voice_client = await channel.connect(timeout=20.0, reconnect=True)
                logger.info(f'Bot conectado al canal {channel.name} en {channel.guild.name}')

                recording_cog = bot.get_cog('RecordingCommands')
                if recording_cog:
                    guild_id = channel.guild.id
                    channel_id = channel.id

                    if guild_id in recording_cog.active_recordings and channel_id in recording_cog.active_recordings[guild_id]:
                        logger.info(f"Ya hay una grabación activa en el canal {channel.name}")
                        return

                    system_channel = channel.guild.system_channel or channel.guild.text_channels[0]
                    ctx = await bot.get_context(await system_channel.send(""))

                    ctx.voice_client = voice_client
                    ctx.channel = channel
                    await recording_cog.start_recording(ctx)
            except discord.ClientException as e:
                logger.error(f'Error de cliente al conectar al canal de voz: {e}')
            except asyncio.TimeoutError:
                logger.error('Tiempo de espera agotado al intentar conectar al canal de voz')
            except Exception as e:
                logger.error(f'Error inesperado al conectar al canal de voz: {e}')

async def main():
    await bot.load_extension('modules.recording')
    await bot.load_extension('modules.transcription')
    await bot.load_extension('modules.help')
    await bot.start(config.DISCORD_TOKEN)

if __name__ == "__main__":
    asyncio.run(main())