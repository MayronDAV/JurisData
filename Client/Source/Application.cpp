#include "Application.h"


namespace JD
{
    Application::Application()
    {
        m_Window = new Window();
    }

    Application::~Application()
    {
        if (m_Window)
            delete m_Window;
    }

    void Application::Run()
    {
        while (!m_Window->ShouldClose())
        {
            m_Window->PollEvents();
            m_Window->SwapBuffer();
        }
    }

} // namespace JD
