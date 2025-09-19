#pragma once

#include <string>
#define GLFW_INCLUDE_NONE
#include <GLFW/glfw3.h>


namespace JD
{
    struct WindowSpecification
    {
        std::string Title = "JurisData";
        uint32_t Width = 800;
        uint32_t Height = 600;
        bool Vsync = true;
    };

    class Window
    {
        public:
            Window(const WindowSpecification& p_Spec = {});
            ~Window();
    
            void SwapBuffer();
            void PollEvents();

            bool ShouldClose() const;
            bool IsMinimized() const;

            int GetWidth() const;
            int GetHeight() const;

            float GetDPIScale() const;

            GLFWwindow* GetNative() { return m_Window; }

        private:
            GLFWwindow* m_Window = nullptr;
    };


} // namespace JD