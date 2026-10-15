import time
import re
import requests
import hw_parser as parser

main_url = "http://hw1.alexbers.com"

user_cookies = {
    'user': 'ff2fa6730bddb5ff77717c04e37ae700'
}
response = requests.get(main_url, cookies=user_cookies)
page = response.text
step = 0

while True:
    secret = re.search(r'Секретный ключ: <b><code>([^<]+)</code>', page)
    if secret:
        print(f"\nСекретный токен найден: {secret.group(1)}")
        break

    step += 1

    sample = re.search(r'Отправьте (\w+)-запрос по адресу <code>([^<]+)</code>', page)
    if sample:
        method = sample.group(1)
        address = sample.group(2)
    else:
        sample = re.search(r'Перейдите по <a href=["\']([^"\']+)["\']', page)
        if sample:
            method = 'GET'
            address = sample.group(1)
        else:
            sample = re.search(r'Загрузите файлы по адресу <code>([^<]+)</code>', page)
            if sample:
                method = 'POST'
                address = sample.group(1)

    print(f"ШАГ : {step} -> {method} {address}")

    tables = page.split("<table")

    result = {'cookies': {}, 'headers': {}, 'forms': {}, 'params': {}, 'files': {}}
    for k in range(1, len(tables)):
        labels = tables[k - 1][-130:]
        table = parser.parse_table(tables[k])
        if 'cookie' in labels:
            result['cookies'] = table
        elif 'Содержимое' in tables[k][:200]:
            result['files'] = table
        elif 'заголовки' in labels:
            result['headers'] = table
        elif 'данные формы' in labels:
            result['forms'] = table
        elif 'параметры запроса' in labels:
            result['params'] = table

    files = None
    if result['files']:
        files = {name: (name, item.encode("UTF-8"))
                 for name, item in result['files'].items()}

    cookies = {**result['cookies'], **user_cookies}


    response = None
    for attempt in range(5):
        try:
            response = requests.request(
                method, main_url + address,
                cookies=cookies, headers=result['headers'],
                params=result['params'], data=result['forms'],
                files=files, timeout=15
            )
            break
        except (requests.exceptions.ProxyError, requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            print(f"Прокси сбросил соединение (попытка {attempt + 1}/5), ждем...")
            time.sleep(2)

    if response is None:
        print("я рот ебал.")
        break

    print(f"   Статус ответа с сервера: {response.status_code}")
    page = response.text