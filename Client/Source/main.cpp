#include <iostream>
#include <string>
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
            buffer[chars_read - 2] = L'\0'; // Remove \r\n
            input = buffer;
        }
    #else
        std::string temp;
        std::getline(std::cin, temp);
        input = std::wstring(temp.begin(), temp.end());
    #endif
    
    return input;
}

std::string WideToUTF8(const std::wstring& p_WideStr) 
{
    #if defined(_WIN32)
        int utf8_size = WideCharToMultiByte(CP_UTF8, 0, p_WideStr.c_str(), -1, nullptr, 0, nullptr, nullptr);
        if (utf8_size == 0) return "";
        
        std::string utf8_str(utf8_size, '\0');
        WideCharToMultiByte(CP_UTF8, 0, p_WideStr.c_str(), -1, &utf8_str[0], utf8_size, nullptr, nullptr);
        
        return utf8_str.substr(0, utf8_size - 1);
    #else
        std::wstring_convert<std::codecvt_utf8<wchar_t>> converter;
        return converter.to_bytes(wide_str);
    #endif
}

int main() 
{
    #if defined(_WIN32)
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

    const char* shutdownCommand = "SHUTDOWN_SERVER";
    while (true)
    {
        std::cout << "You: ";
        
        std::wstring wide_input = GetUnicodeInput();
        std::string input(wide_input.begin(), wide_input.end());
        
        if (input == "exit") 
        {
            send(clientSocket, shutdownCommand, strlen(shutdownCommand), 0);
            break;
        }

        std::string utf8_message = WideToUTF8(wide_input);

        int sent = send(clientSocket, utf8_message.c_str(), utf8_message.size(), 0);
        if (sent <= 0) 
        {
            std::cerr << "Failed to send message or connection closed." << std::endl;
            break;
        }

        int bytesReceived = recv(clientSocket, buffer, sizeof(buffer) - 1, 0);
        if (bytesReceived <= 0) 
        {
            std::cerr << "Server disconnected or error receiving data." << std::endl;
            break;
        }    
        buffer[bytesReceived] = '\0';

        if (memcmp(buffer, shutdownCommand, sizeof(shutdownCommand)) == 0)
        {
            std::cout << "Server is shutting down." << std::endl;
            break;
        }

        std::cout << "Server: " << buffer << std::endl;
    }

    close(clientSocket);

    #if defined(_WIN32)
        WSACleanup();
    #endif

    return 0;
}