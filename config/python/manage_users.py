import json
import sys

# Путь к конфигурационному файлу
config_path = '/usr/local/etc/xray/config.json'

def load_config():
    """Загрузить JSON-конфигурацию."""
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Ошибка при загрузке конфигурации: {e}")
        sys.exit(1)

def save_config(config):
    """Сохранить JSON-конфигурацию."""
    try:
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=4)
        print("Конфигурация успешно сохранена.")
    except Exception as e:
        print(f"Ошибка при сохранении конфигурации: {e}")
        sys.exit(1)

def add_user(uuid, email, flow=None):
    """Добавить клиента в конфигурацию."""
    config = load_config()

    new_client = {
        "id": uuid,
        "email": email,
    }
    if flow:
        new_client["flow"] = flow

    # Предполагается, что клиенты находятся в разделе inbounds->settings->clients
    for inbound in config['inbounds']:
        if 'clients' in inbound.get('settings', {}):
            inbound['settings']['clients'].append(new_client)
            print(f"Пользователь с UUID {uuid} добавлен.")
    
    save_config(config)

def remove_user(email):
    """Удалить клиента из конфигурации по E-Mail."""
    config = load_config()

    for inbound in config['inbounds']:
        if 'clients' in inbound.get('settings', {}):
            initial_count = len(inbound['settings']['clients'])
            inbound['settings']['clients'] = [client for client in inbound['settings']['clients'] if client['email'] != email]
            if len(inbound['settings']['clients']) < initial_count:
                print(f"Пользователь с E-Mail {email} удален.")
            else:
                print(f"Пользователь с E-Mail {email} не найден.")
    
    save_config(config)

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Использование: python3 manage_users.py add <uuid> <email> [flow]")
        print("Использование: python3 manage_users.py remove <uuid>")
        sys.exit(1)

    command = sys.argv[1]
    if command == 'add':
        if len(sys.argv) < 4:
            print("Необходимо указать UUID и email для добавления пользователя.")
            sys.exit(1)
        uuid = sys.argv[2]
        email = sys.argv[3]
        flow = sys.argv[4] if len(sys.argv) > 4 else None
        add_user(uuid, email, flow)
    elif command == 'remove':
        uuid = sys.argv[2]
        remove_user(uuid)
    else:
        print("Неизвестная команда. Используйте 'add' или 'remove'.")
