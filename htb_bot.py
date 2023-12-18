# -<b>- coding: utf-8 -<b>-
from telegram.ext import (Updater, CommandHandler, CallbackQueryHandler)
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
import requests
import json
from datetime import datetime, timedelta
import threading

# Inicialización de variables de entorno
challenge_category = []
challenge_list = []
machine_list = []
machine_unreleased = []
profile = {}
profile_activity = {}
profile_challenges = {}
country_users_top = {}
users_list = []
menu_user = ''
season_data = {}
cache_date=datetime(2023, 8, 1, 10, 30)

#######Modify this to work#######

#IDs de chat de telegram permitidas
allowed_list=(idchat, idchat)
#IDs de chat de telegram permitidas
admin_list=(idchat, idchat)
#Token de bot de telegram
TOKEN='Token de bot de telegram'
#Usernames y ID de usuarios de HTB
users_ids = [{'user': 'username', 'id': 'idnumer'}, {'user': 'username', 'id': 'idnumer'}]

#Bearer Token de HTB
bearer='BearerToken'

proxy = {
}

#######HTB API#######

#HTB Profile basic info
def htb_profile(uid):
    url = "https://labs.hackthebox.com/api/v4/user/profile/basic/" + str(uid)
    result = htb_request(url)
    result = json.loads(result.text).get('profile')
    return result

#HTB Profile challenges info
def htb_profile_challenges(uid):
    url = "https://labs.hackthebox.com/api/v4/user/profile/progress/challenges/" + str(uid)
    result = htb_request(url)
    result = json.loads(result.text).get('profile')
    return result

#HTB Profile Activity info
def htb_profile_activity(uid):
    url = "https://labs.hackthebox.com/api/v4/user/profile/activity/" + str(uid)
    result = htb_request(url)
    result = json.loads(result.text).get('profile')
    return result

#HTB Country TOP
def htb_country_users_top(country_code):
    url = f"https://labs.hackthebox.com/api/v4/rankings/country/{country_code}/members"
    result = htb_request(url)
    result = json.loads(result.text).get('data').get('rankings', [])
    return result

#HTB Unreleased Machines info
def htb_machine_unreleased():
    url = "https://labs.hackthebox.com/api/v4/machine/unreleased"
    result = htb_request(url)
    result = json.loads(result.text).get('data')
    return result

#HTB Active Machines info
def htb_machine_list():
    url="https://labs.hackthebox.com/api/v4/machine/paginated"
    result = htb_request(url)
    result = json.loads(result.text).get('data')
    return result

#HTB Active Challenges info
def htb_challenge_list():
    url="https://labs.hackthebox.com/api/v4/challenge/list"
    result = htb_request(url)
    result = json.loads(result.text).get('challenges')
    return result

#HTB Challenge Categories
def htb_challenge_categories_list():
    url="https://labs.hackthebox.com/api/v4/challenge/categories/list"
    result = htb_request(url)
    result = json.loads(result.text).get('info')
    return result

#HTB Fortresses
def htb_fortresses():
    url="https://labs.hackthebox.com/api/v4/fortresses"
    result = htb_request(url)
    result = json.loads(result.text).get('data')
    return result

def htb_season_list():
    url=f"https://labs.hackthebox.com/api/v4/season/list"
    result = htb_request(url)
    result = json.loads(result.text).get('data')
    return result

def htb_season_position(seasonid, uid):
    url=f"https://labs.hackthebox.com/api/v4/season/end/{seasonid}/{uid}"
    result = htb_request(url)
    result = json.loads(result.text).get('data')
    return result

#HTB Requests to API
def htb_request(url):
    headers = {"Authorization": "Bearer " + bearer, "User-Agent": "htb_python"}
    #response = requests.request("GET", url, headers=headers, proxies=proxy, verify=False)
    response = requests.request("GET", url, headers=headers)
    return response

#######Telegram Menus#######

