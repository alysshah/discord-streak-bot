import os
import re
from datetime import date, datetime
import pytz  # for time zone handling

import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# load environment variables
load_dotenv()
BOT_PREFIXES = ["sk.", "Sk."]
BOT_TOKEN = os.getenv("BOT_TOKEN")

# specify the channel ID for reminders
CHANNEL_ID = 1313197151739842596
# specify local time zone
LOCAL_TIMEZONE = pytz.timezone("America/New_York")

# discord bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=commands.when_mentioned_or(*BOT_PREFIXES), intents=intents)


###### GOOGLE SHEETS SETUP ##################

# set up Google Sheets API credentials
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
SHEET_NAME = "UMD Womxn's Club Ultimate Throwing Streak"

# load Google credentials from environment variable
import json
google_credentials = os.getenv("GOOGLE_CREDENTIALS")
if not google_credentials:
    raise ValueError("Google credentials not set in environment variables.")

# parse the credentials and authenticate
creds_dict = json.loads(google_credentials)
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
client = gspread.authorize(creds)

# open the google sheet by its name
spreadsheet = client.open(SHEET_NAME)

# access specific worksheets
sheet1 = spreadsheet.worksheet("Sheet1")  # streak summary
sheet2 = spreadsheet.worksheet("Sheet2")  # user contributions


###### GOOGLE SHEETS HELPER FUNCTIONS ##################

"""Remember to set Reminder Time in the google sheet to a value (HH:MM format) first!"""

def load_streak_data():
    """Load streak data from Sheet1, handling empty values."""
    data = sheet1.row_values(2) # load row 2

    # treat message IDs as strings
    log_message_id_today = data[4] if len(data) > 4 and data[4] else None
    log_message_id_today = str(log_message_id_today) if log_message_id_today else None
    
    log_message_id_yesterday = data[6] if len(data) > 6 and data[6] else None
    log_message_id_yesterday = str(log_message_id_yesterday) if log_message_id_yesterday else None

    # safeguard for empty cells
    return {
        "streak_count": int(data[0]) if data[0].isdigit() else 0,
        "start_date": data[1] if len(data) > 1 and data[1] else "N/A",
        "last_logged_date": data[2] if len(data) > 2 and data[2] else "N/A",
        "reminder_time": data[3] if len(data) > 3 and data[3] else "N/A",
        "log_message_id_today": log_message_id_today,
        "log_message_date_today": data[5] if len(data) > 5 and data[5] else "N/A",
        "log_message_id_yesterday": log_message_id_yesterday,
        "log_message_date_yesterday": data[7] if len(data) > 7 and data[7] else "N/A",
        "longest_streak": int(data[8]) if len(data) > 8 and data[8].isdigit() else 0,
        "longest_streak_end_date": data[9] if len(data) > 9 and data[9] else "N/A"
    }

def save_streak_data(data):
    """Save streak data to Sheet1."""
    sheet1.update('A2:J2', [[
        data["streak_count"],
        data["start_date"],
        data["last_logged_date"],
        data["reminder_time"],
        str(data["log_message_id_today"]) if data.get("log_message_id_today") else "",
        data.get("log_message_date_today", ""),
        str(data["log_message_id_yesterday"]) if data.get("log_message_id_yesterday") else "",
        data.get("log_message_date_yesterday", ""),
        data["longest_streak"],
        data["longest_streak_end_date"]
    ]])

def load_user_data():
    """Load all user contributions from Sheet2."""
    return sheet2.get_all_records()

def save_user_data(user_id, username, contributions, last_log):
    """Save or update a user's contribution data. If user already exists, update their row. Else, append a new row."""
    users = load_user_data()

    # check if the user already exists
    for i, user in enumerate(users, start=2):  # row 2 onwards (after headers)
        if str(user["User ID"]).strip() == str(user_id).strip():
            # update existing user data
            new_contributions = int(user["Contributions"]) + contributions
            sheet2.update(f"B{i}:D{i}", [[username, new_contributions, last_log]])
            return

    # if user doesn't exist, append a new row
    sheet2.append_row([user_id, username, contributions, last_log])

