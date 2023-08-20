# HTB_Telegram_bot

This script is a Telegram bot written in Python using the `python-telegram-bot` library. The bot fetches data from the Hack The Box platform and allows users to interact with it using Telegram commands and inline keyboard buttons.

## Requirements

- Python 3.x

Install the required packages using the following command:

```bash
pip install -r requeriments.txt
```

## Configuration

Before running the bot, you need to make some modifications to the script.

1. Replace the placeholders in the script:

   - `idchat`: Replace this with the allowed chat IDs of the Telegram groups or users where the bot is allowed to operate.
   - `TOKEN`: Replace this with the Telegram bot token obtained from the BotFather.
   - `bearer`: Replace this with the Bearer Token obtained from the Hack The Box platform.
   - `users_ids`: Replace the placeholders (`username`, `idnumer`) with the usernames and corresponding Hack The Box user IDs of the users you want to track. Add more entries as needed.

2. Make sure you have a working Telegram bot. If you don't have one, create a new bot using BotFather on Telegram and obtain the bot token.

## Running the Bot

Once you have configured the script, you can run the bot using the following command:

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
