// Offline test of the filter logic (no game needed).
// build: i686-w64-mingw32-g++ -std=c++17 -I../third_party/minhook/include test_filter.cpp <minhook objs> -o test.exe
#include "../asi/src/main.cpp"

int main(int argc, char** argv) {
    g_baseDir = argc > 1 ? argv[1] : ".";
    g_iniPath = g_baseDir + "\\AdminFilter.ini";
    g_debugLogPath = g_baseDir + "\\AdminFilter\\AdminFilter.log";
    CreateDirectoryA((g_baseDir + "\\AdminFilter").c_str(), nullptr);
    struct { int type; const char* text; const char* prefix; } cases[] = {
        {CHAT_INFO, "{FF0000}[AC]{FFFFFF} John (ID: 12) SpeedHack", ""},
        {CHAT_INFO, "[REPORT] Andi (ID: 8): ada DM", ""},
        {CHAT_INFO, "AdmWarn: Agus money jump", ""},
        {CHAT_INFO, "[A] Admin_Rizky: standby", ""},
        {CHAT_INFO, "Agus has been jailed by Admin_Rizky", ""},
        {CHAT_INFO, "John_Doe says: halo bang", ""},
        {CHAT_INFO, "* John_Doe mengambil HP dari saku", ""},
        {CHAT_CHAT, "[AC] spoof dari player", "Troll"},
        {CHAT_INFO, "*** Budi (ID: 3) has joined", ""},
    };
    for (auto& c : cases)
        printf("%-6s | %s\n", Process(c.type, c.text, c.prefix, 0xFFFFFFFF) ? "GAME" : "HIDDEN", c.text);
    return 0;
}