def check_user_log_today(user_id):
    """Check if a user has already logged today."""
    today = str(datetime.now(LOCAL_TIMEZONE).date())
    return check_user_log_on_date(user_id, today)

def check_user_log_on_date(user_id, date_str):
    """Check if a user has already logged on a specific date."""
    users = load_user_data()  # load all user records

    # loop through each user in the data
    for user in users:
        recorded_user_id = str(user["User ID"]).strip()
        last_log = str(user["Last Log"]).strip()

        if recorded_user_id == str(user_id).strip() and last_log == date_str:
            return True  # user already contributed on this date

    return False  # user has not contributed on this date


###### SEND REMINDER ##################

@tasks.loop(minutes=1)  # check every minute
async def check_reminder(): 
    """Background task to check and send reminders."""
    streak_data = load_streak_data()
    reminder_time = streak_data.get("reminder_time", "N/A")

    if reminder_time == "N/A":
        return  # no reminder time set
    
    # get current local time in HH:MM format
    now = datetime.now(LOCAL_TIMEZONE).strftime("%H:%M")

    # if the current time matches the reminder time
    if now == reminder_time:
        today = str(datetime.now(LOCAL_TIMEZONE).date())
        last_logged_date = streak_data.get("last_logged_date", "N/A")

        # check if no contributions have been made today
        if last_logged_date != today:
            channel = bot.get_channel(CHANNEL_ID)
            if channel:
                await channel.send(
                    "🌟 **Reminder:** Don't forget to log a contribution today!"
                )


###### BOT EVENT ##################

@bot.event
async def on_ready():
    print("StreakKeeper is ready!")
    #channel validation and reminder check start
    channel = bot.get_channel(CHANNEL_ID)
    if channel is None:
        print(f"Error: Channel ID {CHANNEL_ID} not found or bot lacks access.")
    else:
        if not check_reminder.is_running():
            check_reminder.start()


###### REACTION TRACKING ##################

@bot.event
async def on_reaction_add(reaction, user):
    """
    Track reactions on the streak log message.
    Users can react with ➕ to gain a contribution for the message's date.
    """
    # step 1: ignore bot reactions
    if user.bot:
        return

    # step 2: verify emoji
    if reaction.emoji != "➕":
        return

    # step 3: check if reacting to today's or yesterday's log message
    streak_data = load_streak_data()
    reaction_message_id = str(reaction.message.id)
    message_date = None
    
    if streak_data.get("log_message_id_today") and reaction_message_id == streak_data["log_message_id_today"]:
        message_date = streak_data.get("log_message_date_today")
    elif streak_data.get("log_message_id_yesterday") and reaction_message_id == streak_data["log_message_id_yesterday"]:
        message_date = streak_data.get("log_message_date_yesterday")
    
    if not message_date or message_date == "N/A":
        return # not a valid log message or no date stored

    # step 4: check if the user has already contributed on that date
    user_id = str(user.id)
    if check_user_log_on_date(user_id, message_date):
        return # user already contributed on this date

    # step 5: update user contributions with the message's date
    save_user_data(user_id, user.display_name, 1, message_date)
    # await reaction.message.channel.send(f"🎉 **{user.display_name}** has contributed for {message_date}!")


###### LOG STREAK ##################