#Menu start
menu_main = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("Active", callback_data="menu_active"),
        InlineKeyboardButton("Unreleased", callback_data="menu_unreleased")
    ],
    [
        InlineKeyboardButton("Machines", callback_data="menu_machine_difficulty"),
        InlineKeyboardButton("Fortresses", callback_data="menu_fortresses")
    ],
    [
        InlineKeyboardButton("Challenges", callback_data="menu_challenge_category"),
        InlineKeyboardButton("Users", callback_data="menu_user")
    ],
    [
        InlineKeyboardButton("Seasons", callback_data="menu_season")
    ],
    [
        InlineKeyboardButton("Notion", url="https://vpm-pentesting.notion.site/HTB-d657ca37204f4ca5afe964e9d8e4ab76?pvs=4")
    ]
])

#Menu active machine
def menu_active():
     # Ordenar los datos por fecha descendente
    sorted_data = sorted(machine_list, key=lambda x: x['release'], reverse=True)

    # Obtener la primera máquina (la de fecha más alta)
    latest_machine = sorted_data[0]

    # Obtener los detalles de la máquina
    name = latest_machine['name']
    operating_system = latest_machine['os']
    difficulty = latest_machine['difficultyText']
    id = latest_machine['id']
    users = latest_machine['user_owns_count']
    roots = latest_machine['root_owns_count']

    # Mostrar los detalles de la máquina
    result = "<b>" + str(name) + "</b>\nOS: " + str(operating_system) + "\nDifficulty: " + str(difficulty) + "\nUsers: " + str(users) + "\nRoot: " + str(roots) + check_user_complete(id, 'machine')
    return result

#menu unreleased machine
def menu_unreleased():
    result=''
    for entry in machine_unreleased:
        date = entry['release'].split('T')[0]
        date = datetime.strptime(date, "%Y-%m-%d").strftime("%d-%m-%Y")
        name = entry['name']
        operating_system = entry['os']
        difficulty = entry['difficulty_text']
        result= result +"<b>" + str(date) + "</b>\nName: " + str(name) + "\nOS: " + str(operating_system) + "\nDifficulty: <b>" + str(difficulty) + "</b>\n\n"
    return result

#Menu machine difficulty
menu_machine_difficulty = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("Easy", callback_data="menu_machines_Easy"),
        InlineKeyboardButton("Medium", callback_data="menu_machines_Medium")
    ],
    [
        InlineKeyboardButton("Hard", callback_data="menu_machines_Hard"),
        InlineKeyboardButton("Insane", callback_data="menu_machines_Insane")
    ],
    [
        InlineKeyboardButton("<< Back", callback_data="menu_main")
    ]
])

#Menu machines
def menu_machine(idifficulty):
    names = ''
    keyboard_buttons = []

    for entry in machine_list:
        name = entry['name']
        difficulty = entry['difficultyText']
        
        if difficulty == idifficulty:
            names += name + '\n'
            keyboard_buttons.append(InlineKeyboardButton(name, callback_data=f"menu_machine_info_{name}"))
    keyboard_buttons.append(InlineKeyboardButton("<< Back", callback_data="menu_machine_difficulty"))
    keyboard = InlineKeyboardMarkup([keyboard_buttons[i:i+2] for i in range(0, len(keyboard_buttons), 2)])
    return keyboard

#Menu machine info
def menu_machine_info(iname):
    # Print Release Machines
    for entry in machine_list:
        id = entry['id']
        date = entry['release'].split('T')[0]
        date = datetime.strptime(date, "%Y-%m-%d").strftime("%d-%m-%Y")
        name = entry['name']
        operating_system = entry['os']
        difficulty = entry['difficultyText']
        users = entry['user_owns_count']
        roots = entry['root_owns_count']
        if name == iname:
            results="<b>" + str(name) + "</b>\nOS: " + str(operating_system) + "\nDifficulty: " + str(difficulty) + "\nDate: " + str(date) + "\nUser Number: " + str(users) + "\nRoot Number: " + str(roots) + check_user_complete(id, 'machine')
            result = [
                results,
                str('menu_machines_'+difficulty)
            ]
            return result

#Menu challenge category
def menu_challenge_category():
    keyboard_buttons = []
    for item in challenge_category:
        name = item['name']
        id = item['id']
        keyboard_buttons.append(InlineKeyboardButton(name, callback_data=f"menu_challenge_difficulty_{id}"))

    keyboard_buttons.append(InlineKeyboardButton("<< Back", callback_data="menu_main"))
    keyboard = InlineKeyboardMarkup([keyboard_buttons[i:i+2] for i in range(0, len(keyboard_buttons), 2)])
    challenge_category_menu = keyboard
    return challenge_category_menu

