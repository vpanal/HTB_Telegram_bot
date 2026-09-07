# -*- coding: utf-8 -*-
import asyncio
import html
import logging
import os
import threading
import warnings
from datetime import datetime, timedelta
from urllib.parse import quote

import requests
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

# Cargar variables de entorno desde el archivo .env (ver .env.example)
load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger("htb_bot")


def _parse_id_list(value):
    """Convierte 'id1,id2,id3' en una tupla de enteros."""
    if not value:
        return ()
    return tuple(int(item.strip()) for item in value.split(',') if item.strip())


def _parse_str_list(value):
    """Convierte 'a,b,c' en una lista de strings."""
    if not value:
        return []
    return [item.strip() for item in value.split(',') if item.strip()]


def _parse_int(value, default):
    """Convierte a entero con un valor por defecto si el dato no es válido."""
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


#IDs de chat de telegram permitidas
allowed_list = _parse_id_list(os.getenv("ALLOWED_CHAT_IDS"))
#IDs de chat de telegram con permisos de administrador
admin_list = _parse_id_list(os.getenv("ADMIN_CHAT_IDS"))
#Token de bot de telegram
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
#Usernames y ID de usuarios de HTB
users_ids = _parse_str_list(os.getenv("HTB_USER_IDS"))
#Bearer Token de HTB
bearer = os.getenv("HTB_BEARER_TOKEN")
#Enlace Wiki
enlace_wiki = os.getenv("WIKI_URL")
#Minutos de validez de la cache antes de volver a consultar la API de HTB
cache_ttl_minutes = _parse_int(os.getenv("CACHE_TTL_MINUTES"), 60)
#Configuracion del proxy
proxyenabled = os.getenv("PROXY_ENABLED", "false").strip().lower() == "true"
proxy = {
    "https": os.getenv("PROXY_URL", "http://127.0.0.1:8080")
}

_missing_config = [
    name
    for name, value in (
        ("TELEGRAM_BOT_TOKEN", TOKEN),
        ("HTB_BEARER_TOKEN", bearer),
    )
    if not value
]
if _missing_config:
    raise SystemExit(
        "Faltan variables obligatorias en el .env: "
        + ", ".join(_missing_config)
        + ". Copia .env.example a .env y completa los valores necesarios."
    )

if not allowed_list:
    logger.warning(
        "ALLOWED_CHAT_IDS está vacío: el bot rechazará a todos los chats hasta que lo configures."
    )

#######Endpoints de la API de HTB#######
# Documentacion (no oficial): https://labs.hackthebox.com/api/v4 y /api/v5
HTB_HOST = "https://labs.hackthebox.com"
HTB_API_V4 = f"{HTB_HOST}/api/v4"
HTB_API_V5 = f"{HTB_HOST}/api/v5"
HTB_API_XP = f"{HTB_HOST}/api/experience/v1"

# Mapeo de tiers de Starting Point (spTier -> nombre mostrado)
SP_TIERS = {1: "Tier 0 - Foundations", 2: "Tier 1 - Fundamental Exploitation", 3: "Tier 2 - Multi-Step Attacks"}

# Numero maximo de botones que generamos en un menu para no exceder los limites de Telegram
MAX_MENU_BUTTONS = 40
# Numero de posiciones que mostramos en los rankings
RANKING_ROWS = 15


def esc(value):
    """Escapa texto de origen externo antes de incrustarlo en mensajes parse_mode='HTML'."""
    if value is None:
        return ''
    return html.escape(str(value), quote=False)


def format_date(value, default='?'):
    """Convierte una fecha ISO de la API ('2024-05-01T00:00:00Z') a 'dd-mm-YYYY'.

    La API es no oficial y puede devolver null o formatos inesperados, así que
    nunca lanza: devuelve `default` si no puede interpretar el valor.
    """
    if not value:
        return default
    raw = str(value).split('T')[0]
    try:
        return datetime.strptime(raw, "%Y-%m-%d").strftime("%d-%m-%Y")
    except ValueError:
        return raw or default


# Inicialización de variables de entorno
challenge_category = []
challenge_list = []
machine_list = []
machine_unreleased = []
fortresses = []
seasons = []
sherlock_category = []
sherlock_list = []
prolabs = []
sp_tiers = []
rankings = {}
profile = {}
profile_activity = {}
profile_challenges = {}
country_users_top = {}
users_list = []
menu_user = ''
season_data = {}
season_machines_number = {}
cache_date=datetime(2023, 8, 1, 10, 30)
menu_season_items_per_page = 3

# Proxy disable warnings
if proxyenabled ==True:
    warnings.filterwarnings("ignore", message="Unverified HTTPS request")

#######HTB API#######

#HTB Requests to API
def htb_request(url):
    """Lanza un GET contra la API de HTB. Devuelve la Response o None si la llamada falla."""
    headers = {"Authorization": "Bearer " + bearer, "User-Agent": "htb_python"}
    try:
        if proxyenabled:
            response = requests.request("GET", url, headers=headers, proxies=proxy, verify=False, timeout=30)
        else:
            response = requests.request("GET", url, headers=headers, timeout=30)
        response.raise_for_status()
        return response
    except requests.exceptions.RequestException as error:
        logger.warning("Fallo consultando %s: %s", url, error)
        return None

#GET + parseo de JSON tolerante a fallos
def htb_json(url, default=None):
    """Devuelve el JSON del endpoint, o `default` si la llamada o el parseo fallan."""
    response = htb_request(url)
    if response is None:
        return default
    try:
        return response.json()
    except ValueError:
        logger.warning("La respuesta de %s no es JSON válido", url)
        return default

#Desenvolver respuestas de HTB
def htb_unwrap(payload, *keys):
    """La API envuelve los datos en 'data', 'info', 'profile'... según el endpoint.

    Devuelve el primer contenedor encontrado, o None si ninguno está presente.
    """
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        return None
    for key in keys:
        if key in payload:
            return payload[key]
    return None

#HTB Profile basic info
def htb_profile(uid):
    url = f"{HTB_API_V4}/user/profile/basic/{uid}"
    return htb_unwrap(htb_json(url, {}), 'profile') or {}

#HTB Profile challenges info
def htb_profile_challenges(uid):
    url = f"{HTB_API_V4}/user/profile/progress/challenges/{uid}"
    return htb_unwrap(htb_json(url, {}), 'profile') or {}

#HTB Profile progress by area (machines, challenges, sherlocks, prolab, fortress)
def htb_profile_progress(uid, area):
    url = f"{HTB_API_V4}/user/profile/progress/{area}/{uid}"
    return htb_unwrap(htb_json(url, {}), 'profile', 'data') or {}