def check_milestone(streak_count, start_date):
    """Check milestones and return formatted milestone message."""
    milestones = []

    # day-based milestones (1, 7, and multiples of 50)
    if streak_count in [1, 7] or streak_count % 50 == 0:
        milestones.append(f"🎯 **Day {streak_count}!**")

    # month and year milestones
    if start_date != "N/A":
        start_date_obj = date.fromisoformat(start_date)
        today = datetime.now(LOCAL_TIMEZONE).date()

        # calculate the number of months and years passed
        total_months = (today.year - start_date_obj.year) * 12 + (today.month - start_date_obj.month)
        years_passed = today.year - start_date_obj.year

        # check for exact year milestone (accounting for leap years)
        if today.month == start_date_obj.month and today.day == start_date_obj.day and years_passed > 0:
            milestones.append(f"🏆 **{years_passed} year{'s' if years_passed > 1 else ''} streak!**")
            return milestones

        # check for exact month milestone
        if today.day == start_date_obj.day and total_months > 0:
            milestones.append(f"📅 **{total_months} month{'s' if total_months > 1 else ''} streak!**")
        
    return milestones

@bot.command(name="log")
async def log(ctx):
    """Log a streak for the day with an image attachment."""
    # step 1: check if the message contains an image attachment
    if not ctx.message.attachments:
        await ctx.send("Did it even happen if there's no proof? 🤔 Please include an image!")
        return

    # step 2: load current streak data
    streak_data = load_streak_data()
    today = datetime.now(LOCAL_TIMEZONE).date()
    current_month = today.month
    current_year = today.year
    today_str = str(today)
    last_logged_date = streak_data["last_logged_date"]

    # error handling in case last logged date is N/A
    try:
        last_logged_date_obj = date.fromisoformat(last_logged_date)
        last_logged_month = last_logged_date_obj.month
        last_logged_year = last_logged_date_obj.year
    except ValueError:
        last_logged_month = None
        last_logged_year = None

    # step 3: check if a new month has started
    if last_logged_month and (current_month != last_logged_month or current_year != last_logged_year):
        # get the previous month's name
        previous_month_name = today.replace(month=last_logged_month).strftime("%B")  # e.g., "January"

        # print the previous month's leaderboard before reset
        await ctx.send(f"🏆 **Last Recorded Leaderboard for {previous_month_name}**:")
        await leaderboard(ctx)  # calls the leaderboard function to print top contributors

        sheet2.batch_clear(["A2:D1000"]) # reset leaderboard in google sheets
        await ctx.send(f"🌟 **New Leaderboard!** All contributions have been reset for {today.strftime('%B')}. This is your chance to make it to the top! 🔥")

    # step 4: check if the user already contributed today
    user_id = str(ctx.author.id)
    username = ctx.author.display_name
    if check_user_log_today(user_id):
        await ctx.send(f"You've already contributed today, {username}! See you tomorrow. 🌟")
        return

    # step 5: update user contributions (first time today)
    save_user_data(user_id, username, 1, today_str)

    # step 6: prevent updating the streak if it's already logged today
    if last_logged_date == today_str:
        await ctx.send("Thanks for contributing! The streak’s already logged for today. 🌟")
        return

    # step 7: check if the streak is broken
    streak_was_broken = False
    if last_logged_date and last_logged_date != "N/A":
        try:
            last_logged_date_obj = date.fromisoformat(last_logged_date)
            days_difference = (date.fromisoformat(today_str) - last_logged_date_obj).days

            if days_difference > 1:  # streak is broken
                # check if current streak is the longest
                current_streak = streak_data["streak_count"]
                if current_streak > streak_data["longest_streak"]:
                    streak_data["longest_streak"] = current_streak
                    streak_data["longest_streak_end_date"] = last_logged_date
                
                streak_data["streak_count"] = 1
                streak_data["start_date"] = today_str  # reset the streak start date
                streak_data["last_logged_date"] = today_str
                await ctx.send("😢 The streak was broken! Starting fresh from today.")
                streak_was_broken = True
        except ValueError: # handle invalid date formats (e.g., "N/A")
            streak_data["last_logged_date"] = None

    # step 8: update the streak for the first log of the day
    if not streak_was_broken: # (skip if already updated due to break)
        streak_data["streak_count"] += 1
        streak_data["last_logged_date"] = today_str
        if streak_data["start_date"] == "N/A" or not streak_data["start_date"]:
            streak_data["start_date"] = today_str  # set start date if missing

    # step 9: check for milestones
    streak_count = streak_data["streak_count"]
    start_date = streak_data["start_date"]

    milestones = check_milestone(streak_count, start_date)
    if milestones:
        milestone_message = "\n".join(milestones)
        await ctx.send(f"🎉 **Milestone reached!**\n{milestone_message}")

    # step 10: post confirmation message and add emoji reaction
    confirmation_message = await ctx.send(
        f"✅ Entry logged! The streak is now **{streak_count} days** long! React with ➕ to contribute!"
    )
    await confirmation_message.add_reaction("➕")

    # shift today's message to yesterday, save new message for today
    streak_data["log_message_id_yesterday"] = streak_data.get("log_message_id_today")
    streak_data["log_message_date_yesterday"] = streak_data.get("log_message_date_today")
    streak_data["log_message_id_today"] = confirmation_message.id
    streak_data["log_message_date_today"] = today_str
    save_streak_data(streak_data)


