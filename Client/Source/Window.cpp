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
            ShowErrorWindow("GLFW Initialization Error", "Failed to initialize GLFW", true);
        }

        glfwWindowHint(GLFW_CONTEXT_VERSION_MAJOR, 3);
        glfwWindowHint(GLFW_CONTEXT_VERSION_MINOR, 3);
        glfwWindowHint(GLFW_OPENGL_PROFILE, GLFW_OPENGL_CORE_PROFILE);

        m_Window = glfwCreateWindow(p_Spec.Width, p_Spec.Height, p_Spec.Title.c_str(), nullptr, nullptr);
        if (!m_Window)
        {
            glfwTerminate();
            ShowErrorWindow("GLFW Window Creation Error", "Failed to create GLFW window", true);
        }

        glfwMakeContextCurrent(m_Window);

        if (!gladLoadGLLoader((GLADloadproc)glfwGetProcAddress))
        {
            glfwDestroyWindow(m_Window);
            glfwTerminate();
            ShowErrorWindow("GLAD Initialization Error", "Failed to initialize GLAD", true);
        }

        glfwSwapInterval(p_Spec.Vsync ? 1 : 0);
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
    
    int Window::GetWidth() const
    {
        int width, height;
        glfwGetWindowSize(m_Window, &width, &height);
        return width;
    }

    int Window::GetHeight() const
    {
        int width, height;
        glfwGetWindowSize(m_Window, &width, &height);
        return height;
    }

    bool Window::ShouldClose() const
    {
        return glfwWindowShouldClose(m_Window);
    }

    bool Window::IsMinimized() const
    {
        return glfwGetWindowAttrib(m_Window, GLFW_ICONIFIED) == GLFW_TRUE;
    }
} // namespace JD