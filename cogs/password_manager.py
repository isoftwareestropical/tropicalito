import asyncio
import discord
from discord.ext import commands
from discord import app_commands
import os

# Environment-based configuration
AUTHORIZED_USERS = list(map(int, os.getenv("AUTHORIZED_USERS", "").split(",")))
ONLY_DEVS_PASSWORD_CHANNEL_ID = int(os.getenv("ONLY_DEVS_PASSWORD_CHANNEL_ID", 0))
ONLY_DEVS_SERVER_ID = int(os.getenv("ONLY_DEVS_SERVER_ID", 0))


class PasswordManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="update_password", description="Update the shared password securely.")
    async def update_password_slash(self, interaction: discord.Interaction, password: str):
        print(f"Slash command invoked by {interaction.user} with password: {password}")

        # Respond immediately indicating processing
        await interaction.response.defer(ephemeral=True)

        # Handle password update
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
        guild_id = ctx_or_interaction.guild.id if is_slash else ctx_or_interaction.guild.id

        # Verify if the command is in the correct server
        if guild_id != ONLY_DEVS_SERVER_ID:
            msg = "⛔ This command cannot be used in this server."
            print(f"Command invoked in wrong server by {user}. Guild ID: {guild_id}")
            if is_slash:
                await ctx_or_interaction.followup.send(msg, ephemeral=True)
            else:
                await ctx_or_interaction.send(msg)
            return

        # Verify if the user is authorized
        if user.id not in AUTHORIZED_USERS:
            msg = "⛔ You do not have permission to use this command."
            print(f"Unauthorized user {user} tried to update the password.")
            if is_slash:
                await ctx_or_interaction.followup.send(msg, ephemeral=True)
            else:
                await ctx_or_interaction.send(msg)
            return

        # Verify the channel
        if channel_id != ONLY_DEVS_PASSWORD_CHANNEL_ID:
            msg = f"⚠️ This command can only be used in the designated channel. Please use it in <#{ONLY_DEVS_PASSWORD_CHANNEL_ID}>."
            print(f"Command invoked in the wrong channel by {user}. Channel ID: {channel_id}")
            if is_slash:
                await ctx_or_interaction.followup.send(msg, ephemeral=True)
            else:
                await ctx_or_interaction.send(msg)
            return

        # Get the channel
        channel = self.bot.get_channel(ONLY_DEVS_PASSWORD_CHANNEL_ID)
        if not channel:
            msg = "❌ The password management channel was not found."
            print(f"Channel {ONLY_DEVS_PASSWORD_CHANNEL_ID} not found.")
            if is_slash:
                await ctx_or_interaction.followup.send(msg, ephemeral=True)
            else:
                await ctx_or_interaction.send(msg)
            return

        # Verify permissions
        permissions = channel.permissions_for(ctx_or_interaction.guild.me)
        if not permissions.manage_messages or not permissions.read_message_history:
            msg = "⛔ I don't have sufficient permissions to manage messages in this channel."
            print(f"Insufficient permissions in channel {ONLY_DEVS_PASSWORD_CHANNEL_ID}.")
            if is_slash:
                await ctx_or_interaction.followup.send(msg, ephemeral=True)
            else:
                await ctx_or_interaction.send(msg)
            return

        # Clear messages and update the password
        await channel.purge()
        message = await channel.send(
            f"🔒 **Updated isoftware password:** `{password}` 🔑\n"
            f"👤 **Last updated by:** {user.mention}"
        )
        await message.pin()

        # Final notification
        if is_slash:
            followup_msg = await ctx_or_interaction.followup.send(
                f"✅ {user.mention}, isoftware password has been updated. Check channel for more info.",
                ephemeral=False
            )
            await asyncio.sleep(7)
            await followup_msg.delete()
        else:
            msg = await ctx_or_interaction.send(
                f"✅ {user.mention}, isoftware password has been updated. Check channel for more info."
            )
            await asyncio.sleep(10)
            await msg.delete()


async def setup(bot):
    await bot.add_cog(PasswordManager(bot))