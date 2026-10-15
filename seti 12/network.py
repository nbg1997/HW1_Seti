import socket


class SocketHttpClient:
    @staticmethod
    def send_request(
            sock: socket.socket,
            method: str = "GET",
            endpoint: str = "/",
            headers: list = None,
            payload: list = None,
            timeout: int = 5,
    ) -> str:
        if headers is None:
            headers = []
        if payload is None:
            payload = []

        if method not in ("GET", "POST"):
            raise ValueError(f"Неподдерживаемый HTTP метод: {method}")

        body_len = len(("\r\n".join(payload)).encode("utf-8"))

        request_lines = [
            f"{method} {endpoint} HTTP/1.1",
            "Host: hw1.alexbers.com",
            f"Content-Length: {body_len}",
            "Connection: keep-alive",
        ]

        if headers:
            request_lines.extend(headers)

        if payload:
            request_lines.append("")
            request_lines.extend(payload)

        raw_request = ("\r\n".join(request_lines) + "\r\n\r\n").encode("utf-8")

        sock.settimeout(timeout)
        sock.sendall(raw_request)

        response_data = sock.recv(4096)
        if b"\r\n\r\n" not in response_data:
            return response_data.decode("utf-8", errors="ignore")

        resp_headers, resp_body = response_data.split(b"\r\n\r\n", 1)

        expected_length = 0
        for line in resp_headers.split(b"\r\n"):
            if b"Content-Length" in line:
                expected_length = int(line.split(b" ")[1])
                break

        while len(resp_body) < expected_length:
            chunk = sock.recv(1024)
            if not chunk:
                break
            resp_body += chunk

        return (resp_headers + b"\r\n\r\n" + resp_body).decode("utf-8", errors="ignore")