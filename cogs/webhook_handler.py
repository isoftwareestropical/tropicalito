from aiohttp import web
from discord.ext import commands
import discord
import os

# Environment variables
TECH_SERVER_ID = int(os.getenv("TECH_SERVER_ID", 0))
TECH_CHANNEL_ID = int(os.getenv("TECH_CHANNEL_ID", 0))
TECH_THREAD_ID = int(os.getenv("TECH_THREAD_ID", 0))

# In-memory dictionary to store PR ID and associated Discord message ID
pr_message_mapping = {}

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

            # Extract the resource section
            resource = data.get("resource")
            if not resource:
                return web.Response(status=400, text="Missing resource")

            pr_id = resource.get("pullRequestId")
            if not pr_id:
                return web.Response(status=400, text="Missing PR ID")

            title = resource.get("title", "No Title")
            author = resource.get("createdBy", {}).get("displayName", "Unknown")
            repo = resource.get("repository", {}).get("name", "Unknown")
            source_branch = resource.get("sourceRefName", "Unknown").split('/')[-1]
            target_branch = resource.get("targetRefName", "Unknown").split('/')[-1]
            status = resource.get("status", "Unknown")
            pr_url = resource.get("_links", {}).get("web", {}).get("href", "#")

            # Get the server and thread
            guild = self.bot.get_guild(TECH_SERVER_ID)
            if not guild:
                return web.Response(status=404, text="Server not found")

            channel = guild.get_channel(TECH_CHANNEL_ID)
            if not channel:
                return web.Response(status=404, text="Channel not found")

            thread = channel.get_thread(TECH_THREAD_ID)
            if not thread:
                print(f"[WebhookHandler] Thread not found: {TECH_THREAD_ID}")
                return web.Response(status=404, text="Thread not found")

            # Handle PR Created Event
            if event_type == "git.pullrequest.created":
                embed = discord.Embed(
                    title="🚀 Pull Request Created",
                    description=f"**Title:** [{title}]({pr_url})\n"
                                f"**Author:** {author}\n"
                                f"**Repository:** {repo}\n"
                                f"**Branch:** `{source_branch}` → `{target_branch}`\n"
                                f"**PR ID:** `{pr_id}`\n"
                                f"**Status:** Created",
                    color=discord.Color.yellow()
                )
                sent_message = await thread.send(embed=embed)

                # Store the PR ID and associated message ID
                pr_message_mapping[pr_id] = {
                    "message_id": sent_message.id,
                    "pr_url": pr_url
                }
                print(f"[WebhookHandler] PR {pr_id} message created with ID {sent_message.id}")

            # Handle PR Updated Event
            elif event_type == "git.pullrequest.updated":
                if status.lower() in ["completed", "active"]:
                    # Find the original message details
                    pr_data = pr_message_mapping.get(pr_id)
                    if pr_data:
                        message_id = pr_data["message_id"]
                        stored_pr_url = pr_data["pr_url"]  # Use the stored URL

                        # Fetch the original message
                        original_message = await thread.fetch_message(message_id)
                        # Update the embed with the new status
                        updated_embed = discord.Embed(
                            title="✅ Pull Request Completed",
                            description=f"**Title:** [{title}]({stored_pr_url})\n"
                                        f"**Author:** {author}\n"
                                        f"**Repository:** {repo}\n"
                                        f"**Branch:** `{source_branch}` → `{target_branch}`\n"
                                        f"**PR ID:** `{pr_id}`\n"
                                        f"**Status:** {status.capitalize()}",
                            color=discord.Color.yellow() if status.lower() == "active" else discord.Color.green()
                        )
                        await original_message.edit(embed=updated_embed)
                        print(f"[WebhookHandler] PR {pr_id} message updated with status {status.capitalize()}")

                    # Send a new notification for merged PRs
                    if status.lower() == "completed":
                        merge_notification = discord.Embed(
                            title="✅ Pull Request Approved",
                            description=f"Pull request [{title}]({stored_pr_url}) with ID `{pr_id}` "
                                        f"has been merged from `{source_branch}` into `{target_branch}`.",
                            color=discord.Color.green()
                        )
                        await thread.send(embed=merge_notification)
                        print(f"[WebhookHandler] PR {pr_id} merged notification sent.")

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
            print("[WebhookHandler] Webhook listener started on port 3000.")
        except Exception as e:
            print(f"[WebhookHandler] Error starting webhook listener: {e}")


async def setup(bot):
    cog = WebhookHandler(bot)
    await bot.add_cog(cog)
    await cog.start_webhook_listener()