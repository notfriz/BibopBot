import discord
from discord.ext import commands
import logging

logger = logging.getLogger('discord-recording-bot.help')

class HelpCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Reemplazar el comando de ayuda predeterminado
        bot.remove_command('help')
        
    @commands.command(name='help', help='Muestra este mensaje de ayuda')
    async def help_command(self, ctx):
        embed = discord.Embed(
            title="Bot de Grabación de Discord",
            description="Este bot permite grabar y transcribir conversaciones de voz en Discord.",
            color=discord.Color.blue()
        )
        
        # Comandos de grabación
        embed.add_field(
            name="📹 Comandos de grabación",
            value=(
                "**!grabar** - Comienza a grabar en el canal de voz actual\n"
                "**!detener [nombre]** - Detiene la grabación actual y la guarda\n"
                "**!salir** - Desconecta el bot del canal de voz\n"
                "**!status** - Muestra el estado de las grabaciones activas"
            ),
            inline=False
        )
        
        # Comandos de transcripción
        embed.add_field(
            name="📝 Comandos de transcripción",
            value=(
                "**!transcribir [nombre]** - Transcribe una grabación a texto\n"
                "**!listar** - Lista todas las grabaciones disponibles"
            ),
            inline=False
        )
        
        # Comandos generales
        embed.add_field(
            name="ℹ️ Comandos generales",
            value="**!help** - Muestra este mensaje de ayuda",
            inline=False
        )
        
        # Información adicional
        embed.add_field(
            name="📋 Información",
            value=(
                "- El bot comenzará a grabar automáticamente cuando un usuario se una al canal de voz\n"
                "- Las grabaciones se guardan con la fecha y el nombre que especifiques\n"
                "- Puedes transcribir cualquier grabación a texto posteriormente"
            ),
            inline=False
        )
        
        # Pie de página
        embed.set_footer(text="Para más información contacta al administrador del servidor")
        
        await ctx.send(embed=embed)

def setup(bot):
    bot.add_cog(HelpCommands(bot))
    logger.info('Módulo de ayuda cargado')