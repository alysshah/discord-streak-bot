import os
import re
from datetime import date, timedelta

import discord
from discord.ext import commands
from dotenv import load_dotenv
import gspread
from oauth2client.service_account import ServiceAccountCredentials


# load environment variables
load_dotenv()
BOT_PREFIX = "sk."
BOT_TOKEN = os.getenv("BOT_TOKEN")

# discord Bot Setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=BOT_PREFIX, intents=intents)


###### GOOGLE SHEETS SETUP ##################

# set up Google Sheets API credentials
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
CREDS_FILE = "credentials.json"  # path to service account file
SHEET_NAME = "UMD Womxn's Club Ultimate Throwing Streak" 

# authorize and connect to the sheet
creds = ServiceAccountCredentials.from_json_keyfile_name(CREDS_FILE, SCOPE)
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

    # treat log_message_id as a string
    log_message_id = data[4] if len(data) > 4 and data[4] else None
    log_message_id = str(log_message_id) if log_message_id else None

    # safeguard for empty cells
    return {
        "streak_count": int(data[0]) if data[0].isdigit() else 0,
        "start_date": data[1] if len(data) > 1 and data[1] else "N/A",
        "last_logged_date": data[2] if len(data) > 2 and data[2] else "N/A",
        "reminder_time": data[3] if len(data) > 3 and data[3] else "N/A",
        "log_message_id": log_message_id
    }

def save_streak_data(data):
    """Save streak data to Sheet1."""
    sheet1.update('A2:E2', [[
        data["streak_count"],
        data["start_date"],
        data["last_logged_date"],
        data["reminder_time"],
        str(data["log_message_id"])  # ensure it's saved as a string
    ]])

def load_user_data():
    """Load all user contributions from Sheet2."""
    return sheet2.get_all_records()

def save_user_data(user_id, username, contributions, last_log):
    """Save or update a user's contribution data. If user already exists, update their row. Else, append a new row."""
    users = load_user_data()

    # check if the user already exists
    for i, user in enumerate(users, start=2):  # row 2 onwards (after headers)
        if str(user["User ID"]) == user_id:
            # update existing user data
            new_contributions = int(user["Contributions"]) + contributions
            sheet2.update(f"B{i}:D{i}", [[username, new_contributions, last_log]])
            return

    # if user doesn't exist, append a new row
    sheet2.append_row([user_id, username, contributions, last_log])

def check_user_log_today(user_id):
    """Check if a user has already logged today."""
    users = load_user_data()  # load all user records
    today = str(date.today())  # get today's date as a string

    # loop through each user in the data
    for user in users:
        recorded_user_id = str(user["User ID"]).strip()
        last_log = str(user["Last Log"]).strip()

        if recorded_user_id == user_id and last_log == today:
            #print("User has already logged today!")
            return True  # user already contributed today

    #print("User has not logged yet today.")
    return False  # user has not contributed today


###### BOT EVENT ##################

@bot.event
async def on_ready():
    print("StreakKeeper is ready!")

###### REACTION TRACKING ##################

