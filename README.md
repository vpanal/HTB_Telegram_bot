# HTB_Telegram_bot

This script is a Telegram bot written in Python using the `python-telegram-bot` library. The bot fetches data from the Hack The Box platform and allows users to interact with it using Telegram commands and inline keyboard buttons.

## Requirements

- Python 3.10+ (the bot uses `match`/`case` syntax and the async `python-telegram-bot` v21+ API)

## Installation

It's recommended to install the dependencies in a Python virtual environment (`venv`) to keep them isolated from your system's Python packages.

1. Clone the repository:

   ```bash
   git clone https://github.com/vpanal/HTB_Telegram_bot.git
   cd HTB_Telegram_bot
   ```

2. Create and activate a virtual environment:

   ```bash
   python3 -m venv venv

   # Linux / macOS
   source venv/bin/activate

   # Windows (PowerShell)
   venv\Scripts\Activate.ps1
   ```

3. Install the required packages:

   ```bash
   pip install -r requeriments.txt
   ```

4. When you're done using the bot, you can deactivate the virtual environment with:

   ```bash
   deactivate
   ```

## Configuration

The bot is configured using environment variables, loaded from a `.env` file (via [`python-dotenv`](https://pypi.org/project/python-dotenv/)). A `.env` file keeps your secrets (tokens, IDs, etc.) out of the source code and out of version control — the `.gitignore` in this repo already excludes `.env` so you don't accidentally commit it.

1. Copy the example file to create your own `.env`:

   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and fill in your own values:

   | Variable             | Description                                                                                   |
   |----------------------|-----------------------------------------------------------------------------------------------|
   | `ALLOWED_CHAT_IDS`   | Comma-separated Telegram chat IDs allowed to use the bot (e.g. `123456,654321`).               |
   | `ADMIN_CHAT_IDS`     | Comma-separated Telegram chat IDs with administrator permissions (e.g. `123456`).              |
   | `TELEGRAM_BOT_TOKEN` | Telegram bot token obtained from [BotFather](https://t.me/BotFather).                          |
   | `HTB_USER_IDS`       | Comma-separated Hack The Box user IDs to track (e.g. `1111,2222,3333`).                        |
   | `HTB_BEARER_TOKEN`   | Bearer Token obtained from the Hack The Box platform.                                          |
   | `WIKI_URL`           | URL to your team's Wiki/Notion, shown as a button in the bot menu (optional).                   |
   | `CACHE_TTL_MINUTES`  | Minutes the cached HTB data stays valid before the bot queries the API again (default `60`).    |
   | `PROXY_ENABLED`      | `true` or `false`. Routes HTB API requests through an HTTP(S) proxy (e.g. Burp Suite). **Local debugging only: it disables TLS certificate verification.** |
   | `PROXY_URL`          | Proxy URL to use when `PROXY_ENABLED=true` (e.g. `http://127.0.0.1:8080`).                     |

3. Make sure you have a working Telegram bot. If you don't have one, create a new bot using BotFather on Telegram and obtain the bot token.

> **Note:** if `TELEGRAM_BOT_TOKEN` or `HTB_BEARER_TOKEN` are missing, the bot refuses to start and tells you which variables need to be filled in. If `ALLOWED_CHAT_IDS` is empty the bot starts but rejects every chat.

## Running the Bot

Once you have activated your virtual environment and configured `.env`, you can run the bot with:

```bash
python htb_bot.py
```

The bot will start running and listening for incoming messages and interactions.

## Bot Commands

- `/htb`: Start the bot and display the main menu to choose actions.
- `/help`: Display a help message (the list adapts to whether you are an admin).
- `/search <text>`: Search Hack The Box users and teams by name and get their IDs.

**Admin-only Commands:**

- `/cachedate`: Displays the date and time of the cached Hack The Box data.
- `/refresh`: Forces an immediate refresh of the cached data.
- `/adduser <id[,id]>`: Adds Hack The Box users to the list of users tracked by the bot. Non-numeric IDs are rejected.
- `/purgeuser <id[,id]>`: Removes Hack The Box users from the tracked list.

## Main Features

The bot browses the Hack The Box platform through its internal API and tracks the
progress of a fixed list of users (`HTB_USER_IDS`). Every content view shows, for
each tracked user, whether they have already completed it.

1. **Machines**: latest active machine, machines by difficulty, and unreleased machines, with OS, difficulty, release date and user/root own counts.
2. **Starting Point**: the three tiers with your completion percentage, and the machines inside each tier.
3. **Challenges**: browse by category and difficulty, with solves, release date and category.
4. **Sherlocks**: browse the DFIR labs by category, with difficulty, solves, rating, tags and XP.
5. **Fortresses**: fortress list with flag count and per-user flag progress.
6. **Pro Labs**: lab list with machine and flag counts, skill level, lab masters and whether your plan can play them.
7. **Seasons**: season list with pagination and per-user tier, ranking and flags.
8. **Rankings / Hall of Fame**: top users, teams and countries.
9. **Users**: for each tracked user, the basic profile plus three extra views:
   - **📊 Progress**: completion per content type (machines, challenges, sherlocks, fortresses, pro labs) and badge count.
   - **⚡ XP**: level, level title, total XP and the daily streak (including whether it is at risk).
   - **🏆 Seasons**: the user's rank and league in every season they played.

### About the Hack The Box API

The bot talks to the **internal, undocumented** API of `labs.hackthebox.com`
(`/api/v4`, `/api/v5` and `/api/experience/v1`). It is not a public or supported
API and it can change without notice, so all calls are defensive: a failing or
changed endpoint degrades that single view into a "no data" message instead of
breaking the bot. Only `GET` endpoints are used — the bot never submits flags,
spawns VMs or writes anything to your account.

Authentication uses a Bearer token. The recommended way to obtain one is to
create an **App Token** in *Account Settings → API Tokens* of your HTB account
and put it in `HTB_BEARER_TOKEN`.

## Important Note

- Make sure to keep your bot token and other sensitive information secure and do not share it publicly.
- Never commit your `.env` file — it's already listed in `.gitignore`. Only `.env.example` (with placeholder values) should be tracked in version control.
- It's recommended to deploy the bot in a secure environment, such as a server, to ensure continuous operation.

## Additional Resources

- `python-telegram-bot` library documentation: [python-telegram-bot](https://python-telegram-bot.readthedocs.io/)
- Hack The Box platform: [Hack The Box](https://www.hackthebox.eu/)
- Hack The Box API: [HTB API](https://documenter.getpostman.com/view/13129365/TVeqbmeq) 

Feel free to modify the script to suit your specific requirements. Happy botting!


## Authors

- [vpanal](https://github.com/vpanal): Pentester.

## License

This project is licensed under the [Creative Commons Attribution-NonCommercial 4.0 International License](https://creativecommons.org/licenses/by-nc/4.0/deed.es). Puedes You can get more information in the [LICENSE](LICENSE) file.