#Menu challenge difficulty
def menu_challenge_difficulty(id):
    result = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("Very Easy", callback_data=f"menu_challenges_Very Easy_{id}"),
        InlineKeyboardButton("Easy", callback_data=f"menu_challenges_Easy_{id}"),
        InlineKeyboardButton("Medium", callback_data=f"menu_challenges_Medium_{id}")
    ],
    [
        InlineKeyboardButton("Hard", callback_data=f"menu_challenges_Hard_{id}"),
        InlineKeyboardButton("Insane", callback_data=f"menu_challenges_Insane_{id}")
    ],
    [
        InlineKeyboardButton("<< Back", callback_data="menu_challenge_category")
    ]
    ])
    return result

#Menu challenges
def menu_challenge(icategory, idifficulty):
    names = ''
    keyboard_buttons = []

    for entry in challenge_list:
        name = entry['name']
        difficulty = entry['difficulty']
        category = entry['challenge_category_id']
        
        if difficulty == idifficulty:
            if category == icategory:
                names += name + '\n'
                keyboard_buttons.append(InlineKeyboardButton(name, callback_data=f"menu_challenge_info_{name}"))

    keyboard_buttons.append(InlineKeyboardButton("<< Back", callback_data=f"menu_challenge_difficulty_{icategory}"))
    keyboard = InlineKeyboardMarkup([keyboard_buttons[i:i+2] for i in range(0, len(keyboard_buttons), 2)])

    return keyboard

#Menu challenge info
def menu_challenge_info(iname):
    # Print Release Challenges
    for entry in challenge_list:
        id = entry['id']
        date = entry['release_date'].split('T')[0]
        date = datetime.strptime(date, "%Y-%m-%d").strftime("%d-%m-%Y")
        name = entry['name']
        category = entry['challenge_category_id']
        difficulty = entry['difficulty']
        solves = entry['solves']
        if name == iname:
            results="<b>" + str(name) + "</b>\nCategory: " + check_challenge_category_name(category) + "\nDifficulty: " + str(difficulty) + "\nDate: " + str(date) + "\nSolves Number: " + str(solves) + check_user_complete(id, 'challenge')
            result = [
                results,
                str('menu_challenges_'+str(difficulty)+'_'+str(category))
            ]
            return result

#Menu user
def menu_user_function():
    keyboard_buttons = []
    for user_id in users_list:
        user_name = user_id['user']
        user_callback_data = user_id['id']
        keyboard_buttons.append([InlineKeyboardButton(user_name, callback_data=user_callback_data)])

    keyboard_buttons.append([InlineKeyboardButton("<< Back", callback_data="menu_main")])
    keyboard = InlineKeyboardMarkup(keyboard_buttons)
    return keyboard

#Menu user info
def menu_user_info(uid):

    # Print Release Machines
    name = profile[uid].get('name')
    rank = profile[uid].get('rank')
    points = profile[uid].get('points')
    user_owns = profile[uid].get('user_owns')
    system_owns = profile[uid].get('system_owns')
    ranking = profile[uid].get('ranking')
    challenges = profile_challenges[uid]["challenge_owns"]["solved"]
    htbpwn = profile[uid].get('rank_ownership')
    tonextrank = profile[uid].get('current_rank_progress')
    nextrank = profile[uid].get('next_rank')
    country_name = profile[uid].get('country_name')
    country_code = profile[uid].get('country_code')
    countryranking = check_country_users_top(uid, country_code)
    userdata = f"<b>{name}</b>\nID: {uid}\nRank: {rank}\nGlobal Ranking: {ranking}\n{country_name} Ranking: {countryranking}\nPoints: {points}\nUser Owns: {user_owns}\nSystem Owns: {system_owns}\nSolved Challenges: {challenges}\nHTB Pwned: {htbpwn}%\nTo {nextrank}: {tonextrank}%"
    userdata= str(userdata)
    return userdata

