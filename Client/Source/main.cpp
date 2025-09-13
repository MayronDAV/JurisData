#include <iostream>
#if defined(_WIN32)
    #include <ws2tcpip.h>
    #include <sys/types.h>
    #define close closesocket
#else
    #include <netinet/in.h>
    #include <sys/socket.h>
#endif

int main() 
{
    #if defined(_WIN32)
        WSADATA wsaData;
        if (WSAStartup(MAKEWORD(2, 2), &wsaData) != 0) {
            std::cerr << "Failed to initialize WinSock" << std::endl;
            return 1;
        }
    #endif

    int clientSocket = socket(AF_INET, SOCK_STREAM, 0);
    if (clientSocket == -1) {
        std::cerr << "Failed to create socket!" << std::endl;
        return 1;
    }

    sockaddr_in serverAddress;
    serverAddress.sin_family = AF_INET;
    serverAddress.sin_port = htons(8082); // Server Port
    serverAddress.sin_addr.s_addr = inet_addr("127.0.0.1");
    inet_pton(AF_INET, "127.0.0.1", &serverAddress.sin_addr);

    if (connect(clientSocket, (struct sockaddr*)&serverAddress, sizeof(serverAddress)) == -1) 
    {
        std::cerr << "Failed to connect!" << std::endl;
        close(clientSocket);
        return 1;
    }

    const char* message = "Hello, server!";
    send(clientSocket, message, strlen(message), 0);

    char* buffer = new char[2048];
    int bytesReceived = recv(clientSocket, buffer, 2048, 0);
    if (bytesReceived > 0) {
        buffer[bytesReceived] = '\0';
        std::cout << "Received from server: " << buffer << std::endl;
    }

    close(clientSocket);
    delete[] buffer;

    #if defined(_WIN32)
        WSACleanup();
    #endif

    return 0;
}