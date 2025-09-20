#include "Application.h"
#include "Base.h"



int main()
{
    #ifdef _WIN32
        #ifndef JD_DISABLE_LOG
            SetConsoleOutputCP(CP_UTF8);
            SetConsoleCP(CP_UTF8);
            
            // Enable Input UNICODE
            HANDLE h_stdin = GetStdHandle(STD_INPUT_HANDLE);
            DWORD mode;
            GetConsoleMode(h_stdin, &mode);
            SetConsoleMode(h_stdin, mode | ENABLE_VIRTUAL_TERMINAL_INPUT | ENABLE_PROCESSED_INPUT);
        #endif

        WSADATA wsaData;
        if (WSAStartup(MAKEWORD(2, 2), &wsaData) != 0) 
        {
            JD::ShowErrorWindow("WinSock Error", "Falha ao tentar iniciar o WinSock!", false);
            return 1;
        }
    #endif

    auto app = new JD::Application();
    app->Run();
    delete app;

    #if defined(_WIN32)
        WSACleanup();
    #endif

    return 0;
}