#HTB Profile badges
def htb_profile_badges(uid):
    url = f"{HTB_API_V4}/user/profile/badges/{uid}"
    return htb_unwrap(htb_json(url, {}), 'badges', 'data', 'info') or []

#HTB Profile Activity info (with pagination support)
def htb_profile_activity(uid):
    all_activities = []
    page = 1

    while True:
        url = f"{HTB_API_V5}/user/profile/activity/{uid}?page={page}&per_page=100"
        data = htb_json(url)
        if not isinstance(data, dict):
            # Si la llamada falla devolvemos lo acumulado hasta ahora
            break

        activities = data.get('data', [])
        if not activities:
            break
        all_activities.extend(activities)

        # Comprobar si hemos llegado a la ultima pagina
        meta = data.get('meta', {})
        if 'lastPage' in meta:
            if page >= meta['lastPage']:
                break
        elif 'totalItems' in meta:
            items_per_page = len(activities)
            if items_per_page > 0:
                total_pages = (meta['totalItems'] + items_per_page - 1) // items_per_page
                if page >= total_pages:
                    break
        page += 1
        if page > 20:  # Limite de seguridad para evitar bucles infinitos
            break

    return all_activities

#HTB Experience (XP, nivel y racha). Usa account_id (UUID), no el id numerico
def htb_experience(account_id):
    if not account_id:
        return {}
    url = f"{HTB_API_XP}/account/{account_id}"
    payload = htb_json(url, {})
    return payload if isinstance(payload, dict) else {}

#HTB Country TOP
def htb_country_users_top(country_code):
    if not country_code:
        return []
    url = f"{HTB_API_V4}/rankings/country/{country_code}/members"
    data = htb_unwrap(htb_json(url, {}), 'data') or {}
    if isinstance(data, dict):
        return data.get('rankings', [])
    return data or []

#HTB Rankings / Hall of Fame (scope: users, teams, countries, universities)
def htb_rankings(scope):
    url = f"{HTB_API_V4}/rankings/{scope}"
    data = htb_unwrap(htb_json(url, {}), 'data') or []
    if isinstance(data, dict):
        return data.get('rankings', []) or data.get(scope, []) or []
    return data

#HTB Unreleased Machines info
def htb_machine_unreleased():
    url = f"{HTB_API_V5}/machines?state=unreleased"
    return htb_unwrap(htb_json(url, {}), 'data') or []

#HTB Active Machines info
def htb_machine_list():
    url = f"{HTB_API_V4}/machine/paginated?per_page=100"
    return htb_unwrap(htb_json(url, {}), 'data') or []

#HTB Starting Point tiers progress
def htb_sp_tiers_progress():
    url = f"{HTB_API_V4}/sp/tiers/progress"
    return htb_unwrap(htb_json(url, {}), 'data', 'info') or []

#HTB Starting Point machines of a tier
def htb_sp_machines(tier):
    url = f"{HTB_API_V5}/machines?spTier={tier}&per_page=100"
    return htb_unwrap(htb_json(url, {}), 'data') or []

#HTB Active Challenges info
def htb_challenge_list():
    url = f"{HTB_API_V4}/challenge/list"
    return htb_unwrap(htb_json(url, {}), 'challenges', 'data') or []

#HTB Challenge Categories
def htb_challenge_categories_list():
    url = f"{HTB_API_V4}/challenge/categories/list"
    return htb_unwrap(htb_json(url, {}), 'info', 'data') or []

#HTB Sherlocks list
def htb_sherlock_list():
    url = f"{HTB_API_V4}/sherlocks?per_page=100"
    return htb_unwrap(htb_json(url, {}), 'data') or []

#HTB Sherlocks categories
def htb_sherlock_categories_list():
    url = f"{HTB_API_V4}/sherlocks/categories/list"
    return htb_unwrap(htb_json(url, {}), 'info', 'data') or []

#HTB Sherlock detail (admite nombre o id)
def htb_sherlock_info(sherlock_id):
    url = f"{HTB_API_V4}/sherlocks/{sherlock_id}"
    return htb_unwrap(htb_json(url, {}), 'data', 'info') or {}

#HTB Pro Labs list
def htb_prolabs():
    data = htb_unwrap(htb_json(f"{HTB_API_V4}/prolabs", {}), 'data') or {}
    if isinstance(data, dict):
        return data.get('labs', []) or []
    return data or []

#HTB Pro Lab overview
def htb_prolab_overview(prolab_id):
    url = f"{HTB_API_V4}/prolab/{prolab_id}/overview"
    return htb_unwrap(htb_json(url, {}), 'data', 'info') or {}

#HTB Fortresses
def htb_fortresses():
    url = f"{HTB_API_V4}/fortresses"
    data = htb_unwrap(htb_json(url, {}), 'data') or []
    if isinstance(data, dict):
        # El endpoint devuelve un diccionario indexado por id
        return list(data.values())
    return data

#HTB Seasons list
def htb_season_list():
    url = f"{HTB_API_V4}/season/list"
    return htb_unwrap(htb_json(url, {}), 'data') or []

#HTB Season position of a user
def htb_season_position(seasonid, uid):
    url = f"{HTB_API_V4}/season/end/{seasonid}/{uid}"
    return htb_unwrap(htb_json(url, {}), 'data')

#HTB Season ranks of a user (todas las temporadas jugadas)
def htb_season_user_ranks(uid):
    url = f"{HTB_API_V4}/season/user/{uid}/ranks"
    return htb_unwrap(htb_json(url, {}), 'data') or []

#HTB Number of flags of a season (2 flags por maquina)
def htb_season_machines_number(seasonid):
    url = f"{HTB_API_V4}/season/machines/{seasonid}"
    data = htb_unwrap(htb_json(url, {}), 'data') or []
    return len(data) * 2

#HTB Search (usuarios y equipos)
def htb_search(query):
    url = f"{HTB_API_V4}/search/fetch?query={quote(query)}"
    payload = htb_json(url, {})
    return payload if isinstance(payload, dict) else {}

#######Telegram Menus#######