#Menu fortresses
def menu_fortresses():
    data = fortresses
    keyboard_buttons = []

    for fortress_id, entry in data.items():
        name = entry['name']
        callback_data = f"menu_fortresses_info_{entry['id']}"  # Incluyendo el ID en callback_data
        keyboard_buttons.append(InlineKeyboardButton(name, callback_data=callback_data))

    keyboard_buttons.append(InlineKeyboardButton("<< Back", callback_data="menu_main"))
    keyboard = InlineKeyboardMarkup([keyboard_buttons[i:i+2] for i in range(0, len(keyboard_buttons), 2)])

    return keyboard

#Menu fortresses info
def menu_fortresses_info(id):
    data = fortresses
    name = 'eRroR'
    totalflags = 'error'
    for fortress_id, entry in data.items():
        if int(entry['id']) == int(id):
            name = entry['name']
            totalflags = entry['number_of_flags']
    fortresdata = f"<b>{name}</b>\nNumber of flags: {totalflags}" + check_user_complete(id, 'fortress')
    return fortresdata

#Menu season
def menu_season():
    keyboard_buttons = []
    for entry in seasons:
        sid = entry['id']
        callback = f'menu_season_info_{sid}'
        name = entry['name']
        keyboard_buttons.append([InlineKeyboardButton(name, callback_data=callback)])
    keyboard_buttons.append([InlineKeyboardButton("<< Back", callback_data="menu_main")])
    keyboard = InlineKeyboardMarkup(keyboard_buttons)
    return keyboard

#Menu season info
def menu_season_info(sid):
    for item in seasons:
        if str(item["id"]) == str(sid):
            name = item["name"]
            break
    data = f'<b>{name}</b>\n'
    for entry_key, entry_list in season_data.items():
        if str(entry_key).startswith(str(sid)):
            if entry_list:
                tier = entry_list.get('season').get('tier')
                if tier == 'Holo':
                    tier='🔥Holo🔥'
                ranking = entry_list.get("rank").get("current")
                user = entry_list.get("user").get("name")
                total_flags = entry_list.get("owns").get("total_flags")
                user_flags = entry_list.get("owns").get("user").get("flags_pawned")
                root_flags = entry_list.get("owns").get("root").get("flags_pawned")
                total_flags=total_flags*2
                pawned_flags=root_flags+user_flags
                userdata=f'{ranking} - {user} - {tier} - {pawned_flags}/{total_flags} Flags\n'
                data += userdata
    return data






#######Other functions#######

#Cache HTB data
def cache():
    def get_challenge_category():
        global challenge_category
        challenge_category = htb_challenge_categories_list()

    def get_challenge_list():
        global challenge_list
        challenge_list = htb_challenge_list()

    def get_machine_list():
        global machine_list
        machine_list = htb_machine_list()

    def get_machine_unreleased():
        global machine_unreleased
        machine_unreleased = htb_machine_unreleased()

    def get_fortresses():
        global fortresses
        fortresses = htb_fortresses()

    def get_seasons():
        global seasons, season_data
        seasons = htb_season_list()
        season_data = {}
        for season in seasons:
            sid = season['id']
            for uid in users_ids:
                seasonfinalid = f"{sid}{uid}"
                season_data[seasonfinalid] = htb_season_position(sid, uid)

    def get_profiles():
        global profile, profile_activity, profile_challenges, users_list, menu_user, country_users_top
        users_list = []
        profile_challenges
        for uid in users_ids:
            profile[uid] = htb_profile(uid)
            profile_activity[uid] = htb_profile_activity(uid)
            profile_challenges[uid] = htb_profile_challenges(uid)
            country_code = profile[uid].get('country_code')
            if country_code not in  profile_challenges.keys():
                country_users_top[country_code] = htb_country_users_top(country_code)
            new_user = {'user': str(profile[uid].get('name')), 'id': uid}
            users_list.append(new_user)
            menu_user=menu_user_function()

    threads = [
        threading.Thread(target=get_challenge_category),
        threading.Thread(target=get_challenge_list),
        threading.Thread(target=get_machine_list),
        threading.Thread(target=get_machine_unreleased),
        threading.Thread(target=get_profiles),
        threading.Thread(target=get_fortresses),
        threading.Thread(target=get_seasons)
    ]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    global cache_date
    cache_date = datetime.now()

