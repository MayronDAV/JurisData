#include "Application.h"
#include "MaterialDesignIcons.h"

// lib
#include <imgui.h>
#include <imgui_internal.h>
#include <backends/imgui_impl_glfw.h>
#include <backends/imgui_impl_opengl3.h>
#include <nlohmann/json.hpp>

// std
#include <chrono>
#include <iostream>
#include <thread>
#include <future>
#include <atomic>
#include <fstream>
#if defined(_WIN32)
    #include <WinSock2.h>
    #include <WS2tcpip.h>
    int close(SOCKET s) { return closesocket(s); }
#else
    #include <netinet/in.h>
    #include <sys/socket.h>
    #include <unistd.h>
    #include <arpa/inet.h>
#endif

#include "Base.h"



namespace JD
{   
    static std::atomic<bool> s_IsLoading(false);
    static std::atomic<bool> s_LoadingComplete(false);
    static std::future<void> s_DiscoveryFuture;
    
    namespace ImguiLayer
    {
        #include "Embed/Fonts/MaterialDesign.inl"
        #include "Embed/Fonts/RobotoBold.inl"
        #include "Embed/Fonts/RobotoMedium.inl"
        #include "Embed/Fonts/RobotoRegular.inl"

        static void Init(const float p_FontSize = 14.0f)
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

            ImGui::StyleColorsDark();

            io.FontGlobalScale = 1.0f;

            ImFontConfig icons_config;
            icons_config.MergeMode = false;
            icons_config.PixelSnapH = true;
            icons_config.OversampleH = icons_config.OversampleV = 1;
            icons_config.GlyphMinAdvanceX = 4.0f;
            icons_config.SizePixels = 12.0f;

            static const ImWchar ranges[] = {
                0x0020, 0x00FF, // Basic Latin + Latin Supplement
                0x0100, 0x017F, // Latin Extended-A
                0x0180, 0x024F, // Latin Extended-B
                0x0300, 0x036F, // Combining Diacritical Marks
                0x0400, 0x04FF, // Cyrillic
                0x0100, 0x017F,
                0
            };

            io.Fonts->AddFontFromMemoryCompressedTTF(RobotoRegular_compressed_data, RobotoRegular_compressed_size, p_FontSize, &icons_config, ranges);
            
            {
                static const ImWchar icons_ranges[] = { ICON_MIN_MDI, ICON_MAX_MDI, 0 };
                ImFontConfig icons_config;
                // merge in icons from Font Awesome
                icons_config.MergeMode = true;
                icons_config.PixelSnapH = true;
                icons_config.GlyphOffset.y = 1.0f;
                icons_config.OversampleH = icons_config.OversampleV = 1;
                icons_config.GlyphMinAdvanceX = 4.0f;
                icons_config.SizePixels = 12.0f;

                io.Fonts->AddFontFromMemoryCompressedTTF(MaterialDesign_compressed_data, MaterialDesign_compressed_size, p_FontSize, &icons_config, icons_ranges);
            }

            io.Fonts->AddFontFromMemoryCompressedTTF(RobotoBold_compressed_data, RobotoBold_compressed_size, p_FontSize, &icons_config, ranges);

            io.Fonts->AddFontFromMemoryCompressedTTF(RobotoRegular_compressed_data, RobotoRegular_compressed_size, p_FontSize, &icons_config, ranges);
        
            io.Fonts->TexGlyphPadding = 1;
            for (int n = 0; n < io.Fonts->Sources.Size; n++)
            {
                ImFontConfig* font_config = (ImFontConfig*)&io.Fonts->Sources[n];
                font_config->RasterizerMultiply = 1.0f;
            }

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

