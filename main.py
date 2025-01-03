from http.server import HTTPServer, BaseHTTPRequestHandler
import logging
import os
import socket
import urllib.parse
import multiprocessing
from datetime import datetime
from pymongo import MongoClient

# Конфігурація
SOCKET_SERVER_HOST = '0.0.0.0'
SOCKET_SERVER_PORT = 5000
HTTP_SERVER_PORT = 3000
MONGO_URI = 'mongodb://mongo:27017/'
DATABASE_NAME = 'webapp'
COLLECTION_NAME = 'messages'

# HTTP-сервер
class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/' or self.path == '/index.html':
            self.serve_file('templates/index.html', 'text/html')
        elif self.path == '/message.html':
            self.serve_file('templates/message.html', 'text/html')
        elif self.path.startswith('/static/'):
            self.serve_static_file()
        else:
            self.serve_file('templates/error.html', 'text/html', 404)

    def do_POST(self):
        if self.path == '/message':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            post_params = urllib.parse.parse_qs(post_data.decode())

            # Надсилаємо дані сокет-серверу
            self.send_to_socket_server(post_params)

            # Перенаправлення на головну сторінку
            self.send_response(302)
            self.send_header('Location', '/index.html')
            self.end_headers()
        else:
            self.serve_file('templates/error.html', 'text/html', 404)

    def serve_file(self, filepath, content_type, status_code=200):
        try:
            with open(filepath, 'rb') as file:
                self.send_response(status_code)
                self.send_header('Content-type', content_type)
                self.end_headers()
                self.wfile.write(file.read())
        except FileNotFoundError:
            self.serve_file('templates/error.html', 'text/html', 404)

    def serve_static_file(self):
        static_file_path = self.path.lstrip('/')
        if os.path.exists(static_file_path):
            mime_type = 'text/css' if static_file_path.endswith('.css') else 'image/png'
            self.serve_file(static_file_path, mime_type)
        else:
            self.serve_file('templates/error.html', 'text/html', 404)

    def send_to_socket_server(self, data):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((SOCKET_SERVER_HOST, SOCKET_SERVER_PORT))
            sock.sendall(str(data).encode('utf-8'))


def run_http_server():
    httpd = HTTPServer(('0.0.0.0', HTTP_SERVER_PORT), SimpleHTTPRequestHandler)
    print(f"HTTP сервер запущено на порті {HTTP_SERVER_PORT}")
    httpd.serve_forever()


# Socket-сервер
def save_to_database(data):
    client = MongoClient(MONGO_URI)
    db = client.webapp
    collection = db.messages
    try:
        collection.insert_one(data)
    except ValueError as err:
        logging.error(f'Failed to parse data: {err}')
    except Exception as err:
        logging.error(f'Failed to write or read data: {err}')
    finally:
        client.close()


def run_socket_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((SOCKET_SERVER_HOST, SOCKET_SERVER_PORT))
    server_socket.listen(5)
    print(f"Socket сервер запущено на порті {SOCKET_SERVER_PORT}")

    while True:
        client_socket, client_address = server_socket.accept()
        print(f"Отримано з'єднання від {client_address}")
        data = client_socket.recv(1024)
        if data:
            message = eval(data.decode('utf-8'))
            message['date'] = datetime.now()
            save_to_database(message)
            print(f"Збережено повідомлення: {message}")
        client_socket.close()


if __name__ == '__main__':
    # Запуск серверів у різних процесах
    http_process = multiprocessing.Process(target=run_http_server)
    socket_process = multiprocessing.Process(target=run_socket_server)

    http_process.start()
    socket_process.start()

    http_process.join()
    socket_process.join()