@bot.event
async def on_reaction_add(reaction, user):
    """
    Track reactions on the streak log message.
    Users can react with ➕ to gain a contribution once per day.
    """
    # step 1: ignore bot reactions
    if user.bot:
        return

    # step 2: verify message and emoji
    streak_data = load_streak_data()
    log_message_id = streak_data.get("log_message_id")
    if not log_message_id or str(reaction.message.id) != str(log_message_id) or reaction.emoji != "➕":
        return # ignore unmatched reactions

    # step 3: check if the user has already contributed today
    user_id = str(user.id)
    today = str(date.today())
    if check_user_log_today(user_id):
        return # user already contributed today 

    # step 4: update user contributions
    save_user_data(user_id, user.display_name, 1, today)
    # await reaction.message.channel.send(f"🎉 **{username}** has contributed for today!")


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
        today = date.today()

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
    today = str(date.today())
    last_logged_date = streak_data["last_logged_date"]

    # step 3: check if the user already contributed today
    user_id = str(ctx.author.id)
    username = ctx.author.display_name
    if check_user_log_today(user_id):
        await ctx.send(f"You've already contributed today, {username}! See you tomorrow. 🌟")
        return

    # step 4: update user contributions (first time today)
    save_user_data(user_id, username, 1, today)

    # step 5: prevent updating the streak if it's already logged today
    if last_logged_date == today:
        await ctx.send("Thanks for contributing! The streak’s already logged for today. 🌟")
        return

    # step 6: check if the streak is broken
    if last_logged_date and last_logged_date != "N/A":
        try:
            last_logged_date_obj = date.fromisoformat(last_logged_date)
            days_difference = (date.fromisoformat(today) - last_logged_date_obj).days

            if days_difference > 1:  # streak is broken
                streak_data["streak_count"] = 1
                streak_data["start_date"] = today  # reset the streak start date
                streak_data["last_logged_date"] = today
                save_streak_data(streak_data)
                await ctx.send("😢 The streak was broken! Starting fresh from today.")
                return
        except ValueError: # handle invalid date formats (e.g., "N/A")
            streak_data["last_logged_date"] = None

    # step 7: update the streak for the first log of the day
    streak_data["streak_count"] += 1
    streak_data["last_logged_date"] = today
    if streak_data["start_date"] == "N/A" or not streak_data["start_date"]:
        streak_data["start_date"] = today  # set start date if missing
    save_streak_data(streak_data)

    # step 8: check for milestones
    streak_count = streak_data["streak_count"]
    start_date = streak_data["start_date"]

    milestones = check_milestone(streak_count, start_date)
    if milestones:
        milestone_message = "\n".join(milestones)
        await ctx.send(f"🎉 **Milestone reached!**\n{milestone_message}")

    # step 9: post confirmation message and add emoji reaction
    confirmation_message = await ctx.send(
        f"✅ Entry logged! The streak is now **{streak_count} days** long! React with ➕ to contribute!"
    )
    await confirmation_message.add_reaction("➕")

    # save the message ID for reaction tracking
    streak_data["log_message_id"] = confirmation_message.id
    save_streak_data(streak_data)


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
        await ctx.send("No contributions yet! Be the first to log a streak. 🌟")
        return
    
    # leaderboard_message = "**🏆 Leaderboard (Top 10 Contributors):**\n\n"
    # for rank, user in enumerate(top_contributors, start=1):
    #     username = user["Username"]
    #     contributions = user["Contributions"]
    #     leaderboard_message += f"{rank}. {username} - {contributions} contributions\n"

    # # step 5: send the leaderboard message
    # await ctx.send(leaderboard_message)

    embed = discord.Embed(
        title="🏆 Leaderboard (Top 10 Contributors)",
        color=discord.Color.blue()
    )

    for rank, user in enumerate(sorted_users, start=1):
        embed.add_field(name=f"{rank}. {user['Username']}", value=f"{user['Contributions']} contributions", inline=False)

    embed.set_footer(text="We sow consistency 💦🧑‍🌾, we reap growth 🌱📈!\nDon’t let the streak wither 👀🌽")

    await ctx.send(embed=embed)


###### PRINT FUNCTIONS ##################

@bot.command(name="streak")
async def view_streak(ctx):
    """View the current streak and check if it is broken."""
    streak_data = load_streak_data()
    streak_count = streak_data["streak_count"]
    start_date = streak_data["start_date"] if streak_data["start_date"] else "N/A"
    last_logged_date = streak_data["last_logged_date"]

    today = date.today()

    # check if the streak is broken
    if last_logged_date and last_logged_date != "N/A":
        try:
            last_logged_date_obj = date.fromisoformat(last_logged_date)
            days_difference = (today - last_logged_date_obj).days

            if days_difference > 1:  # streak is broken
                streak_data["streak_count"] = 0
                streak_data["last_logged_date"] = "N/A"
                save_streak_data(streak_data)
                await ctx.send("😢 The streak was broken! It's now reset to 0 days.")
                return
        except ValueError:
            pass  # handle invalid dates (e.g., "N/A")

    # display the streak
    await ctx.send(f"🔥 **Current Streak:** {streak_count} days\n📅 **Start Date:** {start_date}")

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
    user_data = next((user for user in users if str(user["User ID"]) == user_id), None)

    # if user has no contributions
    if not user_data:
        embed = discord.Embed(
            title="📊 User Stats",
            description=f"**{username}** hasn't contributed yet. Be the first to log a streak! 🌟",
            color=discord.Color.yellow()
        )
        await ctx.send(embed=embed)
        return

    # extract stats
    contributions = user_data["Contributions"]
    last_log = user_data["Last Log"]

    # calculate user rank
    sorted_users = sorted(users, key=lambda x: int(x["Contributions"]), reverse=True)
    rank = next((index + 1 for index, user in enumerate(sorted_users) if str(user["User ID"]) == user_id), "N/A")

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