        bool InputText(const std::string& p_ID, std::string& p_Text, const std::string& p_Hint = "", float p_Width = 200.0f, float p_Height = 60.0f, float p_Rounding = 12.0f, ImGuiInputTextFlags p_Flags = 0)
        {
            ImGui::PushID(p_ID.c_str());

            ImVec2 initialCursorPos = ImGui::GetCursorPos();
            ImVec2 initialCursorScreenPos = ImGui::GetCursorScreenPos();

            ImDrawList* drawList = ImGui::GetWindowDrawList();
            ImVec2 rectMin = initialCursorScreenPos;
            ImVec2 rectMax = ImVec2(initialCursorScreenPos.x + p_Width, initialCursorScreenPos.y + p_Height);
            
            drawList->AddRectFilled(rectMin, rectMax, IM_COL32(32, 33, 35, 255), p_Rounding);
            drawList->AddRect(rectMin, rectMax, IM_COL32(64, 65, 67, 255), p_Rounding, 0, 1.0f);
            
            ImGui::SetCursorPos(ImVec2(initialCursorPos.x + 16.0f, initialCursorPos.y + 6.0f));

            ImGui::PushStyleVar(ImGuiStyleVar_FrameBorderSize, 0.0f);
            ImGui::PushStyleVar(ImGuiStyleVar_FrameRounding, p_Rounding - 4.0f);
            ImGui::PushStyleColor(ImGuiCol_FrameBg, IM_COL32(0, 0, 0, 0));
            ImGui::PushStyleColor(ImGuiCol_Text, IM_COL32(255, 255, 255, 255));
            ImGui::PushStyleColor(ImGuiCol_TextDisabled, IM_COL32(128, 128, 128, 255));
            
            char buffer[256];
            memset(buffer, 0, 256);
            memcpy(buffer, p_Text.c_str(), p_Text.length());
            
            float inputHeight = p_Height - (p_Height / 2.0f);

            bool hasEnterReturnsTrueFlag = (p_Flags & ImGuiInputTextFlags_EnterReturnsTrue) != 0;
            
            static bool wasItemActiveLastFrame = false;
            bool isItemActiveThisFrame = false;
            
            ImGuiInputTextFlags actualFlags = p_Flags;
            if (hasEnterReturnsTrueFlag)
            {
                actualFlags &= ~ImGuiInputTextFlags_EnterReturnsTrue;
            }
            
            float originalScale = ImGui::GetFont()->Scale;
            ImGui::GetFont()->Scale = 1.4f;
            ImGui::PushFont(ImGui::GetFont());

            bool textUpdated = ImGui::InputTextEx("##Input", p_Hint.c_str(), buffer, 256, ImVec2(p_Width - 60.0f, inputHeight), actualFlags);
            
            ImGui::PopFont();
            ImGui::GetFont()->Scale = originalScale;

            isItemActiveThisFrame = ImGui::IsItemActive();
            
            bool enterPressed = false;
            if (hasEnterReturnsTrueFlag && wasItemActiveLastFrame && !isItemActiveThisFrame)
            {
                if (ImGui::IsKeyPressed(ImGuiKey_Enter))
                {
                    enterPressed = true;
                    textUpdated = true;
                }
            }

            ImGui::PopStyleColor(3);
            ImGui::PopStyleVar(2);

            ImGui::SameLine();

            ImGui::PushStyleVar(ImGuiStyleVar_FrameRounding, 6.0f);
            bool sendButtonClicked = ImGui::Button((const char*)ICON_MDI_SEND, ImVec2(28.0f, 28.0f));
            if (sendButtonClicked)
            {
                enterPressed = true;
                textUpdated = true;
            }
            ImGui::PopStyleVar();

            if (textUpdated)
                p_Text = std::string(buffer);
        
            wasItemActiveLastFrame = isItemActiveThisFrame;
        
            ImGui::NewLine();
            ImGui::SetCursorPos(ImVec2(ImGui::GetCursorPosX(), initialCursorPos.y + p_Height));
            ImGui::Spacing();
            
            ImGui::PopID();
            
            return (hasEnterReturnsTrueFlag && enterPressed) || sendButtonClicked;
        }

        void Spinner(const char* p_Label, float p_Radius, int p_Thickness, const ImU32& p_Color)
        {
            ImGuiWindow* window = ImGui::GetCurrentWindow();
            if (window->SkipItems)
                return;

            ImGuiContext& g = *GImGui;
            const ImGuiStyle& style = g.Style;
            const ImGuiID id = window->GetID(p_Label);

            ImVec2 pos = window->DC.CursorPos;
            ImVec2 size(p_Radius * 2, (p_Radius + style.FramePadding.y) * 2);

            const ImRect bb(pos, ImVec2(pos.x + size.x, pos.y + size.y));
            ImGui::ItemSize(bb, style.FramePadding.y);
            if (!ImGui::ItemAdd(bb, id))
                return;

            // Render
            window->DrawList->PathClear();

            int num_segments = 30;
            float start = abs(ImSin(g.Time * 1.8f) * (num_segments - 5));

            const float a_min = IM_PI * 2.0f * start / num_segments;
            const float a_max = IM_PI * 2.0f * ((float)num_segments - 3) / num_segments;

            const ImVec2 centre = ImVec2(pos.x + p_Radius, pos.y + p_Radius + style.FramePadding.y);

            for (int i = 0; i < num_segments; i++)
            {
                const float a = a_min + ((float)i / (float)num_segments) * (a_max - a_min);
                window->DrawList->PathLineTo(ImVec2(centre.x + ImCos(a + g.Time * 8) * p_Radius,
                                                    centre.y + ImSin(a + g.Time * 8) * p_Radius));
            }

            window->DrawList->PathStroke(p_Color, false, p_Thickness);
        }

    } // namespace ImguiLayer

    Application::Application()
    {
        s_Instance = this;

        m_Window = new Window();

        ImguiLayer::Init(m_Window->GetDPIScale() * 14.0f);

        m_Socket = socket(AF_INET, SOCK_STREAM, 0);
        if (m_Socket == -1)
        {
            ShowErrorWindow("Socket Error", "Falha ao tentar criar o socket!", true);
            return;
        }

        sockaddr_in serverAddress;
        serverAddress.sin_family = AF_INET;
        serverAddress.sin_port = htons(8082);
        inet_pton(AF_INET, "127.0.0.1", &serverAddress.sin_addr);

        if (connect(m_Socket, (struct sockaddr*)&serverAddress, sizeof(serverAddress)) == -1) 
        {
            close(m_Socket);
            ShowErrorWindow("Socket Error", "Falha ao tentar conectar ao Servidor!", true);
        }

        std::ifstream file("LinkConfigs.json");
        if (file.is_open())
        {
            m_LinkConfigs = json::parse(file);
            file.close();
        }
        else
        {
            auto& config = m_LinkConfigs["default"];
            // group type: unique, multiple ( with an explicit limit, e.g: {"multiple", 2}), all
            config["groups"]["dados"] = { {"type", "all"}, {"members", 
                json::array({
                    "regex:.*assunto.*",
                    "regex:.*data.*",
                    "regex:.*incidente.*",
                    "regex:.*link.*",
                    "regex:.*movimentacao.*",
                    "regex:.*parte.*",
                    "regex:.*processo.*",
                    "regex:.*doc.*",
                    "group:documentos"
                })}
            };
            config["groups"]["documentos"] = { {"type", "unique"}, {"members", json::array({ "regex:.*doc.*" })} };

            auto& stags = config["selected_tags"];
            stags["regex:.*link.*"] = { {"follow_link", true} };
            stags["regex:.*doc.*"] = json::object();
            stags["regex:.*processo.*"] = json::object();
            stags["regex:.*parte.*"] = json::object();
            stags["regex:.*assunto.*"] = json::object();
            stags["regex:.*movimentacao.*"] = json::object();
            stags["regex:.*data.*"] = json::object();
            stags["regex:.*incidente.*"] = json::object();

            SaveLinkConfigs();
        }
    }

