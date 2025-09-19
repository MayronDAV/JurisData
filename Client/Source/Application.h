#pragma once
#include "Window.h"


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
            void DrawUI();

        private:
            std::string m_LinkToScrape = "";
            Window* m_Window = nullptr;

            static inline Application* s_Instance = nullptr;
    };
    
} // namespace JD