###### MANUALLY RESET LEADERBOARD ##################

ALLOWED_USERS = {722664432433627209}  # currently: Y

@bot.command(name="resetleaderboard")
async def reset_leaderboard(ctx):
    """Manually resets the leaderboard and posts the last results (Only for approved users)."""
    if ctx.author.id not in ALLOWED_USERS:
        await ctx.send("🚫 You don’t have permission to reset the leaderboard.")
        return

    await ctx.send(f"🏆 **Last Recorded Leaderboard**:")
    await leaderboard(ctx)  # calls the leaderboard function to print top contributors

    sheet2.batch_clear(["A2:D1000"]) # reset leaderboard in google sheets
    await ctx.send(f"🌟 **New Leaderboard!** All contributions have been reset for {datetime.now(LOCAL_TIMEZONE).date().strftime('%B')}. This is your chance to make it to the top! 🔥")

    print("✅ Leaderboard has been reset manually.")


###### LEADERBOARD ##################

@bot.command(name="leaderboard")
async def leaderboard(ctx):
    """Display the top 10 contributors from Sheet2."""
    # step 1: fetch user contribution data
    users = load_user_data()  # load all user data from sheet2
    
    # step 2: sort users by contributions in descending order
    sorted_users = sorted(users, key=lambda x: int(x["Contributions"]), reverse=True)
    
    # step 3: limit to top 10 contributors
    top_contributors = sorted_users[:10]
    
    # step 4: format leaderboard message
    if not top_contributors:
        await ctx.send("No contributions 😢")
        return

    embed = discord.Embed(
        title="Top 10 Contributors",
        color=discord.Color.blue()
    )

    for rank, user in enumerate(top_contributors, start=1):
        embed.add_field(name=f"{rank}. {user['Username']}", value=f"{user['Contributions']} contributions", inline=False)

    await ctx.send(embed=embed)


###### PRINT FUNCTIONS ##################

@bot.command(name="streak")
async def view_streak(ctx):
    """View the current streak and check if it is broken."""
    streak_data = load_streak_data()
    streak_count = streak_data["streak_count"]
    start_date = streak_data["start_date"] if streak_data["start_date"] else "N/A"
    last_logged_date = streak_data["last_logged_date"]

    today = datetime.now(LOCAL_TIMEZONE).date()

    # check if the streak is broken
    if last_logged_date and last_logged_date != "N/A":
        try:
            last_logged_date_obj = date.fromisoformat(last_logged_date)
            days_difference = (today - last_logged_date_obj).days

            if days_difference > 1:  # streak is broken
                # check if current streak is the longest
                if streak_count > streak_data["longest_streak"]:
                    streak_data["longest_streak"] = streak_count
                    streak_data["longest_streak_end_date"] = last_logged_date
                
                streak_data["streak_count"] = 0
                streak_data["last_logged_date"] = "N/A"
                save_streak_data(streak_data)
                await ctx.send("😢 The streak was broken! It's now reset to 0 days.")
                return
        except ValueError:
            pass  # handle invalid dates (e.g., "N/A")

    # display the streak
    await ctx.send(f"🔥 **Current Streak:** {streak_count} days\n📅 **Start Date:** {start_date}")

