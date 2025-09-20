#pragma once
#include "Window.h"

// lib
#include <nlohmann/json.hpp>

// std
#include <mutex>

using json = nlohmann::json;



namespace JD
{
    struct ClassInfo 
    {
        std::string CssClass;
        std::string ExampleContent;
        std::string TagName;
        int ElementCount;
        std::string SuggestedXPath;
    };

    class Application
    {
        public:
            Application();
            ~Application();
    
            void Run();
            Window& GetWindow() { return *m_Window; }

            static Application& Get() { return *s_Instance; }

        private:
            void ResetSearch();

            void DrawUI();
            void DrawResultsUI();
            void DrawLoadingSpinner();

            bool SendRequest(const json& p_Request);
            json ReceiveResponse();
            void DiscoverClasses(const std::string& p_URL);

        private:
            bool m_SearchPerformed = false;
            std::string m_LinkToScrape = "";
            Window* m_Window = nullptr;

            int m_Socket = -1;
            json m_ServerResponse = {};
            std::mutex m_DataMutex;
            std::vector<ClassInfo> m_AvailableClasses;

            static inline Application* s_Instance = nullptr;
    };
    
} // namespace JD
