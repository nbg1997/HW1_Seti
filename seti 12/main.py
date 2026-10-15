import socket
import bs4
from config import HOST, PORT, AUTH_TOKEN
from network import SocketHttpClient
from analyzer import ResponseAnalyzer


def run():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((HOST, PORT))

    current_response = SocketHttpClient.send_request(
        client_socket, headers=[f"Cookie: user={AUTH_TOKEN}"]
    )

    while True:
        for line in current_response.split("\n"):
            if "Шаг" in line:
                print(line.strip()[4:-5])

        step_data = ResponseAnalyzer.extract_request_payload(current_response)

        current_response = SocketHttpClient.send_request(
            client_socket,
            method=step_data["method"],
            endpoint=step_data["path"],
            headers=step_data["headers"],
            payload=step_data["body"],
        )

        if "Поздравляем," in current_response:
            break

    parsed_html = bs4.BeautifulSoup(current_response, "lxml")
    secret_code = parsed_html.find("code")
    print(f"\n[УРААААААААААААА] Секретный токен НАЙДЕН: {secret_code.text if secret_code else 'Смотри тело ответа'}")

    client_socket.close()


if __name__ == "__main__":
    run()