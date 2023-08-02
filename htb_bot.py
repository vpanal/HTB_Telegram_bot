# -<b>- coding: utf-8 -<b>-
from telegram.ext import (Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters)
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, Bot
import requests
import json
from datetime import datetime

#-------Modifica esto para que funcione-------#
#URL Documentacion
#https://documentation.example
#IDs de chat de telegram permitidas
allowed_list=(idchat, idchat) 
#Token de bot de telegram
TOKEN='Token de bot de telegram'
#Bearer Token de HTB
bearer='Bearer Token de HTB'
#Usernames y ID de usuarios de HTB
users_ids = [{'user': 'username', 'id': 'idnumer'}, {'user': 'username', 'id': 'idnumer'}]

###############################################

headers = {"Authorization": "Bearer " + bearer, "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:102.0) Gecko/20100101 Firefox/102.0", "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8", "Accept-Language": "en-US,en;q=0.5", "Accept-Encoding": "gzip, deflate", "Upgrade-Insecure-Requests": "1", "Sec-Fetch-Dest": "document", "Sec-Fetch-Mode": "navigate", "Sec-Fetch-Site": "none", "Sec-Fetch-User": "?1", "Te": "trailers", "Connection": "close"}
#All
def handle_message(update, context):
	if update.message.chat_id in allowed_list:
		comando =str(update.message.text).split(" ")
		comando = comando[0]
		match comando:
			case _:
				if comando[0]=='/':
					result = '<b>Unknown command, you can find my guide at:</b>\n/help'
					update.message.reply_text(result,parse_mode='HTML', disable_web_page_preview=True)
	else:
		response = 'You are not authorized'
		update.message.reply_text(response,parse_mode='HTML', disable_web_page_preview=True)	

def profile(uid):
    url = "https://www.hackthebox.com/api/v4/user/profile/basic/"+uid
    payload = {}
    global headers
    response = requests.request("GET", url, headers=headers, data=payload)
    #Charge json
    profile = json.loads(response.text).get('profile')
    # Print Release Machines
    name = profile.get('name')
    rank = profile.get('rank')
    points = profile.get('points')
    user_owns = profile.get('user_owns')
    system_owns = profile.get('system_owns')
    userdata = "<b>" + str(name) + "</b>\nRank: " + str(rank) + "\nPoints: " + str(points) + "\nUser Owns: " + str(user_owns) + "\nSystem Owns: " + str(system_owns)
    userdata= str(userdata)
    return userdata

def check_id(mid):
    global users_ids
    result = ''
    for user_id in users_ids:
        username, uid = user_id['user'], user_id['id']
        url = 'https://www.hackthebox.com/api/v4/profile/activity/' + str(uid)
        payload = {}
        global headers
        response = requests.request("GET", url, headers=headers, data=payload)
        data = json.loads(response.text)
        profile = data.get("profile", {})
        activity = profile.get("activity", [])
        user = 'No'
        root = 'No'
        for item in activity:
            if item.get("id") == mid:
                if item.get('type') == 'user':
                    user = 'Yes'
                elif item.get('type') == 'root':
                    root = 'Yes'
        result = result + ' \n' + username + ' Usered: ' + user + ' \n' + username + ' Rooted: ' + root
    return result

#Main menu
def start(update, context):
	if update.message.chat_id in allowed_list:
		response = "Choose action:"
		keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("Active", callback_data="Active"),
                InlineKeyboardButton("Unreleased", callback_data="Unreleased")
            ],
            [
                InlineKeyboardButton("Release", callback_data="Release"),
                InlineKeyboardButton("Documentation", url="https://documentation.example")
            ],
            [
                InlineKeyboardButton("Users", callback_data="umenu")
            ]
		])
		context.bot.send_message(update.message.chat_id,response, reply_markup=keyboard)
	else:
		response = 'You are not authorized'
		update.message.reply_text(response,parse_mode='HTML', disable_web_page_preview=True)

