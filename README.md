# StreakKeeper

## General Information

### Description

StreakKeeper is a Discord bot designed to track and maintain streaks with ease. Built with Python and integrated with Google Sheets for data storage, it offers an interactive and efficient way to log contributions, track progress, celebrate milestones, and and remind users to contribute. By leveraging the Discord API and Google Sheets, StreakKeeper automates streak tracking while allowing for transparency and manual adjustments as needed.

This bot was created to automate streak tracking for UMD Womxn's Club Ultimate's Discord server, providing a fun and competitive way for team members to log their throws and maintain a streak together. While tailored to this specific case, the bot's design can be adapted for any type of streak tracking.

### Features

- **Daily Logging**: Log your contributions with a quick command or reaction.
- **Reaction Tracking**: Keeps streak tracking flexible for group activities.
- **Monthly Leaderboards**: Ranks contributors for a competitive, motivating aspect. Contributions reset at the start of each month, providing fresh competition.
- **Milestone Celebrations**: Recognizes key achievements like streak length and anniversaries.
- **User Stats**: Shows individual contributions and rank.
- **Customizable Reminder Time**: Automatically reminds users to contribute at a specified time.
- **Google Sheets Integration**: Stores all data for transparency, manual updates, and visualizations.

### Commands

The bot uses the `sk.` (or `Sk.`) prefix for commands. Here’s what it supports:
| **Command** | **Description** |
|----------------------------|------------------------------------------------------------------------|
| `sk.log` | Logs a daily contribution with an image attachment |
| `sk.streak` | Displays the current streak count and its start date |
| `sk.leaderboard` | Shows the top 10 contributors ranked by total contributions |
| `sk.stats [user]` | Displays stats for a specific user or yourself if no user is mentioned |
| `sk.remindertime` | Displays the current reminder time stored in the Google Sheet |
| `sk.setremindertime HH:MM` | Updates the reminder time in the Google Sheet (24-hour format) |

## Building StreakKeeper

### Building a Discord Bot

Discord is the platform our team uses to communicate and share updates, making it a natural place to integrate a streak tracker. Building a bot for Discord involves setting up a connection between the bot and Discord's API, which allows it to interact with servers, users, and messages.

