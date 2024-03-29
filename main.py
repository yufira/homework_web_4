import urllib.parse
import mimetypes
import logging
import socket
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from threading import Thread
from datetime import datetime


SOCKET_HOST = '127.0.0.1'
SOCKET_PORT = 5000
HTTP_PORT = 3000
HTTP_HOST = '0.0.0.0'


class HttpGetHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        size = self.headers.get('Content-Length')
        data = self.rfile.read(int(size))

        client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        client_socket.sendto(data, (SOCKET_HOST, SOCKET_PORT))
        client_socket.close()

        self.send_response(302)
        self.send_header('Location', '/')
        self.end_headers()
        
    def do_GET(self):
        url = urllib.parse.urlparse(self.path)
        match url.path:
            case '/':
                self.send_html("index.html")
            #case '/contacts':
                #self.send_html("contacts.html")
            case '/message':
                self.send_html("message.html")
            case _:
                file_path = Path(url.path[1:])
                if file_path.exists():
                    self.send_static(str(file_path))
                else:
                    self.send_html("error.html", 404)
                
    def send_static(self, static_filename):
        self.send_response(200)
        mt = mimetypes.guess_type(self.path)
        # print(f"{mt = }")
        if mt:
            self.send_header('Content-type', mt[0])
        else:
            self.send_header('Content-type', 'text/plain')
        self.end_headers()
        with open(static_filename, 'rb') as f:
            self.wfile.write(f.read())

    def send_html(self, html_filename, status=200):
        self.send_response(status)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        with open(html_filename, 'rb') as f:
            self.wfile.write(f.read())

def save_data_to_json(data):
    parse_data = urllib.parse.unquote_plus(data.decode())
    parse_dict = {key: value for key, value in [el.split("=") for el in parse_data.split("&")]}
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
    data_to_save = {
        timestamp: parse_dict
    }
    with open("storage/data.json", "a", encoding="utf-8") as f:
        if f.tell() != 0:
            f.write("\n")
        json.dump(data_to_save, f, ensure_ascii=False, indent=4)
        f.write("\n")


def run_http_server(host, port):
    address = (host, port)
    http_server = HTTPServer(address, HttpGetHandler)
    logging.info("Starting http server")
    try:
        http_server.serve_forever()
    except KeyboardInterrupt:
        http_server.server_close()


def run_socket_server(host, port):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind((host, port))
    logging.info("Starting socket server")
    try:
        while True:
            msg, address = server_socket.recvfrom(1024)
            logging.info(f"Socket received {address}: {msg}")
            save_data_to_json(msg)
    except KeyboardInterrupt:
        pass
    finally:
        server_socket.close()


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='%(threadName)s %(message)s')

    server = Thread(target=run_http_server, args=(HTTP_HOST, HTTP_PORT))
    server.start()

    server_socket = Thread(target=run_socket_server, args=(SOCKET_HOST, SOCKET_PORT))
    server_socket.start()