#Options of menu
def handle_callback(update, context):

    #Query
    query = update.callback_query
    data=query.data
    chat_id = query.message.chat_id
    message_id = query.message.message_id

    #If allowed
    if query.message.chat_id in allowed_list:

        #Request
        if(data=='Unreleased'):
            url = 'https://www.hackthebox.com/api/v4/machine/unreleased'
        else:
            url = "https://www.hackthebox.com/api/v4/machine/list"
        payload = {}
        global headers
        response = requests.request("GET", url, headers=headers, data=payload)
		
		#Charge json
        json_data = json.loads(response.text)
		
        #Buton main                
        keyboardmain = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("<< Back", callback_data='start')
            ]
        ])
        
        if(data in ('Easy', 'Medium', 'Hard', 'Insane')):
            data='diff'
        else:
            for user_id in users_ids:
                if user_id['id'] == data:
                    uid=data
                    data='user'
        match data:
            #Main menu
            case "start":
                response = "Choose action:"
                keyboard = InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("Active", callback_data="Active"),
                        InlineKeyboardButton("Unreleased", callback_data="Unreleased")
                    ],
                    [
                        InlineKeyboardButton("Release", callback_data="Release"),
                        InlineKeyboardButton("Documentation", url="https://https://documentation.example")
                    ],
                    [
                        InlineKeyboardButton("Users", callback_data="umenu")
                    ]
                ])
                context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=response, reply_markup=keyboard, parse_mode='HTML')
            
            #Machines menu
            case "diff":
                selected_difficulty = query.data
                keyboard=secondarymenu(selected_difficulty, json_data)
                response = "Choose the machine:"
                context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=response, reply_markup=keyboard, parse_mode='HTML')
            
            #Active machine
            case "Active":
                # Ordenar los datos por fecha descendente
                sorted_data = sorted(json_data['info'], key=lambda x: x['release'], reverse=True)

                # Obtener la primera máquina (la de fecha más alta)
                latest_machine = sorted_data[0]

                # Obtener los detalles de la máquina
                name = latest_machine['name']
                operating_system = latest_machine['os']
                difficulty = latest_machine['difficultyText']
                ip = latest_machine['ip']
                id = latest_machine['id']
                users = latest_machine['user_owns_count']
                roots = latest_machine['root_owns_count']

                # Mostrar los detalles de la máquina
                result = "<b>" + str(name) + "</b>\nOS: " + str(operating_system) + "\nDifficulty: " + str(difficulty) + "\nIP: " + str(ip) + "\nUsers: " + str(users) + "\nRoot: " + str(roots) + check_id(id)
                chat_id = query.message.chat_id
                message_id = query.message.message_id
                context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=result, reply_markup=keyboardmain, parse_mode='HTML')

            #Unreleased machines
            case "Unreleased":
                # Print Unreleased Machines
                result=''
                for entry in json_data['data']:
                    date = entry['release'].split('T')[0]
                    date = datetime.strptime(date, "%Y-%m-%d").strftime("%d-%m-%Y")
                    name = entry['name']
                    operating_system = entry['os']
                    difficulty = entry['difficulty_text']
                    result= result +"<b>" + str(date) + "</b>\nName: " + str(name) + "\nOS: " + str(operating_system) + "\nDifficulty: <b>" + str(difficulty) + "</b>\n\n"
                context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=result, reply_markup=keyboardmain, parse_mode='HTML')

            #Difficulty menu
            case "Release":
                response = "Choose the difficulty:"
                keyboard = InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("Easy", callback_data="Easy"),
                        InlineKeyboardButton("Medium", callback_data="Medium")
                    ],
                    [
                        InlineKeyboardButton("Hard", callback_data="Hard"),
                        InlineKeyboardButton("Insane", callback_data="Insane")
                    ],
                    [
                        InlineKeyboardButton("<< Back", callback_data="start")
                    ]
                ])
                context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=response, reply_markup=keyboard, parse_mode='HTML')

            case 'user':
                response=profile(uid)
                keyboard = InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("<< Back", callback_data="umenu")
                    ]
                ])
                context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=response, reply_markup=keyboard, parse_mode='HTML')

            case 'umenu':
                response = "Choose the user:"
                keyboard_buttons = []
                for user_id in users_ids:
                    user_name = user_id['user']
                    user_callback_data = user_id['id']
                    keyboard_buttons.append([InlineKeyboardButton(user_name, callback_data=user_callback_data)])

                keyboard_buttons.append([InlineKeyboardButton("<< Back", callback_data="start")])
                keyboard = InlineKeyboardMarkup(keyboard_buttons)

                context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=response, reply_markup=keyboard, parse_mode='HTML')

            case _:
                result=show(query.data, json_data)
                text = result[0]
                keyboard = InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("<< Back", callback_data=result[1])
                    ]
                ])
                chat_id = query.message.chat_id
                message_id = query.message.message_id
                context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, reply_markup=keyboard, parse_mode='HTML')
    else:
        response = 'You are not authorized'
        chat_id = query.message.chat_id
        message_id = query.message.message_id
        query.message.reply_text(response,parse_mode='HTML', disable_web_page_preview=True)


#Show machine info
def show(iname,json_data):
    # Print Release Machines
    for entry in json_data['info']:
        id = entry['id']
        date = entry['release'].split('T')[0]
        date = datetime.strptime(date, "%Y-%m-%d").strftime("%d-%m-%Y")
        name = entry['name']
        operating_system = entry['os']
        difficulty = entry['difficultyText']
        ip = entry['ip']
        users = entry['user_owns_count']
        roots = entry['root_owns_count']
        if name == iname:
            results="<b>" + str(name) + "</b>\nOS: " + str(operating_system) + "\nDifficulty: " + str(difficulty) + "\nIP: " + str(ip) + "\nDate: " + str(date) + "\nUser Number: " + str(users) + "\nRoot Number: " + str(roots) + check_id(id)
            result = [
                results,
                str(difficulty)
            ]
            return result

#Machines menu
def secondarymenu(idifficulty, json_data):
    names = ''
    keyboard_buttons = []

    for entry in json_data['info']:
        name = entry['name']
        difficulty = entry['difficultyText']
        
        if difficulty == idifficulty:
            names += name + '\n'
            keyboard_buttons.append(InlineKeyboardButton(name, callback_data=name))

    keyboard_buttons.append(InlineKeyboardButton("<< Back", callback_data="Release"))
    keyboard = InlineKeyboardMarkup([keyboard_buttons[i:i+2] for i in range(0, len(keyboard_buttons), 2)])

    return keyboard

#Help
def help(update, context):
	response = 'Make /start to start bot'
	update.message.reply_text(response,parse_mode='HTML', disable_web_page_preview=True)	


def main():
	updater=Updater(TOKEN, use_context=True)
	dp=updater.dispatcher

	# Events that will trigger our bot.
	dp.add_handler(CommandHandler('help',	help))
	dp.add_handler(CommandHandler('start',	start))
	dp.add_handler(CallbackQueryHandler(handle_callback))
	dp.add_handler(MessageHandler(Filters.text,	handle_message))
	# Start bot
	updater.start_polling()
	# Listening
	updater.idle()

if __name__ == '__main__':
	main()
