from config import MULTIPART_BOUNDARY


class PayloadSerializer:
    @staticmethod
    def to_cookie_string(data_dict: dict) -> str:
        return "".join([f"{k}={v};" for k, v in data_dict.items()])[:-1]

    @staticmethod
    def format_headers(data_dict: dict) -> list:
        return [f"{k}: {v}" for k, v in data_dict.items()]

    @staticmethod
    def format_query(data_dict: dict) -> str:
        if not data_dict:
            return ""
        params = "&".join([f"{k}={v}" for k, v in data_dict.items()])
        return f"?{params}"

    @staticmethod
    def format_multipart(files_dict: dict) -> list:
        result = []
        for file_name, file_content in files_dict.items():
            result.append(f"--{MULTIPART_BOUNDARY}")
            result.append(f'Content-Disposition: form-data; filename="{file_name}"')
            result.append("")
            result.append(str(file_content))
        result.append(f"--{MULTIPART_BOUNDARY}--")
        return result

    @staticmethod
    def format_form_urlencoded(data_dict: dict) -> list:
        if not data_dict:
            return [""]
        encoded = "&".join([f"{k}={v}" for k, v in data_dict.items()])
        return [encoded]