#Menu start
menu_main_buttons = [
    [
        InlineKeyboardButton("Active", callback_data="menu_active"),
        InlineKeyboardButton("Unreleased", callback_data="menu_unreleased")
    ],
    [
        InlineKeyboardButton("Machines", callback_data="menu_machine_difficulty"),
        InlineKeyboardButton("Challenges", callback_data="menu_challenge_category")
    ],
    [
        InlineKeyboardButton("Sherlocks", callback_data="menu_sherlock_category"),
        InlineKeyboardButton("Fortresses", callback_data="menu_fortresses")
    ],
    [
        InlineKeyboardButton("Pro Labs", callback_data="menu_prolabs"),
        InlineKeyboardButton("Starting Point", callback_data="menu_starting_point")
    ],
    [
        InlineKeyboardButton("Users", callback_data="menu_user"),
        InlineKeyboardButton("Seasons", callback_data="menu_season")
    ],
    [
        InlineKeyboardButton("Rankings", callback_data="menu_rankings")
    ]
]

# El boton de la wiki solo aparece si WIKI_URL esta configurado en el .env
if enlace_wiki:
    menu_main_buttons.append([InlineKeyboardButton("Notion", url=enlace_wiki)])

menu_main = InlineKeyboardMarkup(menu_main_buttons)

#Menu active machine
def menu_active():
    if not machine_list:
        return 'No hay datos de máquinas. Prueba a refrescar con /refresh.'

     # Ordenar los datos por fecha descendente
    sorted_data = sorted(machine_list, key=lambda x: x.get('release') or '', reverse=True)

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
    result = "<b>" + esc(name) + "</b>\nOS: " + esc(operating_system) + "\nDifficulty: " + esc(difficulty) + "\nUsers: " + esc(users) + "\nRoot: " + esc(roots) + check_user_complete(id, 'machine')
    return result

#menu unreleased machine
def menu_unreleased():
    if not machine_unreleased:
        return 'No hay máquinas sin publicar disponibles.'

    result=''
    for entry in machine_unreleased:
        date = format_date(entry.get('releaseDate'))
        name = entry['name']
        operating_system = entry['os']
        difficulty = entry['difficultyText']
        result= result +"<b>" + esc(date) + "</b>\nName: " + esc(name) + "\nOS: " + esc(operating_system) + "\nDifficulty: <b>" + esc(difficulty) + "</b>\n\n"
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
        date = format_date(entry.get('release'))
        name = entry['name']
        operating_system = entry['os']
        difficulty = entry['difficultyText']
        users = entry['user_owns_count']
        roots = entry['root_owns_count']
        if name == iname:
            results="<b>" + esc(name) + "</b>\nOS: " + esc(operating_system) + "\nDifficulty: " + esc(difficulty) + "\nDate: " + esc(date) + "\nUser Number: " + esc(users) + "\nRoot Number: " + esc(roots) + check_user_complete(id, 'machine')
            result = [
                results,
                str('menu_machines_'+difficulty)
            ]
            return result
    return ['No se ha encontrado esta máquina.', 'menu_machine_difficulty']

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
        date = format_date(entry.get('release_date'))
        name = entry['name']
        category = entry['challenge_category_id']
        difficulty = entry['difficulty']
        solves = entry['solves']
        if name == iname:
            results="<b>" + esc(name) + "</b>\nCategory: " + esc(check_challenge_category_name(category)) + "\nDifficulty: " + esc(difficulty) + "\nDate: " + esc(date) + "\nSolves Number: " + esc(solves) + check_user_complete(id, 'challenge')
            result = [
                results,
                str('menu_challenges_'+str(difficulty)+'_'+str(category))
            ]
            return result
    return ['No se ha encontrado este challenge.', 'menu_challenge_category']

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
    user_profile = profile.get(uid) or {}
    if not user_profile:
        return 'No hay datos de este usuario. Prueba a refrescar con /htb.'

    name = user_profile.get('name')
    rank = user_profile.get('rank')
    points = user_profile.get('points')
    user_owns = user_profile.get('user_owns')
    system_owns = user_profile.get('system_owns')
    ranking = user_profile.get('ranking')
    challenges = (profile_challenges.get(uid) or {}).get("challenge_owns", {}).get("solved", 0)
    htbpwn = user_profile.get('rank_ownership')
    tonextrank = user_profile.get('current_rank_progress')
    nextrank = user_profile.get('next_rank')
    country_name = user_profile.get('country_name')
    country_code = user_profile.get('country_code')
    countryranking = check_country_users_top(uid, country_code)
    team = (user_profile.get('team') or {}).get('name')
    respects = user_profile.get('respects')

    userdata = (
        f"<b>{esc(name)}</b>\nID: {esc(uid)}\nRank: {esc(rank)}\nGlobal Ranking: {esc(ranking)}\n"
        f"{esc(country_name)} Ranking: {esc(countryranking)}\nPoints: {esc(points)}\n"
        f"User Owns: {esc(user_owns)}\nSystem Owns: {esc(system_owns)}\n"
        f"Solved Challenges: {esc(challenges)}\nHTB Pwned: {esc(htbpwn)}%\n"
        f"To {esc(nextrank)}: {esc(tonextrank)}%"
    )
    if team:
        userdata += f"\nTeam: {esc(team)}"
    if respects is not None:
        userdata += f"\nRespects: {esc(respects)}"
    return userdata

#Menu fortresses
def menu_fortresses():
    # Assuming fortresses is the list from your API response
    data = fortresses  # This should be the list from response['data']
    keyboard_buttons = []

    for entry in data:
        name = entry['name']
        callback_data = f"menu_fortresses_info_{entry['id']}"
        keyboard_buttons.append(InlineKeyboardButton(name, callback_data=callback_data))

    keyboard_buttons.append(InlineKeyboardButton("<< Back", callback_data="menu_main"))
    keyboard = InlineKeyboardMarkup([keyboard_buttons[i:i+2] for i in range(0, len(keyboard_buttons), 2)])

    return keyboard

#Menu fortresses info
def menu_fortresses_info(id):
    data = fortresses  # This should be the list from your API response
    name = 'eRroR'
    totalflags = 'error'
    for entry in data:
        if int(entry['id']) == int(id):
            name = entry['name']
            totalflags = entry['number_of_flags']
            break
    fortresdata = f"<b>{esc(name)}</b>\nNumber of flags: {esc(totalflags)}" + check_user_complete(id, 'fortress')
    return fortresdata

