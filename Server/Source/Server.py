import socket
import json
import time
import threading
from typing import Dict, Any, List, Optional
import sys
import tempfile, os
import multiprocessing
from multiprocessing import Queue, Process



try:
    from scrapy.crawler import CrawlerProcess
    from scrapy.utils.project import get_project_settings
    from scrapy import signals
except ImportError as e:
    print(f"[-] ERRO CRÍTICO: Scrapy não está instalado ou não pode ser importado: {e}")
    print("[-] Instale com: pip install scrapy twisted")
    sys.exit(1)

try:
    from ClassDiscoverer import ClassDiscovererSpider
except ImportError as e:
    print(f"[-] ERRO CRÍTICO: Não foi possível importar módulos do Scraper: {e}")
    sys.exit(1)



class ScrapyWorker:
    @staticmethod
    def RunScrapy(p_Url: str, p_ResultQueue: Queue):
        try:
            settings = get_project_settings()
            settings.set('LOG_ENABLED', False)
            settings.set('LOG_LEVEL', 'ERROR')
            process = CrawlerProcess(settings)

            results = []    
            def collect_results(item, response, spider):
                results.append(item)
            
            process.crawl(ClassDiscovererSpider, p_Url=p_Url)
            for crawler in list(process.crawlers):
                crawler.signals.connect(collect_results, signal=signals.item_scraped)

            process.start()

            if not results:
                raise Exception("Nenhum resultado coletado pelo Scrapy")
            
            if len(results).to_bytes() > bytes(4096):
                fd, temp_path = tempfile.mkstemp(suffix=".json")
                os.close(fd)
                with open(temp_path, "w", encoding="utf-8") as f:
                    json.dump(results[0], f, ensure_ascii=False)

                print(f"[+] Resultados muito grandes, salvos em arquivo temporário: {temp_path}")
                p_ResultQueue.put({'success': True, 'file': temp_path })
            else:
                p_ResultQueue.put({'success': True, 'data': results[0] })
            
        except Exception as e:
            p_ResultQueue.put({'success': False, 'error': str(e)})


