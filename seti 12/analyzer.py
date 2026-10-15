import bs4
from config import AUTH_TOKEN, MULTIPART_BOUNDARY
from serializer import PayloadSerializer as Serializer


class QuestStepType:
    COOKIE = 0
    QUERY = 1
    FORM = 2
    FILES = 3
    HEADERS = 4


class ResponseAnalyzer:
    @staticmethod
    def extract_request_payload(raw_response: str) -> dict:
        soup = bs4.BeautifulSoup(raw_response, "lxml")
        http_method, target_path = ResponseAnalyzer._detect_route(raw_response, soup)

        mapping = {
            raw_response.find("cookie"): QuestStepType.COOKIE,
            raw_response.find("параметры запроса"): QuestStepType.QUERY,
            raw_response.find("данные формы"): QuestStepType.FORM,
            raw_response.find("Загрузите файлы"): QuestStepType.FILES,
            raw_response.find("заголовки"): QuestStepType.HEADERS,
        }

        tables = soup.find_all("table")
        active_actions = [action for pos, action in sorted(mapping.items()) if pos != -1]

        if len(active_actions) != len(tables):
            raise RuntimeError("Обнаружена новая или неподдерживаемая структура страницы!")

        cookie_str = ""
        query_str = ""
        request_body = []
        http_headers = []

        for idx, action_type in enumerate(active_actions):
            extracted_data = ResponseAnalyzer._table_to_map(tables[idx])

            if action_type == QuestStepType.COOKIE:
                cookie_str = Serializer.to_cookie_string(extracted_data)
            elif action_type == QuestStepType.QUERY:
                query_str = Serializer.format_query(extracted_data)
            elif action_type == QuestStepType.FORM:
                request_body = Serializer.format_form_urlencoded(extracted_data)
            elif action_type == QuestStepType.FILES:
                request_body = Serializer.format_multipart(extracted_data)
            elif action_type == QuestStepType.HEADERS:
                http_headers = Serializer.format_headers(extracted_data)

        http_headers.append(f"Cookie: user={AUTH_TOKEN};{cookie_str}")

        if QuestStepType.FILES in active_actions:
            http_headers.append(f"Content-Type: multipart/form-data; boundary={MULTIPART_BOUNDARY}")
        elif QuestStepType.FORM in active_actions:
            http_headers.append("Content-Type: application/x-www-form-urlencoded")

        return {
            "method": http_method,
            "path": f"{target_path}{query_str}",
            "headers": http_headers,
            "body": request_body,
        }

    @staticmethod
    def _detect_route(response_text: str, soup: bs4.BeautifulSoup):
        if "ссылке" in response_text:
            return "GET", soup.find("a", href=True)["href"]
        if "GET" in response_text:
            return "GET", soup.find("code").text
        if "POST" in response_text or "Загрузите файлы" in response_text:
            return "POST", soup.find("code").text

        raise RuntimeError("Не удалось определить метод и путь для следующего запроса.")

    @staticmethod
    def _table_to_map(table_tag) -> dict:
        code_elements = [element.text for element in table_tag.find_all("code")]
        if len(code_elements) % 2 != 0:
            raise ValueError("Ошибка разбора таблицы: нечетное количество элементов.")

        result_map = {}
        for i in range(0, len(code_elements), 2):
            result_map[code_elements[i]] = code_elements[i + 1]
        return result_map