#Menu season with pagination
def menu_season(page=0):
    total_seasons = len(seasons)
    total_pages = (total_seasons + menu_season_items_per_page - 1) // menu_season_items_per_page

    # Validar página
    if page < 0:
        page = 0
    if page >= total_pages:
        page = total_pages - 1

    # Calcular índices
    start_idx = page * menu_season_items_per_page
    end_idx = start_idx + menu_season_items_per_page

    # Obtener temporadas para esta página
    page_seasons = seasons[start_idx:end_idx]

    keyboard_buttons = []

    # Añadir botones de temporadas
    for entry in page_seasons:
        sid = entry['id']
        callback = f'menu_season_info_{sid}'
        name = entry['name']
        keyboard_buttons.append([InlineKeyboardButton(name, callback_data=callback)])

    # Añadir botones de navegación (siempre 2, vacíos si no aplica)
    if total_pages > 1:
        nav_buttons = []

        if page > 0:
            nav_buttons.append(InlineKeyboardButton("◀ Previous", callback_data=f"menu_season_page_{page - 1}"))
        else:
            nav_buttons.append(InlineKeyboardButton(" ", callback_data="menu_season_page_0"))

        if page < total_pages - 1:
            nav_buttons.append(InlineKeyboardButton("Next ▶", callback_data=f"menu_season_page_{page + 1}"))
        else:
            nav_buttons.append(InlineKeyboardButton(" ", callback_data=f"menu_season_page_{page}"))

        keyboard_buttons.append(nav_buttons)

    # Botón de atrás
    keyboard_buttons.append([InlineKeyboardButton("<< Back", callback_data="menu_main")])

    keyboard = InlineKeyboardMarkup(keyboard_buttons)
    return keyboard

#Menu season info
def menu_season_info(sid):
    name = next((item["name"] for item in seasons if str(item.get("id")) == str(sid)), 'Season')
    data = f'<b>{esc(name)}</b>\n'
    total_flags = season_machines_number.get(_parse_int(sid, -1), 0)

    # Recorrer cada usuario en users_ids
    for uid in users_ids:
        # Construir la clave compuesta
        key = f"{sid}{uid}"
        entry_list = season_data.get(key)

        if not isinstance(entry_list, dict):
            continue

        tier = (entry_list.get('season') or {}).get('tier')
        if tier == 'Holo':
            tier = '🔥Holo🔥'
        ranking = (entry_list.get('rank') or {}).get('current')
        user = (entry_list.get('user') or {}).get('name')
        owns = entry_list.get('owns') or {}
        user_flags = (owns.get('user') or {}).get('flags_pawned') or 0
        root_flags = (owns.get('root') or {}).get('flags_pawned') or 0
        pawned_flags = root_flags + user_flags
        data += f'{esc(ranking)} - {esc(user)} - {esc(tier)} - {esc(pawned_flags)}/{esc(total_flags)} Flags\n'

    return data


#######Menus de las secciones nuevas de la API#######

#Coger el primer valor disponible entre varias claves (la API mezcla camelCase y snake_case)
def pick(source, *keys, default=None):
    if not isinstance(source, dict):
        return default
    for key in keys:
        value = source.get(key)
        if value is not None:
            return value
    return default

#Construir un teclado en columnas con boton de vuelta
def build_keyboard(buttons, columns=2, back_callback=None):
    rows = [buttons[i:i + columns] for i in range(0, len(buttons), columns)]
    if back_callback:
        rows.append([InlineKeyboardButton("<< Back", callback_data=back_callback)])
    return InlineKeyboardMarkup(rows)

#Extraer los contadores {solved, total} de una respuesta de progreso
def progress_summary(progress):
    for key, value in (progress or {}).items():
        if key.endswith('_owns') and isinstance(value, dict):
            return value
    return {}

#######Sherlocks#######

#Menu de categorias de Sherlocks
def menu_sherlock_category():
    if not sherlock_category:
        return build_keyboard([], back_callback='menu_main')
    buttons = [
        InlineKeyboardButton(str(item.get('name')), callback_data=f"menu_sherlocks_cat_{item.get('id')}")
        for item in sherlock_category[:MAX_MENU_BUTTONS]
        if item.get('id') is not None
    ]
    return build_keyboard(buttons, columns=2, back_callback='menu_main')

#Listado de Sherlocks de una categoria
def menu_sherlock(category_id):
    buttons = []
    for entry in sherlock_list:
        entry_category = pick(entry, 'category_id', 'categoryId', 'category')
        if str(entry_category) != str(category_id):
            continue
        name = pick(entry, 'name', default='?')
        sherlock_id = entry.get('id')
        if sherlock_id is None:
            continue
        buttons.append(InlineKeyboardButton(str(name), callback_data=f"menu_sherlock_info_{sherlock_id}"))
        if len(buttons) >= MAX_MENU_BUTTONS:
            break
    return build_keyboard(buttons, columns=2, back_callback='menu_sherlock_category')

#Ficha de un Sherlock
def menu_sherlock_info(sherlock_id):
    cached = next((item for item in sherlock_list if str(item.get('id')) == str(sherlock_id)), {})
    detail = htb_sherlock_info(sherlock_id) or {}
    data = {**cached, **detail}

    if not data:
        return 'No se ha podido obtener la información de este Sherlock.'

    name = pick(data, 'name', default='?')
    difficulty = pick(data, 'difficulty', 'difficultyText', default='?')
    category = pick(data, 'category_name', 'categoryName', default='?')
    solves = pick(data, 'solves', 'solves_count', default='?')
    rating = pick(data, 'rating', 'stars', default='?')
    retired = pick(data, 'retired', default=False)
    release = pick(data, 'release_at', 'releaseDate', 'release', default='')
    experience = pick(data, 'experience_points', 'experiencePoints')

    if release:
        release = format_date(release)

    text = (
        f"<b>{esc(name)}</b>\n"
        f"Category: {esc(category)}\n"
        f"Difficulty: {esc(difficulty)}\n"
        f"Solves: {esc(solves)}\n"
        f"Rating: {esc(rating)}\n"
        f"State: {'Retired' if retired else 'Active'}"
    )
    if release:
        text += f"\nRelease: {esc(release)}"
    if experience is not None:
        text += f"\nXP: {esc(experience)}"

    tags = data.get('tags')
    if isinstance(tags, list) and tags:
        tag_names = [str(pick(tag, 'name', default=tag) if isinstance(tag, dict) else tag) for tag in tags[:5]]
        text += "\nTags: " + esc(', '.join(tag_names))

    text += check_user_complete(sherlock_id, 'sherlock')
    return text

#######Pro Labs#######

#Listado de Pro Labs
def menu_prolabs_keyboard():
    buttons = [
        InlineKeyboardButton(str(pick(entry, 'name', default='?')), callback_data=f"menu_prolab_info_{entry.get('id')}")
        for entry in prolabs[:MAX_MENU_BUTTONS]
        if entry.get('id') is not None
    ]
    return build_keyboard(buttons, columns=2, back_callback='menu_main')

