import asyncio
import discord
from discord.ext import commands
from discord import app_commands
import os


# Configura el bot
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Token del bot (asegúrate de que esté seguro)
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise ValueError("⚠️ TOKEN not found. Make sure to set it as an environment variable.")

# Lista de usuarios autorizados (IDs de Discord)
# [Frank, Andrea, Bryan]
AUTHORIZED_USERS = os.getenv("AUTHORIZED_USERS").split(",")

# ID del canal donde se gestionarán las contraseñas
PASSWORD_CHANNEL_ID = int(os.getenv("PASSWORD_CHANNEL_ID"))

class PasswordManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="update_password", description="Update the shared password securely.")
    async def update_password_slash(self, interaction: discord.Interaction, password: str):
        print(f"Slash command invoked by {interaction.user} with password: {password}")

        # Responde de inmediato indicando que está procesando
        await interaction.response.defer(ephemeral=True)

        # Maneja la actualización de la contraseña
        try:
            await self.handle_password_update(interaction, password, is_slash=True)
        except Exception as e:
            print(f"Error handling password update: {e}")
            await interaction.followup.send(
                "❌ An unexpected error occurred while updating the password.", ephemeral=True
            )

    async def handle_password_update(self, ctx_or_interaction, password, is_slash):
        user = ctx_or_interaction.user if is_slash else ctx_or_interaction.author
        channel_id = ctx_or_interaction.channel_id if is_slash else ctx_or_interaction.channel.id

        # Verificar si el usuario está autorizado
        if user.id not in AUTHORIZED_USERS:
            msg = "⛔ You do not have permission to use this command."
            print(f"Unauthorized user {user} tried to update the password.")
            if is_slash:
                await ctx_or_interaction.followup.send(msg, ephemeral=True)
            else:
                await ctx_or_interaction.send(msg)
            return

        # Verificar el canal
        if channel_id != PASSWORD_CHANNEL_ID:
            msg = f"⚠️ This command can only be used in the designated channel. Please use it in <#{PASSWORD_CHANNEL_ID}>."
            print(f"Command invoked in the wrong channel by {user}. Channel ID: {channel_id}")
            if is_slash:
                await ctx_or_interaction.followup.send(msg, ephemeral=True)
            else:
                await ctx_or_interaction.send(msg)
            return

        # Obtener el canal
        channel = self.bot.get_channel(PASSWORD_CHANNEL_ID)
        if not channel:
            msg = "❌ The password management channel was not found."
            print(f"Channel {PASSWORD_CHANNEL_ID} not found.")
            if is_slash:
                await ctx_or_interaction.followup.send(msg, ephemeral=True)
            else:
                await ctx_or_interaction.send(msg)
            return

        # Verificar permisos
        permissions = channel.permissions_for(ctx_or_interaction.guild.me)
        if not permissions.manage_messages or not permissions.read_message_history:
            msg = "⛔ I don't have sufficient permissions to manage messages in this channel."
            print(f"Insufficient permissions in channel {PASSWORD_CHANNEL_ID}.")
            if is_slash:
                await ctx_or_interaction.followup.send(msg, ephemeral=True)
            else:
                await ctx_or_interaction.send(msg)
            return

        # Limpiar mensajes y actualizar contraseña
        await channel.purge()
        message = await channel.send(
            f"🔒 **Updated Isoftware Password:** `{password}` 🔑\n"
            f"👤 **Last updated by:** {user.mention}"
        )
        await message.pin()

        # Notificación final
        if is_slash:
            followup_msg = await ctx_or_interaction.followup.send(
                f"✅ {user.mention}, the password has been updated and pinned successfully! 🎉",
                ephemeral=False 
                )
            
            await asyncio.sleep(7)
            await followup_msg.delete()
        else:
            msg = await ctx_or_interaction.send(
                f"✅ {user.mention}, the password has been updated and pinned successfully! 🎉"
            )
            await asyncio.sleep(10)
            await msg.delete()


@bot.event
async def on_ready():
    print(f"Bot connected as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} commands with Discord.")
        print("Registered commands:")
        for command in synced:
            print(f"- {command.name}: {command.description}")
    except Exception as e:
        print(f"❌ Failed to sync commands: {e}")


# Función principal para inicializar el bot
async def main():
    async with bot:
        await bot.add_cog(PasswordManager(bot))
        await bot.start(TOKEN)


# Ejecuta el bot
asyncio.run(main())