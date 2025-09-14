import socket

class Server:
    def __init__(self, p_Host="localhost", p_Port=8082):
        self.ServerSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.ServerSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.ServerAddress = (p_Host, p_Port)
        self.DataPayload = 2048
        self.ShutdownCommand = "SHUTDOWN_SERVER"
    
    def Start(self):
        self.ServerSocket.bind(self.ServerAddress)
        self.ServerSocket.listen()
        print(f"Server listening on {self.ServerAddress}")
        print("Type 'exit' to stop the server.")

        while True:
            client_socket, client_address = self.ServerSocket.accept()
            print(f"Connection from {client_address} has been established!")
            
            while True:
                try:
                    data = client_socket.recv(self.DataPayload)
                    if not data:
                        break
                    
                    message = data.decode('utf-8')
                    
                    if message == self.ShutdownCommand:
                        print("Shutdown command received. Stopping server.")
                        break
                    
                    print(f"Client: {message}")
                    
                    server_message = input("You: ")
                    if server_message.lower() == "exit":
                        print("Closing connection with client.")
                        client_socket.send(self.ShutdownCommand.encode('utf-8'))
                        break
                    
                    client_socket.send(server_message.encode('utf-8'))
                    
                except Exception as e:
                    print(f"Error: {e}")
                    break
            
            client_socket.close()
            print(f"Connection with {client_address} closed.")
            break

    def Stop(self):
        self.ServerSocket.close()
        print("Server stopped.")

if __name__ == "__main__":
    server = Server()
    try:
        server.Start()
    except KeyboardInterrupt:
        print("\nServer interrupted by user.")
    finally:
        server.Stop()