#Ficha de un Pro Lab
def menu_prolab_info(prolab_id):
    cached = next((item for item in prolabs if str(item.get('id')) == str(prolab_id)), {})
    overview = htb_prolab_overview(prolab_id) or {}
    data = {**cached, **overview}

    if not data:
        return 'No se ha podido obtener la información de este Pro Lab.'

    name = pick(data, 'name', default='?')
    machines = pick(data, 'pro_machines_count', 'machines_count', 'proMachinesCount', default='?')
    flags = pick(data, 'pro_flags_count', 'flags_count', 'proFlagsCount', default='?')
    skill = pick(data, 'skill_level', 'skillLevel', default='?')
    version = pick(data, 'version', default='')
    eligible = pick(data, 'user_eligible_to_play', 'userEligibleToPlay')

    text = (
        f"<b>{esc(name)}</b>\n"
        f"Machines: {esc(machines)}\n"
        f"Flags: {esc(flags)}\n"
        f"Skill level: {esc(skill)}"
    )
    if version:
        text += f"\nVersion: {esc(version)}"

    designated = data.get('designated_level')
    if isinstance(designated, dict):
        level = pick(designated, 'level', 'category')
        if level:
            text += f"\nLevel: {esc(level)}"

    masters = data.get('lab_masters')
    if isinstance(masters, list) and masters:
        names = [str(pick(master, 'name', default='?')) for master in masters[:4] if isinstance(master, dict)]
        if names:
            text += "\nLab masters: " + esc(', '.join(names))

    if eligible is not None:
        text += f"\nAccesible con tu plan: {'Sí' if eligible else 'No'}"

    return text

#######Starting Point#######

#Menu de tiers de Starting Point con su progreso
def menu_starting_point():
    buttons = []
    for entry in sp_tiers:
        tier_id = entry.get('id')
        if tier_id is None:
            continue
        name = pick(entry, 'name', default=SP_TIERS.get(tier_id, f"Tier {tier_id}"))
        completion = pick(entry, 'completion_percentage', 'completionPercentage', default=0)
        buttons.append(
            InlineKeyboardButton(f"{name} ({completion}%)", callback_data=f"menu_sp_tier_{tier_id}")
        )
    if not buttons:
        buttons = [
            InlineKeyboardButton(label, callback_data=f"menu_sp_tier_{tier}")
            for tier, label in SP_TIERS.items()
        ]
    return build_keyboard(buttons, columns=1, back_callback='menu_main')

#Maquinas de un tier de Starting Point
def menu_sp_tier(tier):
    machines = htb_sp_machines(tier)
    tier_name = next(
        (pick(entry, 'name', default='') for entry in sp_tiers if str(entry.get('id')) == str(tier)),
        SP_TIERS.get(_parse_int(tier, -1), f"Tier {tier}")
    )

    if not machines:
        return f"<b>{esc(tier_name)}</b>\nNo se han podido obtener las máquinas de este tier."

    text = f"<b>{esc(tier_name)}</b>\n\n"
    for entry in machines:
        name = pick(entry, 'name', default='?')
        operating_system = pick(entry, 'os', default='?')
        difficulty = pick(entry, 'difficultyText', 'difficulty_text', 'difficulty', default='?')
        user_owns = pick(entry, 'userOwnsCount', 'user_owns_count', default=0)
        root_owns = pick(entry, 'rootOwnsCount', 'root_owns_count', default=0)
        text += (
            f"<b>{esc(name)}</b> - {esc(operating_system)} - {esc(difficulty)}\n"
            f"Users: {esc(user_owns)} | Root: {esc(root_owns)}\n\n"
        )
    return text

#######Rankings / Hall of Fame#######

#Menu de rankings
menu_rankings = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("Users", callback_data="menu_rankings_users"),
        InlineKeyboardButton("Teams", callback_data="menu_rankings_teams")
    ],
    [
        InlineKeyboardButton("Countries", callback_data="menu_rankings_countries")
    ],
    [
        InlineKeyboardButton("<< Back", callback_data="menu_main")
    ]
])

#Listado de un ranking concreto
def menu_rankings_list(scope):
    entries = rankings.get(scope) or []
    titles = {'users': 'Hall of Fame - Users', 'teams': 'Hall of Fame - Teams', 'countries': 'Hall of Fame - Countries'}
    text = f"<b>{titles.get(scope, scope.title())}</b>\n\n"

    if not entries:
        return text + 'No se han podido obtener los datos del ranking.'

    for position, entry in enumerate(entries[:RANKING_ROWS], start=1):
        rank = pick(entry, 'rank', 'position', default=position)
        name = pick(entry, 'name', 'value', default='?')
        if isinstance(name, dict):
            name = pick(name, 'name', default='?')
        points = pick(entry, 'points', 'score', default='?')
        line = f"{esc(rank)}. {esc(name)} - {esc(points)} pts"

        if scope == 'users':
            country = pick(entry, 'country', 'country_name')
            if isinstance(country, dict):
                country = pick(country, 'name')
            if country:
                line += f" ({esc(country)})"
        else:
            members = pick(entry, 'members', 'member_count', 'members_count')
            if members is not None:
                line += f" - {esc(members)} members"

        text += line + "\n"

    return text

#######Vistas ampliadas de usuario#######

#Submenu de acciones sobre un usuario
def menu_user_actions(uid):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📊 Progress", callback_data=f"menu_user_progress_{uid}"),
            InlineKeyboardButton("⚡ XP", callback_data=f"menu_user_xp_{uid}")
        ],
        [
            InlineKeyboardButton("🏆 Seasons", callback_data=f"menu_user_seasons_{uid}")
        ],
        [
            InlineKeyboardButton("<< Back", callback_data="menu_user")
        ]
    ])

#Progreso del usuario por tipo de contenido
def menu_user_progress(uid):
    user_profile = profile.get(uid) or {}
    name = user_profile.get('name', uid)
    text = f"<b>{esc(name)}</b> - Progress\n\n"

    areas = [
        ('machines', 'Machines'),
        ('challenges', 'Challenges'),
        ('sherlocks', 'Sherlocks'),
        ('fortress', 'Fortresses'),
        ('prolab', 'Pro Labs'),
    ]

    for area, label in areas:
        summary = progress_summary(htb_profile_progress(uid, area))
        if not summary:
            continue
        solved = pick(summary, 'solved', 'owned', default=0)
        total = pick(summary, 'total', default=0)
        percentage = pick(summary, 'completion_percentage', 'completionPercentage', default=0)
        text += f"{esc(label)}: {esc(solved)}/{esc(total)} ({esc(percentage)}%)\n"

    badges = htb_profile_badges(uid)
    if badges:
        text += f"Badges: {esc(len(badges))}\n"

    if text.endswith('\n\n'):
        text += 'No hay datos de progreso disponibles para este usuario.'
    return text

