import json
import os

SETTINGS_FILE = 'settings.json'

DEFAULT_SETTINGS = {
    "theme": "light",
    "app_password": "",
    "autostart_enabled": False,
    "categories": ["Работа","Учеба","Личное","Здоровье","Финансы"]  # стандартные + пользовательские
}

def load_settings():
    if not os.path.exists(SETTINGS_FILE):
        save_settings(DEFAULT_SETTINGS)
        return DEFAULT_SETTINGS.copy()
    try:
        with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        for k, v in DEFAULT_SETTINGS.items():
            data.setdefault(k, v)
        return data
    except Exception:
        return DEFAULT_SETTINGS.copy()

def save_settings(settings):
    with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)

def set_theme(theme):
    s = load_settings()
    s['theme'] = theme
    save_settings(s)

def set_password(password):
    s = load_settings()
    s['app_password'] = password or ""
    save_settings(s)

def set_autostart(enabled):
    s = load_settings()
    s['autostart_enabled'] = bool(enabled)
    save_settings(s)

def add_category(name):
    s = load_settings()
    name = name.strip()
    if name and name not in s['categories']:
        s['categories'].append(name)
        save_settings(s)

def remove_category(name):
    s = load_settings()
    if name in s['categories']:
        s['categories'].remove(name)
        save_settings(s)

