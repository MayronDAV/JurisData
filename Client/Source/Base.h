#pragma once
#include <format>
#include <iostream>

#ifdef _WIN32
    #include <Windows.h>
#else
    #include <codecvt>
    #include <locale>
#endif

namespace JD
{
    #ifndef JD_DISABLE_LOG
        #define LOG(...) std::cout << std::format(__VA_ARGS__) << "\n";
        #define LOG_WARN(...) std::cout << std::format("WARNING: " __VA_ARGS__) << "\n";
        #define LOG_ERROR(...) std::cerr << std::format("ERROR: " __VA_ARGS__) << "\n";
        #define LOG_FATAL(...) { std::cerr << std::format("FATAL: " __VA_ARGS__) << "\n"; std::abort(); }
    #else
        #define LOG(...) {}
        #define LOG_WARN(...) {}
        #define LOG_ERROR(...) {}
        #define LOG_FATAL(...) std::abort();
    #endif

    inline std::string WideToUTF8(const std::wstring& p_WideStr) 
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

    inline std::wstring UTF8ToWide(const std::string& p_Str)
    {
        #if defined(_WIN32)
            int wideStrLength = MultiByteToWideChar(CP_UTF8, 0, p_Str.c_str(), -1, nullptr, 0);
            if (wideStrLength == 0) return L"";
            
            std::wstring wideStr(wideStrLength, 0);
            MultiByteToWideChar(CP_UTF8, 0, p_Str.c_str(), -1, &wideStr[0], wideStrLength);
            
            return wideStr;
        #else
            std::wstring_convert<std::codecvt_utf8<wchar_t>> converter;
            return converter.from_bytes(p_Str);
        #endif
    }

    inline void ShowErrorWindow(const std::string& p_Title, const std::string& p_Message, bool p_Abort = false)
    {
        //TODO: Adaptar esse código para abrir uma janela de erro no Linux/Mac também
    #ifdef _WIN32
        auto message = UTF8ToWide(p_Message);
        auto title = UTF8ToWide(p_Title);
        MessageBoxW(nullptr, message.c_str(), title.c_str(), MB_OK | MB_ICONERROR);
    #endif

        if (p_Abort)
            LOG_FATAL("{}: {}", p_Title, p_Message)
        else
            LOG_ERROR("{}: {}", p_Title, p_Message);
    }

} // namespace JD