#XP, nivel y racha del usuario
def menu_user_xp(uid):
    user_profile = profile.get(uid) or {}
    name = user_profile.get('name', uid)
    account_id = user_profile.get('account_id')

    if not account_id:
        return f"<b>{esc(name)}</b> - XP\n\nEste usuario no expone su account_id, no se puede consultar la XP."

    experience = htb_experience(account_id)
    if not experience:
        return f"<b>{esc(name)}</b> - XP\n\nNo se han podido obtener los datos de experiencia."

    level = pick(experience, 'level', default='?')
    level_title = pick(experience, 'levelTitle', default='')
    level_grade = pick(experience, 'levelGrade', default='')
    total_xp = pick(experience, 'totalExperiencePoints', default='?')
    next_level = pick(experience, 'experienceUntilNextLevel')

    text = f"<b>{esc(name)}</b> - XP\n\nLevel: {esc(level)}"
    if level_title:
        text += f" - {esc(level_title)}"
    if level_grade:
        text += f" (grade {esc(level_grade)})"
    text += f"\nTotal XP: {esc(total_xp)}"
    if next_level is not None:
        text += f"\nXP para el siguiente nivel: {esc(next_level)}"

    streak = experience.get('streakData')
    if isinstance(streak, dict):
        counter = pick(streak, 'counter', default=0)
        max_streak = pick(streak, 'maxStreak', default='?')
        completed = pick(streak, 'isCompleted', default=False)
        in_danger = pick(streak, 'inDanger', default=False)
        text += f"\n\n🔥 Streak: {esc(counter)} días (máx. {esc(max_streak)})"
        text += f"\nHoy: {'completada' if completed else 'pendiente'}"
        if in_danger:
            text += "\n⚠️ La racha está en peligro"

    return text

#Historico de temporadas del usuario
def menu_user_seasons(uid):
    user_profile = profile.get(uid) or {}
    name = user_profile.get('name', uid)
    ranks = htb_season_user_ranks(uid)

    text = f"<b>{esc(name)}</b> - Seasons\n\n"
    if not ranks:
        return text + 'No hay datos de temporadas para este usuario.'

    for entry in ranks:
        if not isinstance(entry, dict):
            continue
        season_name = pick(entry, 'name', 'season_name', 'season', default='?')
        if isinstance(season_name, dict):
            season_name = pick(season_name, 'name', default='?')
        league = pick(entry, 'league', 'tier', default='')
        rank = pick(entry, 'rank', 'position', 'current_rank', default='?')
        points = pick(entry, 'total_season_points', 'points')

        line = f"<b>{esc(season_name)}</b>: {esc(rank)}"
        if league:
            line += f" - {esc(league)}"
        if points is not None:
            line += f" - {esc(points)} pts"
        text += line + "\n"

    return text

#######Other functions#######

#Cache HTB data (blocking; run via asyncio.to_thread from async handlers)
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
        global seasons, season_data, season_machines_number
        seasons = htb_season_list()
        season_data = {}
        season_machines_number = {}
        for season in seasons:
            sid = season['id']
            season_machines_number[sid] = htb_season_machines_number(sid)
            for uid in users_ids:
                seasonfinalid = f"{sid}{uid}"
                season_data[seasonfinalid] = htb_season_position(sid, uid)

    def get_sherlocks():
        global sherlock_category, sherlock_list
        sherlock_category = htb_sherlock_categories_list()
        sherlock_list = htb_sherlock_list()

    def get_prolabs():
        global prolabs
        prolabs = htb_prolabs()

    def get_starting_point():
        global sp_tiers
        sp_tiers = htb_sp_tiers_progress()

    def get_rankings():
        global rankings
        rankings = {
            scope: htb_rankings(scope)
            for scope in ('users', 'teams', 'countries')
        }

    def get_profiles():
        global profile, profile_activity, profile_challenges, users_list, menu_user, country_users_top
        users_list = []
        for uid in users_ids:
            profile[uid] = htb_profile(uid)
            profile_activity[uid] = htb_profile_activity(uid)
            profile_challenges[uid] = htb_profile_challenges(uid)
            country_code = profile[uid].get('country_code')
            if country_code and country_code not in country_users_top:
                country_users_top[country_code] = htb_country_users_top(country_code)
            new_user = {'user': str(profile[uid].get('name') or uid), 'id': uid}
            users_list.append(new_user)
        menu_user = menu_user_function()

    workers = [
        get_challenge_category,
        get_challenge_list,
        get_machine_list,
        get_machine_unreleased,
        get_profiles,
        get_fortresses,
        get_seasons,
        get_sherlocks,
        get_prolabs,
        get_starting_point,
        get_rankings,
    ]

    def run_worker(worker):
        """Un fallo en una sección no debe tumbar el refresco completo de la caché."""
        try:
            worker()
        except Exception:
            logger.exception("Error refrescando la caché en %s", worker.__name__)

    threads = [threading.Thread(target=run_worker, args=(worker,)) for worker in workers]

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

        activity_list = profile_activity.get(user_id['id'], [])
        if not isinstance(activity_list, list):
            activity_list = []

        user = False
        root = False
        pwn = False
        fortress_flags = 0
        total_flags = 0  # Para saber cuántas flags tiene la fortaleza

        # Obtener el total de flags de la fortaleza
        if type == 'fortress':
            for fortress in fortresses:  # Asumiendo que fortresses es tu lista de fortalezas
                if int(fortress['id']) == int(id):
                    total_flags = fortress['number_of_flags']
                    break

        for item in activity_list:
            if isinstance(item, dict):
                item_id = item.get("id")
                item_type = item.get("type")
                fortress_id = item.get("fortressId")  # Importante: campo correcto para fortalezas

                # Para máquinas
                if type == 'machine':
                    if item_id is not None and str(item_id) == str(id):
                        if item_type == 'user':
                            user = True
                        elif item_type == 'root':
                            root = True
                # Para challenges
                elif type == 'challenge' and item_type == 'challenge':
                    if item_id is not None and str(item_id) == str(id):
                        pwn = True
                # Para sherlocks
                elif type == 'sherlock' and item_type == 'sherlock':
                    if item_id is not None and str(item_id) == str(id):
                        pwn = True
                # Para fortresses - usar fortressId, no id
                elif type == 'fortress' and item_type == 'fortress':
                    if fortress_id is not None and str(fortress_id) == str(id):
                        fortress_flags += 1

        # Determinar el estado
        if root:
            status = '<b>🔥Rooted🔥</b>'
        elif user:
            status = 'Usered'
        elif pwn:
            status = '<b>🔥Pwned🔥</b>'
        elif type == 'fortress':
            status = f'{str(fortress_flags)}/{total_flags} Flags'  # Mostrar progreso
        else:
            status = 'Pending'

        result = result + ' \n' + esc(username) + ' Status: ' + status

    return result

