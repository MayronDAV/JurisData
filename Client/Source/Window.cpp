#include "Window.h"
#include "Base.h"

// lib
#include <glad/glad.h>


namespace JD
{
    Window::Window(const WindowSpecification &p_Spec)
    {
        if (!glfwInit())
        {
            ShowErrorWindow("GLFW Initialization Error", "Failed to initialize GLFW");
        }

        glfwWindowHint(GLFW_CONTEXT_VERSION_MAJOR, 3);
        glfwWindowHint(GLFW_CONTEXT_VERSION_MINOR, 3);
        glfwWindowHint(GLFW_OPENGL_PROFILE, GLFW_OPENGL_CORE_PROFILE);

        m_Window = glfwCreateWindow(p_Spec.Width, p_Spec.Height, p_Spec.Title.c_str(), nullptr, nullptr);
        if (!m_Window)
        {
            glfwTerminate();
            ShowErrorWindow("GLFW Window Creation Error", "Failed to create GLFW window");
        }

        glfwMakeContextCurrent(m_Window);

        if (!gladLoadGLLoader((GLADloadproc)glfwGetProcAddress))
        {
            glfwDestroyWindow(m_Window);
            glfwTerminate();
            ShowErrorWindow("GLAD Initialization Error", "Failed to initialize GLAD");
        }

        if (p_Spec.Vsync)
            glfwSwapInterval(1); // Enable V-Sync
        else
            glfwSwapInterval(0); // Disable V-Sync
    }
    
    Window::~Window()
    {
        if (m_Window)
        {
            glfwDestroyWindow(m_Window);
        }
        glfwTerminate();
    }
    
    void Window::SwapBuffer()
    {
        glfwSwapBuffers(m_Window);
    }
    
    void Window::PollEvents()
    {
        glfwPollEvents();
    }
    
    bool Window::ShouldClose() const
    {
        return glfwWindowShouldClose(m_Window);
    }
} // namespace JD