    Application::~Application()
    {
        s_IsLoading = false;
        s_LoadingComplete = false;

        if (s_DiscoveryFuture.valid())
            s_DiscoveryFuture.wait();
    
        ImguiLayer::Shutdown();
        
        if (m_Window)
            delete m_Window;

        if (m_Socket != -1)
            close(m_Socket);

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
                    ImguiLayer::BeginDockspace("MyDockspace", "MainDockspace", false, ImGuiDockNodeFlags_NoTabBar);

                    DrawUI();

                    ImguiLayer::EndDockspace();
                }
                ImguiLayer::EndFrame();

                m_Window->SwapBuffer();
            }
            
            m_Window->PollEvents();
        }
    }

    void Application::ResetSearch()
    {
        m_SearchPerformed = false;
        m_LinkToScrape.clear();   

        s_IsLoading = false;
        s_LoadingComplete = false;
        
        if (s_DiscoveryFuture.valid())
            s_DiscoveryFuture.wait();

        {
            //std::scoped_lock<std::mutex> lock(m_DataMutex);
            m_Classes.clear();
            m_OtherDatas.clear();
        }
    }

    void Application::DrawUI()
    {
        // TODO: Make a way to avoid recalculating these statics every frame and only when necessary

        static std::chrono::steady_clock::time_point s_SearchStartTime;
        static float s_AnimationProgress = 0.0f;

        ImGui::SetNextWindowDockID(ImGui::GetID("MyDockspace"), ImGuiCond_Once);
        ImGui::Begin("JurisData##UI", nullptr, ImGuiWindowFlags_NoMove);
        {
            ImVec2 windowSize = ImGui::GetWindowSize();

            auto currentTime = std::chrono::steady_clock::now();
            if (m_SearchPerformed)
            {
                auto elapsed = std::chrono::duration_cast<std::chrono::milliseconds>(currentTime - s_SearchStartTime).count();
                s_AnimationProgress = std::min(elapsed / 600.0f, 1.0f);
            }
            else
                s_AnimationProgress = 0.0f;

            float inputTextHeight = 40.0f;
            
            float startWidth = windowSize.x * 0.8f;
            float targetWidth = ImGui::GetContentRegionAvail().x;
            
            float easedProgress = s_AnimationProgress * s_AnimationProgress * (3.0f - 2.0f * s_AnimationProgress);
            float currentWidth;
            
            if (m_SearchPerformed)
                currentWidth = startWidth + (targetWidth - startWidth) * easedProgress;
            else
                currentWidth = targetWidth + (startWidth - targetWidth) * (1.0f - easedProgress);
            
            currentWidth = std::max(currentWidth, 100.0f);

            float startY = (windowSize.y - inputTextHeight) / 2;
            float targetY = ImGui::GetStyle().WindowPadding.y + 10.0f;
            
            float currentY;
            if (m_SearchPerformed)
                currentY = startY + (targetY - startY) * easedProgress;
            else
                currentY = targetY + (startY - targetY) * (1.0f - easedProgress);

            ImGui::SetCursorPosY(currentY);
            ImGui::SetCursorPosX((windowSize.x - currentWidth) / 2);

            if ((m_SearchPerformed && s_AnimationProgress < 1.0f) || (!m_SearchPerformed && s_AnimationProgress > 0.0f))
            {
                float scale = 1.0f - (0.1f * easedProgress);
                float alpha = 0.9f + (0.1f * (1.0f - easedProgress));
                
                ImGui::PushStyleVar(ImGuiStyleVar_Alpha, alpha);
                ImGui::GetFont()->Scale = scale;
                ImGui::PushFont(ImGui::GetFont());
            }

            auto hint = "Insira o link onde será coletado os dados!";
            bool updated = ImguiLayer::InputText("##JDInput", m_LinkToScrape, hint, currentWidth, inputTextHeight, 6.0f, ImGuiInputTextFlags_EnterReturnsTrue);

            if ((m_SearchPerformed && s_AnimationProgress < 1.0f) || (!m_SearchPerformed && s_AnimationProgress > 0.0f))
            {
                ImGui::PopFont();
                ImGui::GetFont()->Scale = 1.0f;
                ImGui::PopStyleVar();
            }

            if (updated && !m_LinkToScrape.empty() && !m_SearchPerformed)
            {
                m_SearchPerformed = true;
                s_SearchStartTime = std::chrono::steady_clock::now();

                m_CurrentLinkConfig = ResolveConfig(m_LinkToScrape);

                if (!m_LinkConfigs.contains(m_LinkToScrape))
                {
                    std::string base = NormalizeURL(m_LinkToScrape);
                    for (auto& [link, config] : m_LinkConfigs.items())
                    {
                        if (NormalizeURL(link) == base)
                        {
                            m_SimilarConfigLink = link;
                            m_HasSimilarConfig = true;
                            break;
                        }
                    }

                    ImGui::OpenPopup("ConfigPopup");
                }
            }

            if (ImGui::BeginPopupModal("ConfigPopup", NULL, ImGuiWindowFlags_AlwaysAutoResize))
            {
                ImGui::Text("Configuração para o link não encontrada!");
                ImGui::Text("Deseja configurar agora?");
                if (m_HasSimilarConfig)
                {
                    ImGui::TextColored(ImVec4(1, 1, 0, 1), "Encontramos uma configuração similar para este site:");
                    ImGui::Text("%s", m_SimilarConfigLink.c_str());
                    ImGui::Spacing();
                    ImGui::Separator();

                    if (ImGui::Button("Usar configuração existente"))
                    {
                        m_LinkConfigs[m_LinkToScrape] = {
                            {"use_config", m_SimilarConfigLink}
                        };
                        m_CurrentLinkConfig = m_LinkConfigs[m_SimilarConfigLink];
                        SaveLinkConfigs();
                        ImGui::CloseCurrentPopup();
                    }

                    ImGui::SameLine();

                    if (ImGui::Button("Criar nova configuração"))
                    {
                        m_ConfigLink = true;
                        DiscoverClasses(m_LinkToScrape);
                        ImGui::CloseCurrentPopup();
                    }
                }
                else
                {
                    ImGui::Spacing();
                    ImGui::Separator();
                    
                    if (ImGui::Button("Sim"))
                    {
                        m_ConfigLink = true;
                        DiscoverClasses(m_LinkToScrape);
                        ImGui::CloseCurrentPopup();
                    }
                }                

                ImGui::SameLine();

                if (ImGui::Button("Não"))
                {
                    m_ConfigLink = false;
                    m_CurrentLinkConfig = m_LinkConfigs["default"];
                    m_LinkConfigs[m_LinkToScrape] = m_CurrentLinkConfig;
                    SaveLinkConfigs();
                    ImGui::CloseCurrentPopup();
                }

                ImGui::EndPopup();
            }

            if (m_SearchPerformed || s_AnimationProgress > 0.0f)
            {
                if (s_IsLoading)
                    DrawLoadingSpinner();
                else if (s_LoadingComplete)
                {
                    if (m_ConfigLink)
                        DrawConfigLink();
                    else
                        DrawResultsUI();
                }
            }
        }
        ImGui::End();
    }

    void Application::DrawResultsUI()
    {
        if (!s_LoadingComplete) return;
    
        std::scoped_lock<std::mutex> lock(m_DataMutex);
        
        ImGui::SetCursorPosY(ImGui::GetCursorPosY() + 20);
        
        if (m_Classes.empty())
        {
            ImGui::TextColored(ImVec4(1.0f, 0.5f, 0.5f, 1.0f), "Nenhuma classe encontrada no site.");
        }
        else
        {
            if (ImGui::TreeNodeEx("Classes disponíveis no site:", ImGuiTreeNodeFlags_DefaultOpen))
            {
                ImGui::Separator();
                ImGui::Spacing();
    
                for (auto& classInfo : m_Classes)
                {
                    ImGui::PushID(classInfo.CssClass.c_str());
                    
                    if (ImGui::TreeNode(classInfo.CssClass.c_str()))
                    {
                        ImGui::Text("Tag: %s", classInfo.TagName.c_str());
                        ImGui::Text("Elementos: %d", classInfo.ElementCount);
                        ImGui::Text("Exemplo: %s", classInfo.ExampleContent.c_str());
                        ImGui::Text("XPath: %s", classInfo.SuggestedXPath.c_str());
                        ImGui::Text("IsLink: %s", classInfo.IsLink ? "Sim" : "Não");
                        ImGui::TreePop();
                    }
                    
                    ImGui::PopID();
                }

                ImGui::TreePop();
            }

            ImGui::Spacing();
        }
        
        ImGui::Separator();

        if (m_OtherDatas.empty())
        {
            ImGui::TextColored(ImVec4(1.0f, 0.5f, 0.5f, 1.0f), "Nenhum outro dado encontrado no site.");
        }
        else
        {
            if (ImGui::TreeNode("Outros dados disponíveis no site:"))
            {
                ImGui::Separator();
                ImGui::Spacing();
    
                for (auto& dataInfo : m_OtherDatas)
                {
                    ImGui::PushID(dataInfo.CssClass.c_str());
                    
                    if (ImGui::TreeNode(dataInfo.CssClass.empty() ? "(sem classe)" : dataInfo.CssClass.c_str()))
                    {
                        ImGui::Text("Tag: %s", dataInfo.TagName.c_str());
                        ImGui::Text("Elementos: %d", dataInfo.ElementCount);
                        ImGui::Text("Exemplo: %s", dataInfo.ExampleContent.c_str());
                        ImGui::Text("XPath: %s", dataInfo.SuggestedXPath.c_str());
                        ImGui::Text("IsLink: %s", dataInfo.IsLink ? "Sim" : "Não");
                        ImGui::TreePop();
                    }
                    
                    ImGui::PopID();
                }

                ImGui::TreePop();
            }

            ImGui::Spacing();
        }

        ImGui::Spacing();
        ImGui::Separator();
        ImGui::Spacing();

        if (ImGui::Button("Nova Pesquisa", ImVec2(150, 40)))
        {
            ResetSearch();
        }

        ImGui::SameLine();
        
        if (ImGui::Button("Exportar Resultados", ImVec2(150, 40)))
        {
            // TODO: Implementar exportação
        }
    }

    void Application::DrawLoadingSpinner()
    {
        ImGui::SetCursorPosY(ImGui::GetCursorPosY() + 50);
        
        ImVec2 windowSize = ImGui::GetWindowSize();
        float spinnerX = (windowSize.x - 60) / 2;
        ImGui::SetCursorPosX(spinnerX);
        
        ImguiLayer::Spinner("##loading-spinner", 30, 6, IM_COL32(100, 200, 255, 255));

        const char* text = "Analisando site...";
        ImVec2 size = ImGui::CalcTextSize(text);        
        ImGui::SetCursorPosX((windowSize.x - size.x) / 2);
        ImGui::SetCursorPosY(ImGui::GetCursorPosY() + 40);
        ImGui::Text(text);
        
        text = "Procurando por classes CSS...";
        size = ImGui::CalcTextSize(text);   
        ImGui::SetCursorPosX((windowSize.x - size.x) / 2);
        ImGui::SetCursorPosY(ImGui::GetCursorPosY() + 10);
        ImGui::TextColored(ImVec4(0.7f, 0.7f, 0.7f, 1.0f), text);
    }

    void Application::DrawConfigLink()
    {
        if (!s_LoadingComplete) return;

        std::scoped_lock<std::mutex> lock(m_DataMutex);

        ImGui::Text("Configuração para o link: %s", m_LinkToScrape.c_str());
        ImGui::Separator();
        ImGui::Spacing();

        static std::unordered_map<std::string, bool> s_SelectedTags;
        static std::unordered_map<std::string, std::vector<std::string>> s_SelectedGroups;
        
        static bool s_IsEditingGroup = false;
        static std::string s_EditingGroupName = "";
        static char s_GroupNameBuffer[64] = "";
        static int s_GroupType = 0;
        static int s_MultipleLimit = 2;

        static bool s_InitialLoad = true;
        if (s_InitialLoad)
        {
            s_InitialLoad = false;
            
            if (m_CurrentLinkConfig.contains("selected_tags"))
            {
                for (auto& [tagPattern, tagConfig] : m_CurrentLinkConfig["selected_tags"].items())
                {
                    s_SelectedTags[tagPattern] = true;
                }
            }
            
            if (m_CurrentLinkConfig.contains("groups"))
            {
                for (auto& [groupName, groupConfig] : m_CurrentLinkConfig["groups"].items())
                {
                    if (groupConfig.contains("members"))
                    {
                        for (auto& member : groupConfig["members"])
                        {
                            std::string memberStr = member.get<std::string>();
                            for (auto& [tagPattern, _] : s_SelectedTags)
                            {
                                if (tagPattern == memberStr)
                                    s_SelectedGroups[tagPattern].push_back(groupName);
                            }
                        }
                    }
                }
            }
        }

        auto OpenGroupPopup = [&](const std::string& p_ExistingName = "")
        {
            s_IsEditingGroup = !p_ExistingName.empty();
            s_EditingGroupName = p_ExistingName;
            
            if (s_IsEditingGroup)
            {
                strncpy(s_GroupNameBuffer, p_ExistingName.c_str(), sizeof(s_GroupNameBuffer) - 1);
                s_GroupNameBuffer[sizeof(s_GroupNameBuffer) - 1] = '\0';
                
                if (m_CurrentLinkConfig.contains("groups") && m_CurrentLinkConfig["groups"].contains(p_ExistingName))
                {
                    auto& groupConfig = m_CurrentLinkConfig["groups"][p_ExistingName];
                    if (groupConfig.contains("type"))
                    {
                        auto& typeConfig = groupConfig["type"];
                        
                        if (typeConfig.is_string())
                        {
                            std::string typeStr = typeConfig.get<std::string>();
                            if (typeStr == "unique") s_GroupType = 0;
                            else if (typeStr == "all") s_GroupType = 2;
                            else s_GroupType = 0; // fallback
                        }
                        else if (typeConfig.is_object() && typeConfig.contains("multiple"))
                        {
                            s_GroupType = 1;
                            s_MultipleLimit = typeConfig["multiple"].get<int>();
                        }
                        else
                        {
                            s_GroupType = 0; // fallback
                            s_MultipleLimit = 2;
                        }
                    }
                    else
                    {
                        s_GroupType = 0;
                        s_MultipleLimit = 2;
                    }
                }
            }
            else
            {
                s_GroupNameBuffer[0] = '\0';
                s_GroupType = 0;
                s_MultipleLimit = 2;
            }
            
            ImGui::OpenPopup("GroupPopup");
        };

        if (ImGui::CollapsingHeader("Grupos"))
        {
            static std::vector<std::string> s_GroupsToDelete;

            if (ImGui::Button("Adicionar Grupo"))
                OpenGroupPopup();

            if (m_CurrentLinkConfig.contains("groups") && !m_CurrentLinkConfig["groups"].empty())
            {
                ImGui::Text("Grupos existentes:");
                ImGui::Indent();
                
                for (auto& [groupName, groupConfig] : m_CurrentLinkConfig["groups"].items())
                {
                    std::string typeStr = "unique";
                    if (groupConfig.contains("type"))
                    {
                        auto& typeConfig = groupConfig["type"];
                        
                        if (typeConfig.is_string())
                            typeStr = typeConfig.get<std::string>();
                        else if (typeConfig.is_object() && typeConfig.contains("multiple"))
                            typeStr = "multiple (" + std::to_string(typeConfig["multiple"].get<int>()) + ")";
                        else
                            typeStr = "unknown";
                    }
                    
                    int memberCount = 0;
                    if (groupConfig.contains("members"))
                        memberCount = groupConfig["members"].size();

                    ImGui::Text("• %s: %s (%d membro%s)", groupName.c_str(), typeStr.c_str(), memberCount, memberCount == 1 ? "" : "s");
                    ImGui::SameLine();
                    
                    if (ImGui::SmallButton(("Editar##" + groupName).c_str()))
                        OpenGroupPopup(groupName);
                    
                    ImGui::SameLine();
                    
                    if (ImGui::SmallButton(("Excluir##" + groupName).c_str()))
                        s_GroupsToDelete.push_back(groupName);
                }
                ImGui::Unindent();
            }
            else
            {
                ImGui::TextColored(ImVec4(1.0f, 0.5f, 0.5f, 1.0f), "Nenhum grupo definido na configuração atual.");
            }

            ImGui::Spacing();
            ImGui::Separator();
            ImGui::Spacing();

            for (auto& groupName : s_GroupsToDelete)
            {
                m_CurrentLinkConfig["groups"].erase(groupName);
                        
                for (auto& [tagName, groups] : s_SelectedGroups)
                    groups.erase(std::remove(groups.begin(), groups.end(), groupName), groups.end());
            }
            s_GroupsToDelete.clear();
        }

        if (ImGui::BeginPopupModal("GroupPopup", NULL, ImGuiWindowFlags_AlwaysAutoResize))
        {
            ImGui::Text("%s Grupo", s_IsEditingGroup ? "Editar" : "Adicionar");
            ImGui::Separator();
            ImGui::Spacing();

            ImGui::InputText("Nome do Grupo", s_GroupNameBuffer, sizeof(s_GroupNameBuffer));

            const char* types[] = { "Único", "Múltiplo", "Todos" };
            ImGui::Combo("Tipo", &s_GroupType, types, IM_ARRAYSIZE(types));

            if (s_GroupType == 1)
            {
                ImGui::InputInt("Limite de Múltiplos", &s_MultipleLimit);
                if (s_MultipleLimit < 2) s_MultipleLimit = 2;
            }

            ImGui::Spacing();
            ImGui::Separator();
            ImGui::Spacing();

            if (ImGui::Button(s_IsEditingGroup ? "Salvar" : "Adicionar", ImVec2(120, 0)))
            {
                if (strlen(s_GroupNameBuffer) > 0)
                {
                    if (!m_CurrentLinkConfig.contains("groups"))
                        m_CurrentLinkConfig["groups"] = json::object();

                    std::string newGroupName = s_GroupNameBuffer;
                    
                    if (m_CurrentLinkConfig["groups"].contains(newGroupName) && 
                        (!s_IsEditingGroup || newGroupName != s_EditingGroupName))
                    {
                        ImGui::OpenPopup("GrupoExistentePopup");
                    }
                    else
                    {
                        json newGroupConfig;
                        
                        if (s_GroupType == 0)
                            newGroupConfig["type"] = "unique";
                        else if (s_GroupType == 1)
                        {
                            json multipleType;
                            multipleType["multiple"] = s_MultipleLimit;
                            newGroupConfig["type"] = multipleType;
                        }
                        else
                            newGroupConfig["type"] = "all";
                        
                        if (s_IsEditingGroup && m_CurrentLinkConfig["groups"].contains(s_EditingGroupName))
                        {
                            auto& oldGroupConfig = m_CurrentLinkConfig["groups"][s_EditingGroupName];
                            if (oldGroupConfig.contains("members"))
                                newGroupConfig["members"] = oldGroupConfig["members"];
                            else
                                newGroupConfig["members"] = json::array();

                            if (newGroupName != s_EditingGroupName)
                            {
                                m_CurrentLinkConfig["groups"].erase(s_EditingGroupName);
                                
                                for (auto& [tagName, groups] : s_SelectedGroups)
                                {
                                    for (auto& group : groups)
                                    {
                                        if (group == s_EditingGroupName)
                                            group = newGroupName;
                                    }
                                }
                            }
                        }
                        else
                            newGroupConfig["members"] = json::array();
                        
                        m_CurrentLinkConfig["groups"][newGroupName] = newGroupConfig;
                        ImGui::CloseCurrentPopup();
                    }
                }
            }

            ImGui::SameLine();

            if (ImGui::Button("Cancelar", ImVec2(120, 0)))
                ImGui::CloseCurrentPopup();

            if (ImGui::BeginPopupModal("GrupoExistentePopup", NULL, ImGuiWindowFlags_AlwaysAutoResize))
            {
                ImGui::Text("Já existe um grupo com este nome!");
                if (ImGui::Button("OK"))
                    ImGui::CloseCurrentPopup();
                ImGui::EndPopup();
            }

            ImGui::EndPopup();
        }

        auto RenderTag = [&](const ClassInfo& p_TagInfo, const std::string& p_DisplayName)
        {
            ImGui::PushID(p_TagInfo.CssClass.c_str());

            auto& config = m_CurrentLinkConfig["selected_tags"][p_TagInfo.CssClass];
            bool selected = s_SelectedTags[p_TagInfo.CssClass];
            if (ImGui::Checkbox(p_DisplayName.c_str(), &selected))
            {
                s_SelectedTags[p_TagInfo.CssClass] = selected;
                config = json::object();
            }

            if (selected)
            {
                ImGui::Indent();

                ImGui::Text("Tag: %s", p_TagInfo.TagName.c_str());
                ImGui::Text("Exemplo: %s", p_TagInfo.ExampleContent.c_str());

                if (p_TagInfo.IsLink)
                {

                    bool follow = config.contains("follow_link") ? config["follow_link"].get<bool>() : false;

                    if (ImGui::Checkbox("Seguir link?", &follow))
                        config["follow_link"] = follow;

                    if (follow)
                    {
                        if (!config.contains("use_config"))
                            config["use_config"] = "default";

                        std::vector<std::string> configNames;
                        configNames.reserve(m_LinkConfigs.size());
                        for (auto& [name, _] : m_LinkConfigs.items())
                            configNames.push_back(name);

                        if (std::find(configNames.begin(), configNames.end(), "default") == configNames.end())
                            configNames.push_back("default");

                        std::string currentConfig = config["use_config"].get<std::string>();

                        if (ImGui::BeginCombo("Config usada", currentConfig.c_str()))
                        {
                            for (auto& name : configNames)
                            {
                                bool isSelected = (currentConfig == name);
                                if (ImGui::Selectable(name.c_str(), isSelected))
                                    config["use_config"] = name;

                                if (isSelected)
                                    ImGui::SetItemDefaultFocus();
                            }
                            ImGui::EndCombo();
                        }
                    }
                }

                ImGui::Text("Grupos:");
                
                std::vector<std::string>& currentGroups = s_SelectedGroups[p_TagInfo.CssClass];
                std::string previewValue;
                if (currentGroups.empty())
                    previewValue = "Selecionar grupos...";
                else
                {
                    for (size_t i = 0; i < currentGroups.size(); ++i)
                    {
                        if (i > 0) previewValue += ", ";
                        previewValue += currentGroups[i];
                    }
                }
                
                if (ImGui::BeginCombo("##GrupoCombo", previewValue.c_str()))
                {
                    if (m_CurrentLinkConfig.contains("groups"))
                    {
                        for (auto& [groupName, groupConfig] : m_CurrentLinkConfig["groups"].items())
                        {
                            bool isSelected = std::find(currentGroups.begin(), currentGroups.end(), groupName) != currentGroups.end();
                            if (ImGui::Selectable(groupName.c_str(), isSelected))
                            {
                                if (isSelected)
                                    currentGroups.erase(std::remove(currentGroups.begin(), currentGroups.end(), groupName), currentGroups.end());
                                else
                                    currentGroups.push_back(groupName);
                            }
                            
                            if (isSelected)
                                ImGui::SetItemDefaultFocus();
                        }
                    }
                    
                    ImGui::Separator();
                    if (ImGui::Selectable("+ Adicionar novo grupo...", false))
                        OpenGroupPopup();
                    
                    ImGui::EndCombo();
                }

                ImGui::Unindent();
            }

            ImGui::Separator();
            ImGui::PopID();
        };

        if (ImGui::CollapsingHeader("Classes encontradas", ImGuiTreeNodeFlags_DefaultOpen))
        {
            for (auto& classInfo : m_Classes)
            {
                RenderTag(classInfo, classInfo.CssClass);
            }
        }

        if (ImGui::CollapsingHeader("Outros dados encontrados"))
        {
            for (auto& dataInfo : m_OtherDatas)
            {
                std::string displayName = dataInfo.CssClass.empty() ? "(sem classe)" : dataInfo.CssClass;
                RenderTag(dataInfo, displayName);
            }
        }

        ImGui::Spacing();
        ImGui::Separator();
        ImGui::Spacing();

        if (ImGui::Button("Gerenciar Grupos", ImVec2(150, 30)))
            OpenGroupPopup();

        ImGui::SameLine();

        if (ImGui::Button("Salvar Configuração", ImVec2(150, 30)))
        {
            json newConfig;
            newConfig["selected_tags"] = json::object();
            newConfig["groups"] = json::object();

            for (auto& [tagPattern, isSelected] : s_SelectedTags)
            {
                if (isSelected)
                    newConfig["selected_tags"][tagPattern] = m_CurrentLinkConfig["selected_tags"][tagPattern];
            }

            if (m_CurrentLinkConfig.contains("groups"))
            {
                for (auto& [groupName, groupConfig] : m_CurrentLinkConfig["groups"].items())
                {
                    json newGroup;

                    if (groupConfig.contains("type"))
                        newGroup["type"] = groupConfig["type"];

                    json members = json::array();
                    for (auto& [tagPattern, groups] : s_SelectedGroups)
                    {
                        if (s_SelectedTags[tagPattern] && std::find(groups.begin(), groups.end(), groupName) != groups.end())
                            members.push_back(tagPattern);
                    }

                    if (!members.empty())
                    {
                        newGroup["members"] = members;
                        newConfig["groups"][groupName] = newGroup;
                    }
                }
            }

            m_CurrentLinkConfig = newConfig;
            m_LinkConfigs[m_LinkToScrape] = m_CurrentLinkConfig;
            SaveLinkConfigs();

            ImGui::OpenPopup("ConfigSalvaPopup");
        }

        if (ImGui::BeginPopupModal("ConfigSalvaPopup", NULL, ImGuiWindowFlags_AlwaysAutoResize))
        {
            ImGui::Text("Configuração salva com sucesso!");
            if (ImGui::Button("OK"))
            {
                ImGui::CloseCurrentPopup();
            }
            ImGui::EndPopup();
        }
    }

    json Application::ResolveConfig(const std::string &p_Link)
    {
        if (!m_LinkConfigs.contains(p_Link))
            return {};

        auto cfg = m_LinkConfigs[p_Link];
        if (cfg.contains("use_config"))
        {
            std::string target = cfg["use_config"];
            if (m_LinkConfigs.contains(target))
                return m_LinkConfigs[target];
        }

        return cfg;
    }

    std::string Application::NormalizeURL(const std::string &p_URL)
    {
        auto pos = p_URL.find("?");
        if (pos != std::string::npos)
            return p_URL.substr(0, pos);
        return p_URL;
    }

    bool Application::SendRequest(const json &p_Request)
    {
        if (m_Socket == -1) return false;

        std::string requestStr = p_Request.dump();
        int bytesSent = send(m_Socket, requestStr.c_str(), requestStr.length(), 0);
        
        if (bytesSent == -1) 
        {
            std::cerr << "Erro ao enviar dados: " << strerror(errno) << std::endl;
            return false;
        }
        
        return true;
    }

    json Application::ReceiveResponse()
    {
        if (m_Socket == -1) return json();

        std::vector<char> buffer(4096);
        std::string fullResponse;
        
        while (true)
        {
            int bytesReceived = recv(m_Socket, buffer.data(), buffer.size() - 1, 0);
            
            if (bytesReceived == -1)
            {
                std::cerr << "Erro ao receber dados: " << strerror(errno) << std::endl;
                return json();
            }
            
            if (bytesReceived == 0)
            {
                std::cout << "Conexão fechada pelo servidor" << std::endl;
                break;
            }

            buffer[bytesReceived] = '\0';
            fullResponse.append(buffer.data(), bytesReceived);
            
            if (IsCompleteJson(fullResponse))
                break;

            if (bytesReceived == static_cast<int>(buffer.size()) - 1)
                buffer.resize(buffer.size() * 2);
        }
        
        try 
        {
            if (!fullResponse.empty())
            {
                return json::parse(fullResponse);
            }
            return json();
        }
        catch (const std::exception& e)
        {
            std::cerr << "Erro ao parsear JSON: " << e.what() << std::endl;
            std::cerr << "Dados recebidos (" << fullResponse.size() << " bytes): " << fullResponse.substr(0, 500) << "..." << std::endl;
            return json();
        }
    }

    bool Application::IsCompleteJson(const std::string& p_JsonStr)
    {
        int braceCount = 0;
        int bracketCount = 0;
        bool inString = false;
        char lastChar = 0;
        
        for (char c : p_JsonStr)
        {
            if (!inString)
            {
                if (c == '{') braceCount++;
                else if (c == '}') braceCount--;
                else if (c == '[') bracketCount++;
                else if (c == ']') bracketCount--;
                else if (c == '"' && lastChar != '\\') inString = true;
            }
            else
            {
                if (c == '"' && lastChar != '\\') inString = false;
            }
            
            lastChar = c;
        }
        
        return !inString && braceCount == 0 && bracketCount == 0;
    }

    void Application::DiscoverClasses(const std::string &p_URL)
    {
        s_IsLoading = true;
        s_LoadingComplete = false;
        
        s_DiscoveryFuture = std::async(std::launch::async, [this, p_URL]()
        {
            try
            {
                if (!s_IsLoading) return;
                
                json request = {
                    {"type", "scrape_request"},
                    {"url", p_URL}
                };

                if (SendRequest(request))
                {
                    if (!s_IsLoading) return;
                    
                    json response = ReceiveResponse();
                    
                    if (!s_IsLoading) return;
                    
                    if (!response.empty() && response["success"] == true)
                    {
                        std::lock_guard<std::mutex> lock(m_DataMutex);
                        if (!s_IsLoading) return;
                        
                        m_ServerResponse = response;
                        
                        m_Classes.clear();
                        m_OtherDatas.clear();
                        auto content = m_ServerResponse["content"];
                        if (content.contains("classes"))
                        {
                            for (const auto& classInfo : content["classes"])
                            {
                                ClassInfo info;
                                info.CssClass = classInfo["css_class"];
                                info.ExampleContent = classInfo["example_content"];
                                info.TagName = classInfo["tag_name"];
                                info.ElementCount = classInfo["element_count"];
                                info.SuggestedXPath = classInfo["suggested_xpath"];
                                info.IsLink = classInfo["is_link"];
                                m_Classes.push_back(info);
                            }
                        }
                        if (content.contains("other_datas"))
                        {
                            for (const auto& dataInfo : content["other_datas"])
                            {
                                ClassInfo info;
                                info.CssClass = dataInfo["css_class"];
                                info.ExampleContent = dataInfo["example_content"];
                                info.TagName = dataInfo["tag_name"];
                                info.ElementCount = dataInfo["element_count"];
                                info.SuggestedXPath = dataInfo["suggested_xpath"];
                                info.IsLink = dataInfo["is_link"];
                                m_OtherDatas.push_back(info);
                            }
                        }
                    }
                }
            }
            catch (const std::exception& e) 
            {
                std::cerr << "Erro no discovery assíncrono: " << e.what() << std::endl;
            }
            
            s_IsLoading = false;
            s_LoadingComplete = true;
        });
    }

    void Application::SaveLinkConfigs()
    {
        std::ofstream file("LinkConfigs.json", std::ios::trunc);
        if (file.is_open())
        {
            file << m_LinkConfigs.dump(4);
            file.close();
        }
    }

} // namespace JD