#Check challenge category name by id
def check_challenge_category_name(id_to_search):
    for item in challenge_category:
        if item['id'] == id_to_search:
            return item['name']

def check_country_users_top(id_to_search, country_code):
    for item in country_users_top.get(country_code) or []:
        if str(item.get("id")) == str(id_to_search):
            return str(item.get("rank"))
    return '?'

#Edit message of telegram bot
async def edit_message(context, chat_id, message_id, text, keyboard):
    await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, reply_markup=keyboard, parse_mode='HTML')

#Lock para que varios usuarios a la vez no disparen refrescos simultáneos
cache_lock = asyncio.Lock()

#Comprobar si la caché ha caducado
def cache_expired():
    return datetime.now() - cache_date > timedelta(minutes=cache_ttl_minutes)

#Refresh the HTB cache in a worker thread so the event loop keeps serving updates
async def refresh_cache(force=False):
    """Refresca la caché de HTB. Sin `force` solo se refresca si ha caducado.

    Evita que hacer spam de /htb dispare decenas de tandas de peticiones a la API.
    """
    async with cache_lock:
        if not force and not cache_expired():
            return
        await asyncio.to_thread(cache)

#######Telegram actions#######

#Command /htb
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message.chat_id in allowed_list:
        response = "Choose action:"
        await context.bot.send_message(update.message.chat_id, response, reply_markup=menu_main)
        await refresh_cache()  # solo consulta la API si la caché ha caducado
    else:
        response = 'You are not authorized'
        await update.message.reply_text(response, parse_mode='HTML', disable_web_page_preview=True)

#Command /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message.chat_id in allowed_list:
        if update.message.chat_id in admin_list:
            response = (
                'Make /htb to use the bot\n'
                'Make /search &lt;texto&gt; to search HTB users and teams\n'
                'Make /cachedate to view the date of cache\n'
                'Make /refresh to force a cache refresh\n'
                'Make /adduser to add users\n'
                'Make /purgeuser to purge users'
            )
        else:
            response = 'Make /htb to use the bot\nMake /search &lt;texto&gt; to search HTB users and teams'
        await update.message.reply_text(response, parse_mode='HTML', disable_web_page_preview=True)
    else:
        response = 'You are not authorized'
        await update.message.reply_text(response, parse_mode='HTML', disable_web_page_preview=True)

#Command /cachedate
async def cachedate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message.chat_id in admin_list:
        await update.message.reply_text(str(cache_date), parse_mode='HTML', disable_web_page_preview=True)
    else:
        response = 'You are not authorized'
        await update.message.reply_text(response, parse_mode='HTML', disable_web_page_preview=True)

# Command /adduser
async def add_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message.chat_id in admin_list:
        args = context.args
        if len(args) == 1:
            global users_ids
            new_user = args[0]
            candidates = [item.strip() for item in new_user.split(',') if item.strip()]
            valid = [item for item in candidates if item.isdigit() and item not in users_ids]
            invalid = [item for item in candidates if not item.isdigit()]

            if valid:
                users_ids.extend(valid)
                await refresh_cache(force=True)
                response = f"Users with IDs '{esc(', '.join(valid))}' has been added."
            else:
                response = "No se ha añadido ningún usuario nuevo."
            if invalid:
                response += f"\nIDs ignorados (deben ser numéricos): {esc(', '.join(invalid))}"
        else:
            response = "Usage: /adduser id,id"
        await update.message.reply_text(response, parse_mode='HTML', disable_web_page_preview=True)
    else:
        response = 'You are not authorized'
        await update.message.reply_text(response, parse_mode='HTML', disable_web_page_preview=True)

#Command /purgeuser
async def purge_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global users_ids, menu_user
    if update.message.chat_id in admin_list:
        args = context.args
        if len(args) == 1:
            id_to_remove = args[0]
            candidates = [item.strip() for item in id_to_remove.split(',') if item.strip()]
            removed = []
            for candidate in candidates:
                if candidate in users_ids:
                    users_ids.remove(candidate)
                    removed.append(candidate)

            if removed:
                await refresh_cache(force=True)
                response = f"Users with IDs '{esc(', '.join(removed))}' have been purged."
            else:
                response = "User ID doesn't exist."
        else:
            response = "Usage: /purgeuser id,id"
        await update.message.reply_text(response, parse_mode='HTML', disable_web_page_preview=True)
    else:
        response = 'You are not authorized'
        await update.message.reply_text(response, parse_mode='HTML', disable_web_page_preview=True)


#Command /search - busca usuarios y equipos en HTB
async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message.chat_id not in allowed_list:
        await update.message.reply_text('You are not authorized', parse_mode='HTML', disable_web_page_preview=True)
        return

    query = ' '.join(context.args).strip()
    if len(query) < 2:
        await update.message.reply_text(
            "Usage: /search &lt;texto&gt; (mínimo 2 caracteres)",
            parse_mode='HTML',
            disable_web_page_preview=True,
        )
        return

    results = await asyncio.to_thread(htb_search, query)
    users = results.get('users') or []
    teams = results.get('teams') or []

    if not users and not teams:
        response = f"Sin resultados para <b>{esc(query)}</b>."
    else:
        response = f"Resultados para <b>{esc(query)}</b>\n"
        if users:
            response += "\n<b>Users</b>\n"
            for item in users[:10]:
                name = pick(item, 'value', 'name', default='?')
                response += f"{esc(name)} - ID: <code>{esc(item.get('id'))}</code>\n"
        if teams:
            response += "\n<b>Teams</b>\n"
            for item in teams[:10]:
                name = pick(item, 'value', 'name', default='?')
                response += f"{esc(name)} - ID: <code>{esc(item.get('id'))}</code>\n"
        if users and update.message.chat_id in admin_list:
            response += "\nUsa /adduser &lt;id&gt; para empezar a seguir a un usuario."

    await update.message.reply_text(response, parse_mode='HTML', disable_web_page_preview=True)

