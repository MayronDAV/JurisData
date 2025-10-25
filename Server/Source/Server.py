import socket
import json
import os
import time
import threading
from typing import Dict, Any
import sys
import multiprocessing
import asyncio
import logging

try: 
    from twisted.internet import asyncioreactor

    if hasattr(asyncio, "WindowsSelectorEventLoopPolicy"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    asyncioreactor.install()

    from twisted.internet import defer, reactor
    from scrapy.crawler import CrawlerRunner
    from scrapy.utils.project import get_project_settings
    from scrapy import signals
except ImportError as e:
    print(f"[-] Scrapy/Twisted não disponíveis: {e}")
    sys.exit(1)

try:
    from Spider import Spider
except ImportError as e:
    print(f"[-] Falha ao importar Spider: {e}")
    sys.exit(1)



DEFAULT_MAX_SPIDERS = 5


class ScrapyWorker:
    def __init__(self, request, config, conn=None):
        self.config = config
        self.request = request
        self.conn = conn
        self.sites = config.get("sites", {})

        logging.basicConfig(
            level=logging.ERROR,
            format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        self.settings = {
            'CONCURRENT_REQUESTS': 1,
            'DOWNLOAD_DELAY': 1,
            'AUTOTHROTTLE_ENABLED': True,
            
            # Desabilita o logging do Scrapy para usar o nosso
            'LOG_ENABLED': False,
            
            # Playwright
            'DOWNLOAD_HANDLERS': {
                "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
                "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
            },
            'TWISTED_REACTOR': "twisted.internet.asyncioreactor.AsyncioSelectorReactor",
            'PLAYWRIGHT_BROWSER_TYPE': "chromium",
            'PLAYWRIGHT_LAUNCH_OPTIONS': {
                "headless": True,
                "timeout": 30 * 1000,
            },
        }

        self.runner = CrawlerRunner(self.settings)
        self.max_spiders = config.get("settings", {}).get("max_spiders", DEFAULT_MAX_SPIDERS)
        self.semaphore = defer.DeferredSemaphore(tokens=self.max_spiders)
        self.collected_data = {}

        print(f"[ScrapyWorker] Máximo de spiders simultâneas: {self.max_spiders}")

    @defer.inlineCallbacks
    def crawl_site(self, url, site_conf, search_term):
        yield self.semaphore.acquire()
        site_data = {}
        try:
            print(f"[Spider] Iniciando scrape de {url}")

            spider_config = {
                "sites": {url: site_conf},
                "settings": self.config.get("settings", {}),
            }

            crawler = self.runner.create_crawler(Spider)

            def collect_results(item, response, spider):
                if isinstance(item, dict):
                    for key, value in item.items():
                        if value is not None:
                            if key in site_data:
                                if not isinstance(site_data[key], list):
                                    site_data[key] = [site_data[key]]
                                site_data[key].append(value)
                            else:
                                site_data[key] = value

            crawler.signals.connect(collect_results, signal=signals.item_scraped)

            yield crawler.crawl(start_urls=[url], config=spider_config, search_term=search_term)

            self.collected_data[url] = site_data
            print(f"[Spider] Concluído scrape de {url}: {len(site_data)} campos coletados")

        except Exception as e:
            print(f"[Spider] Erro em {url}: {e}")
            self.collected_data[url] = {}
        finally:
            self.semaphore.release()



    @defer.inlineCallbacks
    def crawl_all_sites(self):
        if not self.sites:
            print("[ScrapyWorker] Nenhum site configurado.")
            if self.conn:
                self.conn.send({})
                self.conn.close()
            return


        search_term = self.request.get("search_term", "")
        tasks = [self.crawl_site(url, conf, search_term) for url, conf in self.sites.items()]
        print(f"[ScrapyWorker] Executando {len(tasks)} spiders (máx {self.max_spiders})")
        yield defer.DeferredList(tasks, consumeErrors=True)

        print(f"[ScrapyWorker] Todas concluídas. Total de sites processados: {len(self.collected_data)}")
        if self.conn:
            time.sleep(0.2)
            self.conn.send(self.collected_data)
            self.conn.close()

def start_scrapy_worker(request, config, conn=None):
    try:
        worker = ScrapyWorker(request, config, conn)
        d = worker.crawl_all_sites()

        def _on_done(_):
            reactor.callFromThread(reactor.stop)

        d.addBoth(_on_done)

        if not reactor.running:
            reactor.run(installSignalHandlers=False)
    except Exception as e:
        print(f"[-] Erro no worker: {e}")
        if conn:
            conn.send({"error": str(e)})
            conn.close()




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

    def process_scrape(self, client, request):
        try:
            parent_conn, child_conn = multiprocessing.Pipe()
            p = multiprocessing.Process(
                target=start_scrapy_worker, 
                args=(request, self.config, child_conn)
            )
            p.start()

            if parent_conn.poll(300):  # 5 minutos timeout
                scraped_data = parent_conn.recv()
            else:
                scraped_data = {"error": "Timeout no scraping"}
                p.terminate()

            p.join(timeout=30)
            if p.is_alive():
                p.terminate()
                p.join()

            response = self.create_response("finished", scraped_data)
            client.send(json.dumps(response, default=str).encode('utf-8'))

        except Exception as e:
            print(f"[-] Erro no process_scrape: {e}")
            err = self.create_response("error", str(e), False)
            try:
                client.send(json.dumps(err).encode('utf-8'))
            except:
                pass

    def handle_request(self, client, json_data: Dict[str, Any]) -> None:
        try:
            thread = threading.Thread(
                target=self.process_scrape, 
                args=(client, json_data),
                daemon=True
            )
            thread.start()
            
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