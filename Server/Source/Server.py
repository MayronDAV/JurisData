import socket
import json
import os
import time
import threading
from typing import Dict, Any
import sys
import multiprocessing
import asyncio

try:
    from playwright.async_api import async_playwright
except ImportError as e:
    print(f"[-] Playwright não disponível: {e}")
    sys.exit(1)

try:
    from Worker import PlaywrightWorker
except ImportError as e:
    print(f"[-] Falha ao importar Worker: {e}")
    sys.exit(1)

try:
    from ParserEngine import ParserEngine
except ImportError as e:
    print(f"[-] Falha ao importar ParserEngine: {e}")
    sys.exit(1)




def load_config():
    try:
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))
        
        json_path = os.path.join(base_path, 'Config.json')
        
        with open(json_path, 'r', encoding='utf-8') as arquivo:
            return json.load(arquivo)
            
    except FileNotFoundError:
        print(f"Arquivo de Config não encontrado em: {json_path}")
        return {}
    except json.JSONDecodeError:
        print("Erro ao decodificar o JSON de config")
        return {}


class Server:
    def __init__(self, host="localhost", port=8082):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_addr = (host, port)
        self.data_payload = 10240
        self.clients = []
        self.lock = threading.Lock()
        self.shutdown_cmd = "SHUTDOWN_SERVER"
        self.config = load_config();

    def create_response(self, type: str, content: Any, success: bool = True) -> Dict[str, Any]:
        return {"type": type, "content": content, "success": success, "timestamp": time.time()}

    def handle_request(self, client, json_data: Dict[str, Any]) -> None:
        try:
            site_cfg = self.config["sites"]["TJRJ"]

            worker = PlaywrightWorker(site_cfg)
            pages_html = asyncio.run(worker.execute(json_data["search_term"]))

            parser = ParserEngine(site_cfg)
            parsed = asyncio.run(parser.parse(pages_html))

            response = self.create_response("finished", {
                site_cfg["url"]: parsed
            })

            client.send(json.dumps(response, default=str).encode('utf-8'))

        except Exception as e:
            print(f"[-] Erro no handle_request: {e}")
            response = self.create_response("error", str(e), False)
            try:
                client.send(json.dumps(response).encode('utf-8'))
            except:
                pass
    
    def handle_client(self, client_socket, client_addr):
        print(f"[+] Conexão estabelecida com {client_addr}")
        
        try:
            while True:
                data = client_socket.recv(self.data_payload)
                if not data:
                    break
                
                try:
                    json_data = json.loads(data.decode('utf-8'))
                    print(f"[+] Recebido comando: {json_data.get('type')}")

                    if json_data.get('type') == 'command' and json_data.get('content') == self.shutdown_cmd:
                        print("[-] Shutdown command received")
                        response = self.create_response("command", self.shutdown_cmd)
                        client_socket.send(json.dumps(response).encode('utf-8'))
                        break           
                    elif json_data.get('type') == 'scrape_request':
                        self.handle_request(client_socket, json_data)
                    else:
                        response = self.create_response("error", "Comando desconhecido", False)
                        client_socket.send(json.dumps(response).encode('utf-8'))

                except json.JSONDecodeError as e:
                    message = data.decode('utf-8', errors='ignore')
                    print(f"[-] JSON decode error from {client_addr}: {e}")
                    
                    if message == self.shutdown_cmd:
                        break
                    
                    response = self.create_response("error", "JSON inválido", False)
                    client_socket.send(json.dumps(response).encode('utf-8'))
                    
        except Exception as e:
            print(f"[-] Erro com cliente {client_addr}: {e}")
        finally:
            with self.lock:
                if client_socket in self.clients:
                    self.clients.remove(client_socket)
            
            client_socket.close()
            print(f"[-] Conexão com {client_addr} fechada")
    
    def start(self):
        self.server_socket.bind(self.server_addr)
        self.server_socket.listen(5)
        print(f"[+] Servidor ouvindo em {self.server_addr}")
        print("[+] Digite 'exit' para parar o servidor.")
       
        threading.Thread(target=self.monitor_exit, daemon=True).start()
        
        while True:
            try:
                client_socket, client_addr = self.server_socket.accept()            
                with self.lock:
                    self.clients.append(client_socket)
                
                threading.Thread(
                    target=self.handle_client, 
                    args=(client_socket, client_addr), 
                    daemon=True
                ).start()
            except OSError:
                break  # Socket fechado

    def monitor_exit(self):
        while True:
            try:
                cmd = input().strip()
                if cmd.lower() == "exit":
                    print("[-] Desligando servidor...")
                    self.stop()
                    break
            except (EOFError, KeyboardInterrupt):
                break

    def stop(self):
        with self.lock:
            for client in self.clients:
                try:
                    shutdown_msg = self.create_response("system", self.shutdown_cmd)
                    client.send(json.dumps(shutdown_msg).encode('utf-8'))
                    client.close()
                except:
                    pass
            self.clients.clear()
        
        try:
            self.server_socket.close()
        except:
            pass

def main():
    if sys.platform.startswith('win'):
        multiprocessing.freeze_support()

    server = Server()
    try:
        server.start()
    except KeyboardInterrupt:
        print("\n[-] Servidor interrompido pelo usuário.")
    except Exception as e:
        print(f"[-] Erro no servidor: {e}")
    finally:
        server.stop()
        print("[-] Servidor desligado")

if __name__ == "__main__":
    main()