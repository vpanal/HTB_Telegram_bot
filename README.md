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
   | `WIKI_URL`           | URL to your team's Wiki/Notion, shown as a button in the bot menu.                             |
   | `PROXY_ENABLED`      | `true` or `false`. Enables routing HTB API requests through an HTTP(S) proxy (e.g. Burp Suite).|
   | `PROXY_URL`          | Proxy URL to use when `PROXY_ENABLED=true` (e.g. `http://127.0.0.1:8080`).                     |

3. Make sure you have a working Telegram bot. If you don't have one, create a new bot using BotFather on Telegram and obtain the bot token.

> **Note:** if `TELEGRAM_BOT_TOKEN` is missing, the bot will refuse to start and remind you to configure your `.env` file.

## Running the Bot

Once you have activated your virtual environment and configured `.env`, you can run the bot with:

```bash
python htb_bot.py
```

The bot will start running and listening for incoming messages and interactions.

## Bot Commands

- `/start`: Start the bot and display the main menu to choose actions.
- `/help`: Display a help message.
  
**Additional Commands:**

- `/cachedate`: Displays the current date and time of the Hack The Box platform's cache from where the data is retrieved.
- `/adduser`: Adds a new Hack The Box user to the list of users tracked by the bot.
- `/purgeuser`: Removes a Hack The Box user from the list of users tracked by the bot.

## Main Features

The bot provides the following main features:

1. **Main Menu**: The main menu provides options to access different functionalities.
2. **Machine Information**: The bot can fetch information about released machines, including their name, operating system, difficulty, IP, date, number of user owns, and number of root owns.
3. **Unreleased Machines**: The bot can display information about unreleased machines, including their names, operating systems, and difficulties.
4. **User Information**: The bot can fetch and display the basic profile information for specified Hack The Box users.

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