#Command /refresh - fuerza el refresco de la cache
async def refresh_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message.chat_id in admin_list:
        await update.message.reply_text('Refrescando la caché de HTB...', parse_mode='HTML', disable_web_page_preview=True)
        await refresh_cache(force=True)
        await update.message.reply_text(f'Caché actualizada: {esc(cache_date)}', parse_mode='HTML', disable_web_page_preview=True)
    else:
        response = 'You are not authorized'
        await update.message.reply_text(response, parse_mode='HTML', disable_web_page_preview=True)

#Command Buttons
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    #Query
    query = update.callback_query
    data=query.data
    chat_id = query.message.chat_id
    message_id = query.message.message_id

    #If allowed
    if query.message.chat_id in allowed_list:

        #Acknowledge the callback so Telegram stops showing the loading spinner
        await query.answer()

        #Command executed
        print(data)

        #Refresca los datos si la caché ha caducado (CACHE_TTL_MINUTES)
        await refresh_cache()

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
                keyboard = menu_user or back_button('menu_main')

            #menu_user_info
            case data if any(user['id'] == data for user in users_list):
                text = menu_user_info(data)
                keyboard=menu_user_actions(data)

            #menu_user_progress
            case data if data.startswith('menu_user_progress_'):
                uid = data[len('menu_user_progress_'):]
                text = await asyncio.to_thread(menu_user_progress, uid)
                keyboard = back_button(uid)

            #menu_user_xp
            case data if data.startswith('menu_user_xp_'):
                uid = data[len('menu_user_xp_'):]
                text = await asyncio.to_thread(menu_user_xp, uid)
                keyboard = back_button(uid)

            #menu_user_seasons
            case data if data.startswith('menu_user_seasons_'):
                uid = data[len('menu_user_seasons_'):]
                text = await asyncio.to_thread(menu_user_seasons, uid)
                keyboard = back_button(uid)

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
                total_seasons = len(seasons)
                total_pages = (total_seasons + menu_season_items_per_page - 1) // menu_season_items_per_page
                text = f"Choose the season (Page 1/{total_pages}):"
                keyboard=menu_season(0)

            #menu_season_page pagination
            case data if data.startswith('menu_season_page_'):
                page = int(data[len('menu_season_page_'):])
                total_seasons = len(seasons)
                total_pages = (total_seasons + menu_season_items_per_page - 1) // menu_season_items_per_page
                # Validar página
                if page >= total_pages:
                    page = total_pages - 1
                if page < 0:
                    page = 0
                text = f"Choose the season (Page {page + 1}/{total_pages}):"
                keyboard=menu_season(page)

            #menu_season_info
            case data if data.startswith('menu_season_info_'):
                sid=data[len('menu_season_info_'):]
                text=menu_season_info(sid)
                keyboard = back_button('menu_season')

            #menu_sherlock_category
            case 'menu_sherlock_category':
                text = "Choose sherlock category:"
                keyboard = menu_sherlock_category()

            #menu_sherlocks de una categoria
            case data if data.startswith('menu_sherlocks_cat_'):
                category_id = data[len('menu_sherlocks_cat_'):]
                text = "Choose the sherlock:"
                keyboard = menu_sherlock(category_id)

            #menu_sherlock_info
            case data if data.startswith('menu_sherlock_info_'):
                sherlock_id = data[len('menu_sherlock_info_'):]
                cached = next((item for item in sherlock_list if str(item.get('id')) == str(sherlock_id)), {})
                category_id = pick(cached, 'category_id', 'categoryId', 'category', default='')
                text = await asyncio.to_thread(menu_sherlock_info, sherlock_id)
                keyboard = back_button(f'menu_sherlocks_cat_{category_id}' if category_id != '' else 'menu_sherlock_category')

            #menu_prolabs
            case 'menu_prolabs':
                text = "Choose the Pro Lab:"
                keyboard = menu_prolabs_keyboard()

            #menu_prolab_info
            case data if data.startswith('menu_prolab_info_'):
                prolab_id = data[len('menu_prolab_info_'):]
                text = await asyncio.to_thread(menu_prolab_info, prolab_id)
                keyboard = back_button('menu_prolabs')

            #menu_starting_point
            case 'menu_starting_point':
                text = "Choose the Starting Point tier:"
                keyboard = menu_starting_point()

            #menu_sp_tier
            case data if data.startswith('menu_sp_tier_'):
                tier = data[len('menu_sp_tier_'):]
                text = await asyncio.to_thread(menu_sp_tier, tier)
                keyboard = back_button('menu_starting_point')

            #menu_rankings
            case 'menu_rankings':
                text = "Choose the ranking:"
                keyboard = menu_rankings

            #menu_rankings_{scope}
            case data if data.startswith('menu_rankings_'):
                scope = data[len('menu_rankings_'):]
                if scope not in ('users', 'teams', 'countries'):
                    text = 'Ranking no disponible'
                    keyboard = back_button('menu_rankings')
                else:
                    text = menu_rankings_list(scope)
                    keyboard = back_button('menu_rankings')

            case _:
                text='Unexpected error'
                keyboard = back_button('menu_main')

        await edit_message(context, chat_id, message_id, text, keyboard)
    else:
        response = 'You are not authorized'
        await query.answer()
        await query.message.reply_text(response, parse_mode='HTML', disable_web_page_preview=True)

#######Start bot#######

#Captura las excepciones no controladas de los handlers para que el bot no se quede mudo
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Error procesando la actualización %s", update, exc_info=context.error)

    chat = getattr(update, 'effective_chat', None)
    if chat is not None and chat.id in allowed_list:
        try:
            await context.bot.send_message(chat.id, 'Se ha producido un error procesando la petición.')
        except Exception:
            logger.exception("No se ha podido notificar el error al chat %s", chat.id)

def main():
    application = Application.builder().token(TOKEN).build()

    # Events that will trigger our bot.
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CommandHandler('htb', start))
    application.add_handler(CommandHandler('search', search_command))
    application.add_handler(CommandHandler('adduser', add_user))
    application.add_handler(CommandHandler('purgeuser', purge_user))
    application.add_handler(CommandHandler('cachedate', cachedate))
    application.add_handler(CommandHandler('refresh', refresh_command))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_error_handler(error_handler)

    # Start bot and listen for updates until interrupted
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
