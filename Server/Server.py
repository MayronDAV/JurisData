import socket

class Server:
    def __init__(self, p_Host="localhost", p_Port=8082):
        self.ServerSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.ServerSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.ServerAddress = (p_Host, p_Port)
        self.DataPayload = 2048 # bytes
    
    def Start(self):
        self.ServerSocket.bind(self.ServerAddress)
        self.ServerSocket.listen(5)
        print(f"Server listening on {self.ServerAddress}")
        
        i = 0
        while True:
            print(f"Waiting to receive message from client")
            client_socket, client_address = self.ServerSocket.accept()
            data = client_socket.recv(self.DataPayload)
            if data:
                print("Received data: %s" %data)
                client_socket.send(data)
                print("send %s bytes back to %s" %(data, client_address))
                # end connection
                client_socket.close()
                i += 1
                if i >= 3: break

    def Stop(self):
        self.ServerSocket.close()
        print("Server stopped.")

if __name__ == "__main__":
    server = Server()
    server.Start()