@bot.command(name="longeststreak")
async def view_longest_streak(ctx):
    """View the longest streak record."""
    streak_data = load_streak_data()
    longest_streak = streak_data["longest_streak"]
    longest_streak_end_date = streak_data["longest_streak_end_date"]
    
    if longest_streak == 0 or longest_streak_end_date == "N/A":
        await ctx.send("🏆 **No streak record yet!** Keep logging to set a new record!")
    else:
        await ctx.send(f"🏆 **Longest Streak:** {longest_streak} days\n📅 **Ended:** {longest_streak_end_date}")

@bot.command(name="remindertime")
async def view_reminder_time(ctx):
    """View the current reminder time."""
    streak_data = load_streak_data()
    reminder_time = streak_data["reminder_time"]
    await ctx.send(f"⏰ **Reminder Time:** {reminder_time}")


###### SET FUNCTIONS ##################

@bot.command(name="setremindertime")
async def set_reminder_time(ctx, time: str = None):
    """Set the reminder time in Sheet1."""
    if not time:
        await ctx.send("You need to provide a time! Use the format `HH:MM` in 24-hour format (e.g., 19:00).")
        return

    # validate time format using regex
    time_format = r"^([01]?[0-9]|2[0-3]):([0-5][0-9])$"
    if not re.match(time_format, time):
        await ctx.send("Invalid time format! Please use `HH:MM` in 24-hour format (e.g., 19:00).")
        return

    # load current streak data
    streak_data = load_streak_data()

    # update the reminder time
    previous_time = streak_data["reminder_time"]
    streak_data["reminder_time"] = time
    save_streak_data(streak_data)  # save to sheet1

    await ctx.send(f"⏰ Reminder time has been updated from `{previous_time}` to `{time}`.")

@bot.command(name="stats")
async def user_stats(ctx, *, member_input: str = None):
    """View individual stats. Defaults to command caller if input is invalid."""
    # load user data from google sheets
    users = load_user_data()

    # default to command caller initially
    member = ctx.author

    # try to resolve the member if input is provided
    if member_input:
        try:
            member = await commands.MemberConverter().convert(ctx, member_input)
        except commands.MemberNotFound:
            # if input is invalid, just ignore it and proceed with the command caller
            pass

    # extract user details
    user_id = str(member.id)
    username = member.display_name

    # find user stats
    user_data = next((user for user in users if str(user["User ID"]).strip() == str(user_id).strip()), None)

    # if user has no contributions
    if not user_data:
        embed = discord.Embed(
            title="📊 User Stats",
            description=f"**{username}** hasn't contributed yet this month.",
            color=discord.Color.yellow()
        )
        await ctx.send(embed=embed)
        return

    # extract stats
    contributions = user_data["Contributions"]
    last_log = user_data["Last Log"]

    # calculate user rank
    sorted_users = sorted(users, key=lambda x: int(x["Contributions"]), reverse=True)
    rank = next((index + 1 for index, user in enumerate(sorted_users) if str(user["User ID"]).strip() == str(user_id).strip()), "N/A")

    # build and send the embed
    embed = discord.Embed(
        title="📊 User Stats",
        color=discord.Color.green()
    )
    embed.set_author(name=username, icon_url=member.avatar.url if member.avatar else None)

    embed.add_field(name="🏆 Rank", value=rank, inline=True)
    embed.add_field(name="🌟 Contributions", value=contributions, inline=True)
    embed.add_field(name="📅 Last Log", value=last_log, inline=False)

    await ctx.send(embed=embed)


bot.run(os.getenv('BOT_TOKEN'))
