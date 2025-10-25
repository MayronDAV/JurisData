#pragma once
#include "Window.h"

// lib
#include <nlohmann/json.hpp>

// std
#include <mutex>

using json = nlohmann::json;



namespace JD
{
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

            json CreateRequest(const std::string& p_Type, const std::string& p_Term);
            bool SendRequest(const json& p_Request);
            json ReceiveResponse();
            bool IsCompleteJson(const std::string& p_JsonStr);

        private:
            bool m_SearchPerformed = false;
            std::string m_SearchTerm = "";
            Window* m_Window = nullptr;

            int m_Socket = -1;
            json m_ServerResponse = {};

            static inline Application* s_Instance = nullptr;
    };
    
} // namespace JD