#Back button
def back_button(action):
    menu = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("<< Back", callback_data=action)
        ]
    ])
    return menu

#Check if users have completed machine or challenge
def check_user_complete(id, type):
    result = ''
    for user_id in users_list:
        username = user_id['user']
        profile = profile_activity[user_id['id']]
        activity = profile.get("activity", [])
        user = False
        root = False
        pwn = False
        fortress_flags = 0
        for item in activity:
            if int(item.get("id")) == int(id) and item.get("object_type") == type:
                if type == 'machine':
                    if item.get('type') == 'user':
                        user = True
                    elif item.get('type') == 'root':
                        root = True
                elif type == 'challenge':
                    pwn = True
                elif type == 'fortress':
                    fortress_flags += 1
        if root:
            status='<b>🔥Rooted🔥</b>'
        elif user:
            status='Usered'
        elif pwn:
            status='<b>🔥Pwned🔥</b>'
        elif type == 'fortress':
            status=f'{str(fortress_flags)} Flags'
        else:
            status='Pending'

        result = result + ' \n' + username + ' Status: ' + status
    return result

#Check challenge category name by id
def check_challenge_category_name(id_to_search):
    for item in challenge_category:
        if item['id'] == id_to_search:
            return item['name']

def check_country_users_top(id_to_search, country_code):
    for item in country_users_top[country_code]:
            if str(item["id"]) == str(id_to_search):
                countryrank = str(item["rank"])
                return countryrank
            
#Edit message of telegram bot
def edit_message(context, chat_id, message_id, text, keyboard):
    context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, reply_markup=keyboard, parse_mode='HTML')

#######Telegram actions#######

#Command /htb
def start(update, context):
    if update.message.chat_id in allowed_list:
        response = "Choose action:"
        context.bot.send_message(update.message.chat_id,response, reply_markup=menu_main)
        cache()
    else:
        response = 'You are not authorized'
        update.message.reply_text(response,parse_mode='HTML', disable_web_page_preview=True)

#Command /help
def help(update, context):
    if update.message.chat_id in allowed_list:
        if update.message.chat_id in admin_list:
            response = 'Make /htb to use the bot\nMake /cachedate to view the date of cache\nMake /adduser to add a user\nMake /purgeuser to purge user'
        else:
            response = 'Make /htb to use the bot'
        update.message.reply_text(response,parse_mode='HTML', disable_web_page_preview=True)	
    else:
        response = 'You are not authorized'
        update.message.reply_text(response,parse_mode='HTML', disable_web_page_preview=True)

#Command /cachedate
def cachedate(update, context):
    if update.message.chat_id in admin_list:
        update.message.reply_text(str(cache_date),parse_mode='HTML', disable_web_page_preview=True)
    else:
        response = 'You are not authorized'
        update.message.reply_text(response,parse_mode='HTML', disable_web_page_preview=True)

# Command /adduser
def add_user(update, context):
    if update.message.chat_id in admin_list:
        args = context.args
        if len(args) == 1:
            global users_ids
            new_user = args[0]
            users_ids.append(new_user)
            response = f"User with ID '{args[0]}' has been added."
            cache()
        else:
            response = "Usage: /adduser id"
        update.message.reply_text(response, parse_mode='HTML', disable_web_page_preview=True)
    else:
        response = 'You are not authorized'
        update.message.reply_text(response, parse_mode='HTML', disable_web_page_preview=True)

#Command /purgeuser
def purge_user(update, context):
    global users_ids, menu_user
    if update.message.chat_id in admin_list:
        args = context.args
        if len(args) == 1:
            id_to_remove = args[0]
            if id_to_remove in users_ids:
                users_ids.remove(id_to_remove)
                cache()
                response = f"User with ID '{id_to_remove}' has been purged."
            else:
                response = "User id dont exist."
        else:
            response = "Usage: /purgeuser id"
        update.message.reply_text(response, parse_mode='HTML', disable_web_page_preview=True)
    else:
        response = 'You are not authorized'
        update.message.reply_text(response, parse_mode='HTML', disable_web_page_preview=True)

