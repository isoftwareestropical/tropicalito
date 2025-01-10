from aiohttp import web
from discord.ext import commands
import os

# Environment variables
TECH_SERVER_ID = int(os.getenv("TECH_SERVER_ID", 0))
TECH_CHANNEL_ID = int(os.getenv("TECH_CHANNEL_ID", 0))

class WebhookHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.web_app = web.Application()
        self.web_app.router.add_post("/webhook/pull-request", self.handle_webhook)

    async def handle_webhook(self, request):
        
        try:
            # Parse the incoming webhook payload
            data = await request.json()

            event_type = data.get("eventType")
            if not event_type:
                return web.Response(status=400, text="Missing event type")

            print(f"[WebhookHandler] Event type: {event_type}")

            if event_type != "git.pullrequest.merged":
                return web.Response(status=200, text="Ignored event type")

            # Extract relevant information
            resource = data.get("resource")
            if not resource:
                return web.Response(status=400, text="Missing resource")

            title = resource.get("title", "No Title")
            author = resource.get("createdBy", {}).get("displayName", "Unknown")
            repo = resource.get("repository", {}).get("name", "Unknown")
            source_branch = resource.get("sourceRefName", "Unknown").split('/')[-1]
            target_branch = resource.get("targetRefName", "Unknown").split('/')[-1]

            # Get the thread where the message will be sent
            guild = self.bot.get_guild(TECH_SERVER_ID)
            if not guild:
                return web.Response(status=404, text="Server not found")

            channel = guild.get_channel(TECH_CHANNEL_ID)
            if not channel:
                return web.Response(status=404, text="Channel not found")

            # Send message to the channel
            message = (
                f"✅ **Pull Request Approved**\n"
                f"**Title:** {title}\n"
                f"**Author:** {author}\n"
                f"**Repository:** {repo}\n"
                f"**Source Branch:** `{source_branch}`\n"
                f"**Target Branch:** `{target_branch}`"
            )
            await channel.send(message)
            return web.Response(status=200, text="OK")

        except Exception as e:
            print(f"[WebhookHandler] Error handling webhook: {e}")
            return web.Response(status=500, text="Internal Server Error")

    async def start_webhook_listener(self):
        try:
            runner = web.AppRunner(self.web_app)
            await runner.setup()
            site = web.TCPSite(runner, "0.0.0.0", 3000)
            await site.start()
        except Exception as e:
            print(f"[WebhookHandler] Error starting webhook listener: {e}")


async def setup(bot):
    cog = WebhookHandler(bot)
    await bot.add_cog(cog)
    await cog.start_webhook_listener()