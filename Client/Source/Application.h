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
        bool IsLink = false;
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
            void DrawConfigLink();

            json ResolveConfig(const std::string& p_Link);
            std::string NormalizeURL(const std::string& p_URL);

            bool SendRequest(const json& p_Request);
            json ReceiveResponse();
            bool IsCompleteJson(const std::string& p_JsonStr);
            void DiscoverClasses(const std::string& p_URL);
            void SaveLinkConfigs();

        private:
            bool m_SearchPerformed = false;
            std::string m_LinkToScrape = "";
            Window* m_Window = nullptr;

            std::string m_SimilarConfigLink  = "";
            bool m_HasSimilarConfig = false;

            int m_Socket = -1;
            json m_ServerResponse = {};
            json m_LinkConfigs = {};
            json m_CurrentLinkConfig = {};
            bool m_ConfigLink = false;
            std::mutex m_DataMutex;
            std::vector<ClassInfo> m_Classes;
            std::vector<ClassInfo> m_OtherDatas;

            static inline Application* s_Instance = nullptr;
    };
    
} // namespace JD
