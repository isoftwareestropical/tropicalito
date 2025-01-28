from aiohttp import web
from discord.ext import commands
import discord
import os
import asyncio
import json

# Environment variables
TECH_SERVER_ID = int(os.getenv("TECH_SERVER_ID", 0))
TECH_CHANNEL_ID = int(os.getenv("TECH_CHANNEL_ID", 0))
TECH_THREAD_ID = int(os.getenv("TECH_THREAD_ID", 0))

ADRIANA_ID = os.getenv("ADRIANA_ID", "0")
ANDREA_ID = os.getenv("ANDREA_ID", "0")
BRYAN_ID = os.getenv("BRYAN_ID", "0")
GERENCIA_TI_ID = os.getenv("GERENCIA_TI_ID", "0")
KEVIN_ID = os.getenv("KEVIN_ID", "0")
LUIS_ID = os.getenv("LUIS_ID", "0")
FRANKLIN_ID = os.getenv("FRANKLIN_ID", "0")

# In-memory dictionary to store PR ID and associated Discord message ID
pr_message_mapping = {}

def get_discord_mention(reviewer_name: str) -> str:
    """
    Tries to match a known reviewer name with a Discord ID.
    If no match is found, returns the original name as a fallback.
    """
    name_lower = reviewer_name.lower()

    # Simple name checks; adjust as needed for your naming patterns
    if "adriana" in name_lower:
        return f"<@{ADRIANA_ID}>"
    elif "andrea" in name_lower:
        return f"<@{ANDREA_ID}>"
    elif "bryan" in name_lower:
        return f"<@{BRYAN_ID}>"
    elif "gerencia ti" in name_lower:
        return f"<@{GERENCIA_TI_ID}>"
    elif "kevin" in name_lower:
        return f"<@{KEVIN_ID}>"
    elif "luis" in name_lower:
        return f"<@{LUIS_ID}>"
    elif "franklin" in name_lower:
        return f"<@{FRANKLIN_ID}>"
    else:
        # Fallback if you don't have them mapped
        return reviewer_name

class WebhookHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.web_app = web.Application()
        self.web_app.router.add_post("/webhook/pull-request", self.handle_webhook)

    async def handle_webhook(self, request):
        try:
            # Parse the incoming webhook payload
            data = await request.json()
            
            print("[WebhookHandler] Full webhook payload:")
            print(json.dumps(data, indent=4))

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
            description = resource.get("description", "").strip()
            if not description:
                description = "No Description Provided"
            author = resource.get("createdBy", {}).get("displayName", "Unknown")
            repo = resource.get("repository", {}).get("name", "Unknown")
            source_branch = resource.get("sourceRefName", "Unknown").split('/')[-1]
            target_branch = resource.get("targetRefName", "Unknown").split('/')[-1]
            status = resource.get("status", "Unknown")
            pr_url = resource.get("_links", {}).get("web", {}).get("href", "#")
            reviewers = resource.get("reviewers", [])
            if not reviewers:
                reviewers_list = "No Reviewers Assigned"
            else:
                reviewers_list = ", ".join(
                    get_discord_mention(r.get("displayName", "Unknown"))
                    for r in reviewers
                )

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
                    description=(
                        f"**Title:** [{title}]({pr_url})\n"
                        f"**Description:** {description}\n"
                        f"**Author:** {author}\n"
                        f"**Repository:** {repo}\n"
                        f"**Branch:** `{source_branch}` → `{target_branch}`\n"
                        f"**PR ID:** `{pr_id}`\n"
                        f"**Reviewers:** {reviewers_list}\n"
                        f"**Status:** Created"
                    ),
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
                # We only care about status == "completed"; ignore all else
                if status.lower() == "completed":
                    # Find the original message details
                    pr_data = pr_message_mapping.get(pr_id)
                    if pr_data:
                        message_id = pr_data["message_id"]
                        stored_pr_url = pr_data["pr_url"]  # Use the stored URL

                        # Fetch the original message
                        original_message = await thread.fetch_message(message_id)

                        # Update the embed with the new status (Completed)
                        updated_embed = discord.Embed(
                            title="✅ Pull Request Completed",
                            description=(
                                f"**Title:** [{title}]({stored_pr_url})\n"
                                f"**Description:** {description}\n"
                                f"**Author:** {author}\n"
                                f"**Repository:** {repo}\n"
                                f"**Branch:** `{source_branch}` → `{target_branch}`\n"
                                f"**PR ID:** `{pr_id}`\n"
                                f"**Reviewers:** {reviewers_list}\n"
                                f"**Status:** Completed"
                            ),
                            color=discord.Color.green()
                        )
                        await original_message.edit(embed=updated_embed)
                        print(f"[WebhookHandler] PR {pr_id} message updated to Completed")

                        # Optionally send a short "merged" notification, then delete it
                        merge_notification = discord.Embed(
                            title="✅ Pull Request Completed",
                            description=(
                                f"Pull request [{title}]({stored_pr_url}) with ID `{pr_id}` "
                                f"has been merged from `{source_branch}` into `{target_branch}`."
                            ),
                            color=discord.Color.green()
                        )
                        notification_message = await thread.send(embed=merge_notification)
                        print(f"[WebhookHandler] PR {pr_id} merged notification sent.")
                        
                        # Wait 10 seconds, then delete the message
                        await asyncio.sleep(10)
                        await notification_message.delete()

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