To create StreakKeeper, I used the Python library [discord.py](https://discordpy.readthedocs.io/en/stable/), a powerful wrapper for the Discord API. Here's a general breakdown of what goes into building a Discord bot:

1. **Setting Up the Bot**:
   - I registered the bot with the Discord Developer Portal to get a unique token that identifies it. This token allows the bot to connect to Discord's servers.
   - Configuring the bot's permissions ensures it can perform the necessary actions, like reading messages, tracking reactions, and sending responses.
2. **Connecting to Discord**:
   - Using `discord.py`, I created an event loop to connect the bot to Discord and handle commands or events, such as logging a streak, tracking reactions, or displaying leaderboards.
   - The bot listens for messages and user interactions, processes them, and responds accordingly.
3. **Interactive Features**:
   - To make the bot user-friendly, I implemented commands with a prefix (`sk.`) that trigger specific actions, like viewing stats or logging a streak.
   - Reaction tracking was added so users could contribute to the streak by reacting with a specific emoji, creating a fun and interactive way to stay engaged.
4. **Error Handling**:
   - Anticipating issues like invalid commands or typos, I added error handling to ensure the bot could respond gracefully, either by ignoring invalid input or providing helpful feedback.
   - By combining these elements, I built a bot that integrates seamlessly with our Discord server, enabling us to automate what would otherwise be a manual process. This approach keeps everything centralized and accessible to the team while leveraging Discord's capabilities for communication and interaction.

### Google Sheets Integration

Google Sheets serves as the backend for StreakKeeper, providing a simple yet powerful way to store and manage data. Using the Google Sheets API alongside Python's [gspread](https://docs.gspread.org/en/v6.1.3/) library, I integrated this tool to handle streak tracking in a transparent and accessible manner.

#### Why Google Sheets?

1. **Persistent Storage**:
   - Initially, I used a JSON file to track streak data locally. While this approach worked during development, I quickly realized it would have limitations when deploying the bot to Heroku. Heroku uses an ephemeral filesystem, meaning all files reset each time a restart happens (which would occur at least once a day). This would cause the streak data to be lost after each restart.
   - To solve this issue, I transitioned to Google Sheets, which offers external, persistent, and FREE storage. This ensures data remains intact and accessible regardless of the bot's hosting environment or restarts.
2. **Transparency and Manual Control**:
   - The spreadsheet format makes it easy to view and edit the data directly. If there’s ever a mistake, it can be corrected manually without modifying the bot’s code.
   - This transparency also allows for creating visualizations like graphs or summary reports using the same data.
3. **Accessibility**:
   - With proper permissions, the sheet is accessible to other users. This means even non-technical users can interact with the streak data when necessary.

#### Technical Details

1. **Google Sheets API**:
   - I used the `gspread` library to interface with the Google Sheets API. This library simplifies common actions like reading, writing, and updating rows or columns.
   - To authenticate, the bot uses a service account key file (`credentials.json`). This allows the bot to access and update the spreadsheet securely.
2. **Data Structure**:
   - The spreadsheet is divided into two sheets:
     - **Streak Summary**: Tracks the overall streak count, start date, last logged date, reminder time, and the ID of the most recent log message for reaction tracking.
     - **User Contributions**: Records individual user data, including contributions and the last log date.
3. **Dynamic Updates**:
   - Each time a command or reaction is logged, the bot updates the relevant data in real-time, ensuring the spreadsheet reflects the current state of the streak.
   - This dynamic integration automates the process, reducing manual input while keeping the streak accurate and up-to-date.

#### What This Enables

1. **Automation**:
   - The bot automatically tracks streak contributions, milestones, and stats, updating the sheet in real time.
2. **Customization**:
   - Users can modify fields like reminder times or manually edit streak details if needed, allowing for flexibility in adapting to the team’s needs.
3. **Data Utilization**:
   - With data stored in Google Sheets, it’s easy to create additional features like visual graphs or analytics. For example, the team could chart streak trends or compare individual contributions over time.

Google Sheets strikes a balance between automation and manual control, making it a reliable and accessible choice for StreakKeeper’s backend. This setup ensures data integrity, adaptability, and transparency while leveraging Google’s free(!) and reliable tools.

### Thought Process Behind StreakKeeper

StreakKeeper is designed to be a versatile streak-tracking bot, but its functionalities were specifically tailored to meet the needs and habits of my ultimate frisbee team. While the general framework can be adapted to any streak-tracking scenario, the choices I made reflect how we operate as a group and how we wanted to approach maintaining a streak.

#### Adapting to Team Needs

1. **Reaction Tracking**:
   - Ultimate is a team-oriented sport, and many of us often practice together in groups. Including reaction tracking means that when one person logs a streak with a photo, others can add a reaction to confirm they participated. This avoids redundant messages and makes it easier for multiple people to contribute to the streak while keeping the Discord channel tidy.
2. **Leaderboards**:
   - As a competitive team, having a leaderboard adds a friendly, motivational element. It rewards consistency and encourages players to take initiative in contributing to the streak. This feature also allows for fun recognition moments, like shouting out the top contributors at meetings or in team discussions.
3. **Multiple Logs per Day**:
   - Instead of restricting contributions to just one per day, I allowed for multiple logs. This ensures that additional efforts by teammates are recognized rather than ignored. It also helps maintain momentum, as seeing others contribute encourages participation.

#### Monthly Leaderboard Reset

At the start of each month, **all individual contributions reset to zero** to encourage fresh competition. When the first contribution of a new month is logged:

1. The final leaderboard of the previous month is displayed in the channel.
2. All contribution data is cleared, and the leaderboard starts fresh.
3. The streak itself continues, but the leaderboard rankings reset.

This ensures that:

- Everyone has an equal chance to rank highly each month.
- The leaderboard remains active, even if some users fall behind.
- Past efforts are acknowledged before resetting.
  Since the streak itself does not reset, **milestones and overall streak tracking continue as usual**.

#### Reminder Time

The **reminder system** ensures the streak stays active by nudging users to contribute if they haven't already. This feature balances automation with user interaction by only reminding users when necessary. These automated reminders reduce the need for manual check-ins and ensure no days are accidentally skipped. Here's how it works:

1. **Customization**:
   - Users can view the current reminder time using `sk.remindertime`.
   - The `sk.setremindertime HH:MM` command updates the time in the Google Sheet, which the bot references for reminders. This allows us to set times that work best for our schedules.
2. **Periodic Check**:
   - A background task runs every minute, comparing the current time (adjusted to the correct timezone) with the reminder time in the sheet. While this is pretty frequent, it should have a negligible impact on performance since the operation is lightweight.
   - The bot uses the `pytz` library to ensure the reminder time aligns with the correct timezone, avoiding discrepancies due to server time settings. The default timezone is `America/New_York`, but this can be adjusted in the code if needed.
   - If no contributions have been logged for the day, the bot sends a reminder message to the specified channel.

#### Balancing Automation and Interaction

The goal with StreakKeeper was to automate something we would’ve otherwise done manually, making it more interactive and engaging. By connecting the bot to Google Sheets and using reaction tracking and leaderboards, I was able to create a system that not only keeps the streak alive but also strengthens team involvement. Each design choice—from allowing multiple contributions to avoiding reminders—was shaped by how we as a team wanted to interact with the streak.

StreakKeeper is more than just a bot; it’s a tool for fostering consistency, collaboration, and a little bit of friendly competition. While it’s specific to our needs, I believe these ideas can be adapted for streak-tracking in a variety of contexts.