#Command Buttons
def handle_callback(update, context):
    #Query
    query = update.callback_query
    data=query.data
    chat_id = query.message.chat_id
    message_id = query.message.message_id

    #If allowed
    if query.message.chat_id in allowed_list:

        #Command executed
        print(data)

        #Check cachedate > 1 hour to cache data
        if datetime.now() - cache_date > timedelta(hours=1):
            cache()

        #Actions to do
        
        match data:
            #menu_main
            case "menu_main":
                text = "Choose action:"
                keyboard=menu_main

            #menu_active
            case "menu_active":
                text = menu_active()
                keyboard=back_button('menu_main')

            #menu_unreleased
            case "menu_unreleased":
                text = menu_unreleased()
                keyboard=back_button('menu_main')
  
            #menu_machine_difficulty
            case "menu_machine_difficulty":
                text = "Choose machine dificulty:"
                keyboard=menu_machine_difficulty

            #menu_machines
            case data if data.startswith('menu_machines_'):
                selected_difficulty = data[len('menu_machines_'):]
                text = "Choose the machine:"
                keyboard=menu_machine(selected_difficulty)

            #menu_machine_info
            case data if data.startswith('menu_machine_info_'):
                machine_name=data[len('menu_machine_info_'):]
                result=menu_machine_info(machine_name)
                text = result[0]
                keyboard=back_button(result[1])

            #menu_challenge_category
            case "menu_challenge_category":
                text = "Choose challenge category:"
                keyboard=menu_challenge_category()

            #menu_challenge_difficulty
            case data if data.startswith('menu_challenge_difficulty_'):
                id = data[len('menu_challenge_difficulty_'):]
                text = "Choose the difficulty of challenge:"
                keyboard=menu_challenge_difficulty(id)

            #menu_challenges
            case data if data.startswith('menu_challenges_'):
                parts = data.split('_')
                selected_difficulty = parts[2]
                selected_category = int(parts[3])
                text = "Choose the challenge:"
                keyboard = menu_challenge(selected_category, selected_difficulty)
            
            #menu_challenge_info
            case data if data.startswith('menu_challenge_info_'):
                challenge=data[len('menu_challenge_info_'):]
                result=menu_challenge_info(challenge)
                text = result[0]
                keyboard = back_button(result[1])

            #menu_user
            case 'menu_user':
                text = "Choose the user:"
                keyboard=menu_user

            #menu_user_info
            case data if any(user['id'] == data for user in users_list):
                text = menu_user_info(data)
                keyboard=back_button('menu_user')
            
            #menu_fortresses
            case 'menu_fortresses':
                text = "Choose the fortress:"
                keyboard=menu_fortresses()

            #menu_fortresses_info
            case data if data.startswith('menu_fortresses_info_'):
                fortres=data[len('menu_fortresses_info_'):]
                text=menu_fortresses_info(fortres)
                keyboard = back_button('menu_fortresses')
            
            #menu_season
            case 'menu_season':
                text = "Choose the season:"
                keyboard=menu_season()
                            
            #menu_season
            case data if data.startswith('menu_season_info_'):
                sid=data[len('menu_season_info_'):]
                text=menu_season_info(sid)
                keyboard = back_button('menu_season')

            case _:
                text='Unexpected error'
                keyboard = back_button('menu_main')
        
        edit_message(context, chat_id, message_id, text, keyboard)
    else:
        response = 'You are not authorized'
        query.message.reply_text(response,parse_mode='HTML', disable_web_page_preview=True)

#######Start bot#######
def main():
	updater=Updater(TOKEN, use_context=True)
	dp=updater.dispatcher

	# Events that will trigger our bot.
	dp.add_handler(CommandHandler('help',	help))
	dp.add_handler(CommandHandler('htb',	start))
	dp.add_handler(CommandHandler('adduser', add_user))
	dp.add_handler(CommandHandler('purgeuser', purge_user))
	dp.add_handler(CommandHandler('cachedate',	cachedate))
	dp.add_handler(CallbackQueryHandler(handle_callback))
	# Start bot
	updater.start_polling()
	# Listening
	updater.idle()

if __name__ == '__main__':
	main()
