import mimetypes
import socket
import json
import urllib.parse
import logging
from datetime import datetime
from threading import Thread
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler


HTTP_HOST = '0.0.0.0'
HTTP_PORT = 3000
SOCKET_HOST = 'localhost'
SOCKET_PORT = 5000
BASE_DIR = Path(__file__).resolve().parent
BUFFER_SIZE = 1024


class MyHTTPFramework (SimpleHTTPRequestHandler):
    def do_GET(self):
        # super().do_GET()
        route = urllib.parse.urlparse(self.path)
        print(route)
        match route.path:
            case '/':
                self.send_html('index.html')
            case '/message':
                self.send_html('message.html')
            case _:
                file = BASE_DIR / route.path.lstrip('/')
                if file.exists() and file.is_file():
                    self.send_static(file)
                else:
                    self.send_html('error.html', 404)

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length'))
        post_data = self.rfile.read(content_length)
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            client_socket.sendto(post_data, (SOCKET_HOST, SOCKET_PORT))
            client_socket.close()

            self.send_response(302)
            self.send_header('Location', '/message')
        except Exception as e:
            logging.error(f'Error sending data to socket: {e}')
            self.send_response(404)
            self.send_header('Location', '/error')
        finally:
            self.end_headers()

    def send_html(self, html_file: str, status_code: int = 200):
        self.send_response(status_code)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        with open(BASE_DIR / html_file, 'rb') as file:
            self.wfile.write(file.read())

    def send_static(self, file: str, status_code: int = 200):
        self.send_response(status_code)
        mimetype = mimetypes.guess_type(file)[0]
        if mimetype:
            self.send_header('Content-type', mimetype)
        else:
            self.send_header('Content-type', 'text/plain')
        self.end_headers()
        with open(BASE_DIR / file, 'rb') as f:
            self.wfile.write(f.read())


def save_json_data(data: str):
    file_path = BASE_DIR / 'storage/data.json'
    if file_path.exists():
        with open(file_path, "r", encoding="utf-8") as file:
            file_data = json.load(file)
    else:
        file_data = {}
    d = urllib.parse.unquote_plus(data)
    try:
        parsed_data = {key: value for key, value in [el.split('=') for el in d.split('&')]}
        key = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        file_data[key] = parsed_data
        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump(file_data, file, ensure_ascii=False, indent=4)
    except Exception as e:
        logging.error(f'Error saving data in socket: {e}')


def run_http_server(host: str, port: int):
    address = (host, port)
    http_server = HTTPServer(address, MyHTTPFramework)
    logging.info(f'HTTP server running on {host}:{port}')
    try:
        http_server.serve_forever()
    except KeyboardInterrupt:
        logging.info('Destroy server')
    finally:
        http_server.server_close()


def run_socket_server(host: str, port: int):
    socket_server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    socket_server.bind((host, port))
    logging.info(f'Socket server running on {host}:{port}')
    try:
        while True:
            data, address = socket_server.recvfrom(BUFFER_SIZE)
            logging.info(f'Socket received from {address}: {data.decode()}')
            save_json_data(data.decode())
    except Exception as e:
        logging.error(f'Socket server error: {e}')
    finally:
        socket_server.close()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(threadName)s - %(message)s')
    print(f"BASE_DIR = {BASE_DIR}")
    http_server = Thread(target=run_http_server, args=(HTTP_HOST, HTTP_PORT))
    http_server.start()

    socket_server = Thread(target=run_socket_server,
                           args=(SOCKET_HOST, SOCKET_PORT))
    socket_server.start()
