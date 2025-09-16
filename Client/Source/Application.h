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

        private:
            Window* m_Window = nullptr;
    };
    
} // namespace JD
