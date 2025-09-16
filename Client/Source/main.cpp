#include "Application.h"
#include "Base.h"

#if 0
#include <iostream>
#include <string>
#include <nlohmann/json.hpp>
#if defined(_WIN32)
    #include <WinSock2.h>
    #include <WS2tcpip.h>
    #define close closesocket
#else
    #include <netinet/in.h>
    #include <sys/socket.h>
    #include <unistd.h>
    #include <arpa/inet.h>
#endif

using json = nlohmann::json;

std::wstring GetUnicodeInput() 
{
    std::wstring input;
    
    #if defined(_WIN32)
        const int buffer_size = 1024;
        wchar_t buffer[buffer_size];
        
        DWORD chars_read;
        HANDLE h_stdin = GetStdHandle(STD_INPUT_HANDLE);
        
        if (ReadConsoleW(h_stdin, buffer, buffer_size - 1, &chars_read, nullptr)) 
        {
            buffer[chars_read - 2] = L'\0';
            input = buffer;
        }
    #else
        std::string temp;
        std::getline(std::cin, temp);
        input = std::wstring(temp.begin(), temp.end());
    #endif
    
    return input;
}

json CreateMessage(const std::string& p_Type, const std::string& p_Content) 
{
    return {
        {"type", p_Type},
        {"content", p_Content},
        {"timestamp", std::time(nullptr)}
    };
}
#endif

int main()
{
    #if defined(_WIN32) && !defined(JD_DISABLE_LOG)
        SetConsoleOutputCP(CP_UTF8);
        SetConsoleCP(CP_UTF8);
        
        // Enable Input UNICODE
        HANDLE h_stdin = GetStdHandle(STD_INPUT_HANDLE);
        DWORD mode;
        GetConsoleMode(h_stdin, &mode);
        SetConsoleMode(h_stdin, mode | ENABLE_VIRTUAL_TERMINAL_INPUT | ENABLE_PROCESSED_INPUT);
        
        WSADATA wsaData;
        if (WSAStartup(MAKEWORD(2, 2), &wsaData) != 0) {
            std::cerr << "Failed to initialize WinSock" << std::endl;
            return 1;
        }
    #endif

#if 1
    auto app = new JD::Application();
    app->Run();
    delete app;

    JD::ShowErrorWindow("Teste", "Isso é um teste", false);
#else
    int clientSocket = socket(AF_INET, SOCK_STREAM, 0);
    if (clientSocket == -1) {
        std::cerr << "Failed to create socket!" << std::endl;
        return 1;
    }

    sockaddr_in serverAddress;
    serverAddress.sin_family = AF_INET;
    serverAddress.sin_port = htons(8082);
    serverAddress.sin_addr.s_addr = inet_addr("127.0.0.1");

    if (connect(clientSocket, (struct sockaddr*)&serverAddress, sizeof(serverAddress)) == -1) 
    {
        std::cerr << "Failed to connect!" << std::endl;
        close(clientSocket);
        return 1;
    }
    
    std::cout << "Connected to server!" << std::endl;
    std::cout << "Type 'exit' to quit." << std::endl;

    char buffer[2048];

    while (true)
    {
        std::cout << "You: ";
        
        std::wstring wide_input = GetUnicodeInput();
        std::string input(wide_input.begin(), wide_input.end());
        
        if (input == "exit") 
        {
            json shutdown_msg = CreateMessage("command", "shutdown");
            std::string json_str = shutdown_msg.dump();
            
            send(clientSocket, json_str.c_str(), json_str.size(), 0);
            break;
        }

        json message = CreateMessage("message", WideToUTF8(wide_input));
        std::string json_str = message.dump();
        
        std::cout << "Sending JSON: " << json_str << std::endl;

        int sent = send(clientSocket, json_str.c_str(), json_str.size(), 0);
        if (sent <= 0) 
        {
            std::cerr << "Failed to send message." << std::endl;
            break;
        }

        int bytesReceived = recv(clientSocket, buffer, sizeof(buffer) - 1, 0);
        if (bytesReceived <= 0) 
        {
            std::cerr << "Server disconnected." << std::endl;
            break;
        }
        
        buffer[bytesReceived] = '\0';
        std::string response_str(buffer);
        
        try
        {
            json response_json = json::parse(response_str);
            
            if (response_json.contains("type") && response_json["type"] == "command") 
            {
                if (response_json["content"] == "shutdown") 
                {
                    std::cout << "Server is shutting down." << std::endl;
                    break;
                }
            }
            else if (response_json.contains("content")) 
                std::cout << "Server: " << response_json["content"].get<std::string>() << std::endl;
            else
                std::cout << "Server: " << response_str << std::endl;
        }
        catch (const std::exception& e) 
        {
            std::cout << "Server (non-JSON): " << response_str << std::endl;
        }
    }

    close(clientSocket);

    #if defined(_WIN32)
        WSACleanup();
    #endif

#endif
    return 0;
}