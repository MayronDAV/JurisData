#include "Application.h"

// lib
#include <imgui.h>
#include <imgui_internal.h>
#include <backends/imgui_impl_glfw.h>
#include <backends/imgui_impl_opengl3.h>



namespace JD
{
    namespace ImguiLayer
    {
        static void Init()
        {
            IMGUI_CHECKVERSION();
            ImGui::CreateContext();
            ImGuiIO& io = ImGui::GetIO(); (void)io;
            io.IniFilename = nullptr;                                   // Disable imgui.ini
            io.ConfigFlags |= ImGuiConfigFlags_NavEnableKeyboard;       // Enable Keyboard Controls
            //io.ConfigFlags |= ImGuiConfigFlags_NavEnableGamepad;      // Enable Gamepad Controls
            io.ConfigFlags |= ImGuiConfigFlags_DockingEnable;           // Enable Docking
            io.ConfigFlags |= ImGuiConfigFlags_ViewportsEnable;         // Enable Multi-Viewport / Platform Windows
            io.ConfigFlags |= ImGuiConfigFlags_DpiEnableScaleViewports;
            io.ConfigFlags |= ImGuiConfigFlags_DpiEnableScaleFonts;
            io.ConfigFlags |= ImGuiConfigFlags_DpiEnableScaleViewports;

            ImGui_ImplGlfw_InitForOpenGL(Application::Get().GetWindow().GetNative(), true);
		    ImGui_ImplOpenGL3_Init("#version 330 core");
        }

        static void NewFrame()
        {
            ImGui_ImplOpenGL3_NewFrame();
            ImGui_ImplGlfw_NewFrame();
            ImGui::NewFrame();
        }

        static void EndFrame()
        {
            ImGuiIO& io = ImGui::GetIO();
            auto& window = Application::Get().GetWindow();
            io.DisplaySize = ImVec2((float)window.GetWidth(), (float)window.GetHeight());

            // Rendering
            ImGui::Render();
            ImGui_ImplOpenGL3_RenderDrawData(ImGui::GetDrawData());

            if (io.ConfigFlags & ImGuiConfigFlags_ViewportsEnable)
            {
                GLFWwindow* backup_current_context = glfwGetCurrentContext();

                ImGui::UpdatePlatformWindows();
                ImGui::RenderPlatformWindowsDefault();

                glfwMakeContextCurrent(backup_current_context);
            }
        }

        static void Shutdown()
        {
            ImGui_ImplOpenGL3_Shutdown();
            ImGui_ImplGlfw_Shutdown();
            ImGui::DestroyContext();
        }

        void BeginDockspace(std::string p_ID, std::string p_Dockspace, bool p_MenuBar = false, ImGuiDockNodeFlags p_DockFlags = 0)
        {
            static bool opt_fullscreen = true;
            static bool opt_padding = false;
            static ImGuiDockNodeFlags dockspace_flags = ImGuiDockNodeFlags_NoWindowMenuButton | ImGuiDockNodeFlags_NoCloseButton;

            ImGuiWindowFlags window_flags = ImGuiWindowFlags_NoDocking;
            if (p_MenuBar)
                window_flags |= ImGuiWindowFlags_MenuBar;

            if (opt_fullscreen)
            {
                const ImGuiViewport* viewport = ImGui::GetMainViewport();
                ImGui::SetNextWindowPos(viewport->WorkPos);
                ImGui::SetNextWindowSize(viewport->WorkSize);
                ImGui::SetNextWindowViewport(viewport->ID);
                ImGui::PushStyleVar(ImGuiStyleVar_WindowRounding, 0.0f);
                ImGui::PushStyleVar(ImGuiStyleVar_WindowBorderSize, 0.0f);
                window_flags |= ImGuiWindowFlags_NoTitleBar | ImGuiWindowFlags_NoCollapse
                    | ImGuiWindowFlags_NoResize | ImGuiWindowFlags_NoMove;
                window_flags |= ImGuiWindowFlags_NoBringToFrontOnFocus | ImGuiWindowFlags_NoNavFocus;
            }
            else
            {
                dockspace_flags &= ~ImGuiDockNodeFlags_PassthruCentralNode;
            }

            if (dockspace_flags & ImGuiDockNodeFlags_PassthruCentralNode)
                window_flags |= ImGuiWindowFlags_NoBackground;

            ImGui::PushStyleColor(ImGuiCol_WindowBg, { 0.0f, 0.0f, 0.0f, 1.0f });
            if (!opt_padding)
                ImGui::PushStyleVar(ImGuiStyleVar_WindowPadding, ImVec2(0.0f, 0.0f));
            ImGui::Begin(p_Dockspace.c_str(), nullptr, window_flags);
            if (!opt_padding)
                ImGui::PopStyleVar();
            ImGui::PopStyleColor(); // windowBg

            if (opt_fullscreen)
                ImGui::PopStyleVar(2);

            // Submit the DockSpace
            ImGuiIO& io = ImGui::GetIO();
            if (io.ConfigFlags & ImGuiConfigFlags_DockingEnable)
            {
                ImGuiID dockspace_id = ImGui::GetID(p_ID.c_str());
                ImGui::DockSpace(dockspace_id, ImVec2(0.0f, 0.0f), dockspace_flags | p_DockFlags);
            }
        }

        void EndDockspace()
        {
            ImGui::End();
        }

    } // namespace ImguiLayer

    Application::Application()
    {
        s_Instance = this;

        m_Window = new Window();

        ImguiLayer::Init();
    }

    Application::~Application()
    {
        ImguiLayer::Shutdown();

        if (m_Window)
            delete m_Window;

        s_Instance = nullptr;
    }

    void Application::Run()
    {
        while (!m_Window->ShouldClose())
        {
            if (!m_Window->IsMinimized())
            {
                ImguiLayer::NewFrame();
                {
                    ImguiLayer::BeginDockspace("MyDockspace", "MainDockspace");

                    ImGui::ShowDemoWindow();

                    ImguiLayer::EndDockspace();
                }
                ImguiLayer::EndFrame();

                m_Window->SwapBuffer();
            }
            
            m_Window->PollEvents();
        }
    }

} // namespace JD