class Server:
    def __init__(self, p_Host="localhost", p_Port=8082):
        self.ServerSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.ServerSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.ServerAddress = (p_Host, p_Port)
        self.DataPayload = 4096
        self.ShutdownCommand = "SHUTDOWN_SERVER"
        self.clients = []
        self.client_states = {}
        self.lock = threading.Lock()
    
    def CreateResponse(self, p_Type: str, p_Content: Any, p_Success: bool = True) -> Dict[str, Any]:
        return {
            "type": p_Type,
            "content": p_Content,
            "success": p_Success,
            "timestamp": time.time()
        }
    
    def ScrapeDiscoveryPhase(self, p_Url: str) -> Dict[str, Any]:
        print(f"[DISCOVERY] Analisando site: {p_Url}")
        
        result_queue = Queue()
        scrapy_process = Process(
            target=ScrapyWorker.RunScrapy,
            args=(p_Url, result_queue)
        )
        
        scrapy_process.start()
        scrapy_process.join(timeout=120)
        
        if scrapy_process.is_alive():
            scrapy_process.terminate()
            scrapy_process.join()
            raise Exception("Timeout no scraping (120 segundos)")
        
        if result_queue.empty():
            raise Exception("Nenhum resultado do processo de scraping")
        
        result = result_queue.get()
        
        if not result['success']:
            raise Exception(result.get('error', 'Erro desconhecido no scraping'))
        
        discovery_data = {}
        if 'file' in result:
            with open(result['file'], 'r', encoding='utf-8') as f:
                discovery_data = json.load(f)
            os.remove(result['file'])
        elif 'data' in result:
            discovery_data = result['data']
        else:
            raise Exception(result.get('error', 'Resultado de scraping inválido'))

        print(f"[DISCOVERY] Dados coletados: {len(discovery_data.get('classes', {}))} classes, {len(discovery_data.get('ids', {}))} ids")
        
        return {
            "url": p_Url,
            "available_classes": self.FormatScrapyResults(discovery_data),
            "scrapy_used": True,
            "success": True
        }
    
    def FormatScrapyResults(self, p_ScrapyData):
        formatted_classes = []
        
        if 'ids' in p_ScrapyData:
            for id_name, id_info in p_ScrapyData['ids'].items():
                formatted_classes.append({
                    "css_class": f"#{id_name}",
                    "example_content": id_info.get('text', '')[:200],
                    "tag_name": id_info.get('tag', ''),
                    "element_count": id_info.get('element_count', 1),
                    "suggested_xpath": id_info.get('xpath', '')
                })

        if 'classes' in p_ScrapyData:
            for class_name, class_info in p_ScrapyData['classes'].items():
                formatted_classes.append({
                    "css_class": class_name,
                    "example_content": class_info.get('text', '')[:200],
                    "tag_name": class_info.get('tag', ''),
                    "element_count": class_info.get('element_count', 1),
                    "suggested_xpath": class_info.get('xpath', '')
                })
        
        return formatted_classes

    def ScrapeTargetedPhase(self, p_Url: str, p_Targets: Optional[List[str]] = None, p_XPathSelectors: Optional[List[str]] = None) -> Dict[str, Any]:
        print(f"[TARGETED] Extraindo conteúdo de: {p_Url}")
        print(f"Classes alvo: {p_Targets}")
        print(f"XPaths alvo: {p_XPathSelectors}")
        
        time.sleep(2)
        
        results = []
        if p_Targets:
            for css_class in p_Targets:
                results.append({
                    "css_class": css_class,
                    "content": [
                        f"Conteúdo real 1 da classe {css_class}",
                        f"Conteúdo real 2 da classe {css_class}",
                        f"Conteúdo real 3 da classe {css_class}"
                    ],
                    "items_found": 3
                })
        
        return {
            "url": p_Url,
            "results": results,
            "total_items": len(results) * 3,
            "scrape_timestamp": time.time(),
            "scrapy_used": False
        }
    
    def HandleScrapeRequest(self, p_Client, p_JsonData: Dict[str, Any]) -> None:
        url = p_JsonData.get('url')
        if not url:
            response = self.CreateResponse("error", "URL não fornecida", False)
            p_Client.send(json.dumps(response).encode('utf-8'))
            return
        
        target_classes = p_JsonData.get('target_classes')
        xpath_selectors = p_JsonData.get('xpath_selectors')
        
        try:
            if not target_classes and not xpath_selectors:
                print(f"[+] Iniciando fase de discovery para: {url}")
                discovery_results = self.ScrapeDiscoveryPhase(url)
                
                with self.lock:
                    client_addr = p_Client.getpeername()
                    self.client_states[client_addr] = {
                        'url': url,
                        'phase': 'awaiting_selection',
                        'discovery_data': discovery_results
                    }
                
                response = self.CreateResponse("discovery_results", discovery_results)
                print(f"[+] Discovery concluído para {url}")
                
            else:
                print(f"[+] Iniciando scraping direcionado para: {url}")
                scrape_results = self.ScrapeTargetedPhase(url, target_classes, xpath_selectors)
                
                response = self.CreateResponse("scrape_results", scrape_results)
                print(f"[+] Scraping direcionado concluído para {url}")
                
                with self.lock:
                    client_addr = p_Client.getpeername()
                    if client_addr in self.client_states:
                        del self.client_states[client_addr]
            
            p_Client.send(json.dumps(response).encode('utf-8'))
            
        except Exception as e:
            error_msg = f"Erro durante scraping: {str(e)}"
            print(f"[-] {error_msg}")
            response = self.CreateResponse("error", error_msg, False)
            p_Client.send(json.dumps(response).encode('utf-8'))
    
    def HandleClient(self, p_ClientSocket, p_ClientAddress):
        print(f"[+] Conexão estabelecida com {p_ClientAddress}")
        
        try:
            while True:
                data = p_ClientSocket.recv(self.DataPayload)
                if not data:
                    break
                
                try:
                    json_data = json.loads(data.decode('utf-8'))
                    print(f"[+] Recebido: {json_data}")

                    if json_data.get('type') == 'command' and json_data.get('content') == 'shutdown':
                        print("[-] Shutdown command received")
                        response = self.CreateResponse("command", "shutdown")
                        p_ClientSocket.send(json.dumps(response).encode('utf-8'))
                        break
                    
                    elif json_data.get('type') == 'scrape_request':
                        self.HandleScrapeRequest(p_ClientSocket, json_data)
                    
                    elif json_data.get('type') == 'class_selection':
                        with self.lock:
                            client_addr = p_ClientSocket.getpeername()
                            client_state = self.client_states.get(client_addr, {})
                        
                        if client_state.get('phase') == 'awaiting_selection':
                            selected_classes = json_data.get('selected_classes', [])
                            selected_xpaths = json_data.get('selected_xpaths', [])
                            
                            if not selected_classes and not selected_xpaths:
                                response = self.CreateResponse("error", "Nenhuma classe ou XPath selecionado", False)
                                p_ClientSocket.send(json.dumps(response).encode('utf-8'))
                                continue
                            
                            scrape_results = self.ScrapeTargetedPhase(
                                client_state['url'], 
                                selected_classes, 
                                selected_xpaths
                            )
                            
                            response = self.CreateResponse("scrape_results", scrape_results)
                            p_ClientSocket.send(json.dumps(response).encode('utf-8'))

                            with self.lock:
                                if client_addr in self.client_states:
                                    del self.client_states[client_addr]
                        else:
                            response = self.CreateResponse("error", "Estado inválido para seleção de classes", False)
                            p_ClientSocket.send(json.dumps(response).encode('utf-8'))
                    
                    elif json_data.get('type') == 'message':
                        message_content = json_data.get('content', '')
                        print(f"Cliente {p_ClientAddress}: {message_content}")
                        
                        response = self.CreateResponse("message", "Mensagem recebida")
                        p_ClientSocket.send(json.dumps(response).encode('utf-8'))
                        
                except json.JSONDecodeError:
                    message = data.decode('utf-8')
                    print(f"Cliente {p_ClientAddress} (non-JSON): {message}")
                    
                    if message == self.ShutdownCommand:
                        break
                    
                    response = self.CreateResponse("message", "Comando não-JSON recebido")
                    p_ClientSocket.send(json.dumps(response).encode('utf-8'))
                    
        except Exception as e:
            print(f"[-] Erro com cliente {p_ClientAddress}: {e}")
        finally:
            with self.lock:
                client_addr = p_ClientSocket.getpeername()
                if client_addr in self.client_states:
                    del self.client_states[client_addr]
                if p_ClientSocket in self.clients:
                    self.clients.remove(p_ClientSocket)
            
            p_ClientSocket.close()
            print(f"[-] Conexão com {p_ClientAddress} fechada")
    
    def Start(self):
        self.ServerSocket.bind(self.ServerAddress)
        self.ServerSocket.listen(5)
        print(f"[+] Servidor ouvindo em {self.ServerAddress}")
        print("[+] Digite 'exit' para parar o servidor.")
        
        def MonitorExit():
            while True:
                command = input()
                if command.lower() == 'exit':
                    print("[-] Desligando servidor...")
                    with self.lock:
                        for client in self.clients:
                            try:
                                shutdown_msg = self.CreateResponse("system", "Servidor está sendo desligado")
                                client.send(json.dumps(shutdown_msg).encode('utf-8'))
                                client.close()
                            except:
                                pass
                    self.ServerSocket.close()
                    break
        
        exit_thread = threading.Thread(target=MonitorExit, daemon=True)
        exit_thread.start()
        
        try:
            while True:
                client_socket, client_address = self.ServerSocket.accept()
                
                with self.lock:
                    self.clients.append(client_socket)
                
                client_thread = threading.Thread(
                    target=self.HandleClient,
                    args=(client_socket, client_address),
                    daemon=True
                )
                client_thread.start()
                
        except OSError:
            pass
        except Exception as e:
            print(f"[-] Erro no servidor: {e}")
        finally:
            self.Stop()
    
    def Stop(self):
        with self.lock:
            for client in self.clients:
                try:
                    client.close()
                except:
                    pass
        
        self.ServerSocket.close()
        print("[-] Servidor parado")

def main():
    if sys.platform.startswith('win'):
        multiprocessing.freeze_support()

    server = Server()
    try:
        server.Start()
    except KeyboardInterrupt:
        print("\n[-] Servidor interrompido pelo usuário.")
    finally:
        server.Stop()

if __name__ == "__main__":
    main()