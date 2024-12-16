from discord.ext import commands
import discord
import os
from dotenv import load_dotenv
from datetime import date
import re
import json

# Load environment variables from .env
load_dotenv()

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

DATA_FILE = "data.json"


###### JSON HELPER FUNCTIONS ##################

# Load all server data from the JSON file
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as file:
            return json.load(file)
    return {}

# Save all server data back to the JSON file
def save_data(data):
    with open(DATA_FILE, "w") as file:
        json.dump(data, file, indent=4)

# Fetch data for a specific server, initializing defaults if necessary
def get_server_data(guild_id):
    all_data = load_data()
    if str(guild_id) not in all_data:
        all_data[str(guild_id)] = {
            "streak_count": 0,
            "last_logged_date": None,
            "reminder_time": "19:00",
            "user_contributions": {},
            "original_logger_id": None,
            "log_message_id": None
        }
        save_data(all_data)  # Save updated data
    return all_data[str(guild_id)]

# Update data for a specific server
def update_server_data(guild_id, server_data):
    all_data = load_data()
    all_data[str(guild_id)] = server_data
    save_data(all_data)


###### BOT EVENT ##################

@bot.event
async def on_ready():
    print("StreakKeeper is ready!")


###### LEADERBOARD ##################

@bot.command(name="leaderboard")
async def leaderboard(ctx):
    guild_id = ctx.guild.id
    server_data = get_server_data(guild_id)
    contributions = server_data.get("user_contributions", {})

    # Sort contributions by count
    leaderboard = sorted(contributions.items(), key=lambda x: x[1], reverse=True)

    # Limit to top 10 contributors
    top_contributors = leaderboard[:10]

    # Create leaderboard text
    leaderboard_text = "\n".join(
        [f"{index + 1}. <@{user_id}>: {count}x" for index, (user_id, count) in enumerate(top_contributors)]
    )

    if not leaderboard_text:
        await ctx.send("No contributions yet! Be the first to log a streak! 🔥")
    else:
        await ctx.send(f"**Leaderboard (Top 10):**\n{leaderboard_text}")


###### REACTION TRACKING ##################

@bot.event
async def on_reaction_add(reaction, user):
    if user.bot:  # Ignore bot reactions
        return

    guild_id = reaction.message.guild.id
    server_data = get_server_data(guild_id)

    # Check if this is the streak log message
    log_message_id = server_data.get("log_message_id")
    if reaction.message.id != log_message_id or reaction.emoji != "➕":
        return

    # Prevent the original logger from gaining extra contributions
    original_logger_id = server_data.get("original_logger_id")
    if str(user.id) == original_logger_id:
        return

    # Update user contributions
    contributions = server_data.get("user_contributions", {})
    contributions[str(user.id)] = contributions.get(str(user.id), 0) + 1
    server_data["user_contributions"] = contributions
    update_server_data(guild_id, server_data)


###### LOG STREAK ##################

def check_milestone(streak_count):
    if streak_count in [1, 7, 30] or streak_count % 50 == 0 or streak_count % 365 == 0:
        return True
    return False

@bot.command(name="log")
async def log(ctx):
    guild_id = ctx.guild.id
    server_data = get_server_data(guild_id)

    # Check if the message contains an attachment
    if not ctx.message.attachments:
        await ctx.send("Did it even happen if there's no proof? 🤔")
        return

    # Get the current date and last logged date
    today = str(date.today())
    last_logged_date = server_data["last_logged_date"]

    # Count the user's contribution
    contributions = server_data.get("user_contributions", {})
    contributions[str(ctx.author.id)] = contributions.get(str(ctx.author.id), 0) + 1
    server_data["user_contributions"] = contributions

    # Save the data after counting the contribution
    update_server_data(guild_id, server_data)

    # Prevent multiple logs from advancing the streak
    if last_logged_date == today:
        await ctx.send("Thanks! The streak’s logged. See you tomorrow! 🌟")
        return

    # Check if the streak is broken
    if last_logged_date:
        last_logged_date_obj = date.fromisoformat(last_logged_date)
        days_difference = (date.fromisoformat(today) - last_logged_date_obj).days

        if days_difference > 1:  # Streak is broken
            server_data["streak_count"] = 0
            server_data["last_logged_date"] = None
            update_server_data(guild_id, server_data)
            await ctx.send("😢 The streak was broken! Starting fresh from today.")
            return

    # Update the streak
    server_data["streak_count"] += 1
    server_data["last_logged_date"] = today

    # Save the original logger's ID
    server_data["original_logger_id"] = str(ctx.author.id)
    update_server_data(guild_id, server_data)

    # Check for milestones
    if check_milestone(server_data["streak_count"]):
        await ctx.send(f"🎉 **Milestone reached!** {server_data['streak_count']} days of streak! 🚀")

    # Post confirmation and add emoji reaction
    confirmation_message = await ctx.send(
        f"Entry logged! The streak is now {server_data['streak_count']} days long! React with ➕ to contribute!"
    )
    # Bot reacts to its own message
    await confirmation_message.add_reaction("➕")

    # Save the message ID for reaction tracking
    server_data["log_message_id"] = confirmation_message.id
    update_server_data(guild_id, server_data)


