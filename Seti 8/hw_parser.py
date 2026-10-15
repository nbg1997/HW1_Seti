from bs4 import BeautifulSoup


def parse_table(table_html: str) -> dict:
    full_html = "<table" + table_html
    soup = BeautifulSoup(full_html, "lxml")
    table = soup.find("table")
    if not table:
        return {}


    code_elements = [el.get_text().strip() for el in table.find_all("code")]

    result = {}
    if len(code_elements) >= 2 and len(code_elements) % 2 == 0:
        for i in range(0, len(code_elements), 2):
            k = code_elements[i]
            v = code_elements[i + 1]
            if k.lower() not in ["ключ", "header", "key", "имя файла", "параметр"]:
                result[k] = v
    else:
        for row in table.find_all("tr"):
            cols = row.find_all(["td", "th"])
            if len(cols) >= 2:
                k = cols[0].get_text().strip()
                v = cols[1].get_text().strip()
                if k and v and k.lower() not in ["ключ", "header", "key", "имя файла", "параметр"]:
                    result[k] = v

    return result