###### PRINT FUNCTIONS ##################

@bot.command(name="streak")
async def view_streak(ctx):
    guild_id = ctx.guild.id
    server_data = get_server_data(guild_id)

    today = date.today()
    last_logged_date = server_data["last_logged_date"]

    # Check if the streak is broken
    if last_logged_date:
        last_logged_date_obj = date.fromisoformat(last_logged_date)
        days_difference = (today - last_logged_date_obj).days

        if days_difference > 1:  # Streak is broken
            server_data["streak_count"] = 0
            server_data["last_logged_date"] = None
            update_server_data(guild_id, server_data)
            await ctx.send("😢 The streak was broken! It's now reset to 0 days.")
            return

    # Display the current streak
    streak = server_data["streak_count"]
    await ctx.send(f"The current streak is {streak} days!")

@bot.command(name='remindertime')
async def view_reminder_time(ctx):
    guild_id = ctx.guild.id
    server_data = get_server_data(guild_id)
    await ctx.send(f"The current reminder time is {server_data['reminder_time']}.")

@bot.command(name="stats")
async def user_stats(ctx, member: discord.Member = None):
    guild_id = ctx.guild.id
    server_data = get_server_data(guild_id)
    contributions = server_data.get("user_contributions", {})

    # Default to the command's author if no member is mentioned
    member = member or ctx.author
    user_id = str(member.id)

    # Get the user's contribution count
    user_contributions = contributions.get(user_id, 0)

    # Calculate the user's rank on the leaderboard
    leaderboard = sorted(contributions.items(), key=lambda x: x[1], reverse=True)
    user_rank = next((index + 1 for index, (uid, _) in enumerate(leaderboard) if uid == user_id), None)

    # Generate the response message
    if user_rank:
        await ctx.send(
            f"**{member.display_name}'s Stats:**\n"
            f"🌟 Contributions: {user_contributions}\n"
            f"🏅 Leaderboard Rank: {user_rank}"
        )
    else:
        await ctx.send(f"{member.display_name} has not contributed yet.")


###### SET FUNCTIONS ##################

@bot.command(name='reset')
async def reset_streak(ctx, count: int = 0):
    guild_id = ctx.guild.id
    server_data = get_server_data(guild_id)
    server_data["streak_count"] = count
    server_data["last_logged_date"] = None  # Reset the logged date
    update_server_data(guild_id, server_data)
    await ctx.send(f"The streak has been reset to {count} days.")

@bot.command(name='setremindertime')
async def set_reminder_time(ctx, time: str = None):
    guild_id = ctx.guild.id
    server_data = get_server_data(guild_id)

    # Check if a time string is provided
    if time is None:
        await ctx.send("You need to provide a time! Use the format HH:MM in 24-hour time (e.g., 19:00).")
        return

    # Validate the time format (HH:MM in 24-hour format)
    time_format = r"^([01]?[0-9]|2[0-3]):([0-5][0-9])$"
    if not re.match(time_format, time):
        await ctx.send("Invalid time format! Please use HH:MM in 24-hour format (e.g., 19:00).")
        return

    # Update the reminder time
    prev_time = server_data["reminder_time"]
    server_data["reminder_time"] = time
    update_server_data(guild_id, server_data)
    await ctx.send(f"Reminder time has been updated from {prev_time} to {time}!")


@bot.command(name="setcontributions")
@commands.has_permissions(administrator=True)  # Requires admin permissions
async def set_contributions(ctx, member: discord.Member, contributions: int):
    if contributions < 0:
        await ctx.send("Contributions cannot be negative.")
        return

    guild_id = ctx.guild.id
    server_data = get_server_data(guild_id)

    # Update the user's contributions
    user_id = str(member.id)
    server_data["user_contributions"][user_id] = contributions
    update_server_data(guild_id, server_data)

    await ctx.send(
        f"Contributions for **{member.display_name}** have been set to {contributions}. 🚀"
    )


@set_contributions.error
async def set_contributions_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("Usage: `!setcontributions @member <number>`")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("You do not have permission to use this command.")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("Please mention a valid user and provide a valid number.")
    else:
        await ctx.send("An unexpected error occurred. Please try again.")


###### EXPORT ##################

@bot.command(name="export")
async def export_data(ctx):
    # Ensure the file exists
    if not os.path.exists(DATA_FILE):
        await ctx.send("No data to export. The streak data file doesn't exist yet.")
        return

    # Send the data.json file as an attachment
    try:
        await ctx.send("Here is the exported streak data:", file=discord.File(DATA_FILE))
    except Exception as e:
        await ctx.send(f"Failed to export data: {e}")


bot.run(os.getenv('BOT_TOKEN'))