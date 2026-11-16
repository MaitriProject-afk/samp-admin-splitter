// AdminFilter.asi - SA-MP 0.3.DL chat splitter
// Hooks CChat::AddEntry in samp.dll. Messages matching a channel in
// AdminFilter.ini are written to AdminFilter\logs\<channel>.log and
// (depending on Action) hidden from the in-game chatbox.
// Config is hot-reloaded: edit the INI while playing, no restart needed.

#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <share.h>
#include <cstdio>
#include <cstring>
#include <cstdint>
#include <ctime>
#include <string>
#include <vector>
#include <regex>
#include <algorithm>
#include "MinHook.h"

// ---------------------------------------------------------------- types
enum ChatType { CHAT_NONE = 0, CHAT_DEBUG = 1, CHAT_CHAT = 2, CHAT_INFO = 4, CHAT_DEBUG8 = 8 };
enum Action { ACT_MOVE, ACT_COPY, ACT_DROP };

struct Channel {
    std::string name;
    std::vector<std::string> match, startsWith, exclude;
    std::regex re;
    bool hasRe = false;
    Action action = ACT_MOVE;
    bool playerChat = false;  // also match type CHAT (player talk)? default no
    FILE* fp = nullptr;
};

struct IniSection {
    std::string name;
    std::vector<std::pair<std::string, std::string>> kv;
    std::string get(const char* key, const std::string& def = "") const {
        for (auto& p : kv)
            if (_stricmp(p.first.c_str(), key) == 0) return p.second;
        return def;
    }
};

typedef void(__thiscall* AddEntry_t)(void*, int, const char*, const char*, DWORD, DWORD);

// ---------------------------------------------------------------- globals
static HMODULE g_self = nullptr;
static std::string g_baseDir, g_iniPath, g_logDir, g_debugLogPath;
static std::vector<Channel> g_channels;
static bool g_enabled = true, g_caseSensitive = false, g_captureAll = false, g_requireMonitor = true;
static DWORD g_reloadMs = 250, g_lastCheck = 0;
static FILETIME g_iniTime{};
static FILE* g_allFp = nullptr;
static AddEntry_t g_origAddEntry = nullptr;

// ---------------------------------------------------------------- utils
static void DebugLog(const char* fmt, ...) {
    FILE* f = _fsopen(g_debugLogPath.c_str(), "a", _SH_DENYNO);
    if (!f) return;
    time_t t = time(nullptr);
    tm lt; localtime_s(&lt, &t);
    fprintf(f, "[%02d:%02d:%02d] ", lt.tm_hour, lt.tm_min, lt.tm_sec);
    va_list ap; va_start(ap, fmt); vfprintf(f, fmt, ap); va_end(ap);
    fputc('\n', f);
    fclose(f);
}

static std::string Trim(const std::string& s) {
    size_t a = s.find_first_not_of(" \t\r\n");
    if (a == std::string::npos) return "";
    size_t b = s.find_last_not_of(" \t\r\n");
    return s.substr(a, b - a + 1);
}

static std::string Lower(std::string s) {
    for (auto& c : s) c = (char)tolower((unsigned char)c);
    return s;
}

static std::vector<std::string> SplitList(const std::string& s, bool lower) {
    std::vector<std::string> out;
    size_t start = 0;
    while (start <= s.size()) {
        size_t p = s.find('|', start);
        std::string item = Trim(s.substr(start, p == std::string::npos ? std::string::npos : p - start));
        if (!item.empty()) out.push_back(lower ? Lower(item) : item);
        if (p == std::string::npos) break;
        start = p + 1;
    }
    return out;
}

static bool IsHex(char c) { return isxdigit((unsigned char)c) != 0; }

// Remove SA-MP inline colour codes like {FF0000}
static std::string StripColors(const char* text) {
    std::string out;
    for (const char* p = text; *p; ++p) {
        if (p[0] == '{' && IsHex(p[1]) && IsHex(p[2]) && IsHex(p[3]) && IsHex(p[4]) &&
            IsHex(p[5]) && IsHex(p[6]) && p[7] == '}') {
            p += 7;
            continue;
        }
        out += *p;
    }
    return out;
}

static std::string Sanitize(const char* s) {
    std::string out = s ? s : "";
    for (auto& c : out) if (c == '\t' || c == '\r' || c == '\n') c = ' ';
    return out;
}

static bool GetFileTime(const std::string& path, FILETIME& ft) {
    WIN32_FILE_ATTRIBUTE_DATA d;
    if (!GetFileAttributesExA(path.c_str(), GetFileExInfoStandard, &d)) return false;
    ft = d.ftLastWriteTime;
    return true;
}

static bool ReadIni(const std::string& path, std::vector<IniSection>& out) {
    FILE* f = _fsopen(path.c_str(), "r", _SH_DENYNO);
    if (!f) return false;
    char buf[4096];
    IniSection* cur = nullptr;
    out.clear();
    out.push_back({""});
    cur = &out.back();
    bool first = true;
    while (fgets(buf, sizeof(buf), f)) {
        std::string line = buf;
        if (first) {  // skip UTF-8 BOM
            if (line.size() >= 3 && (unsigned char)line[0] == 0xEF && (unsigned char)line[1] == 0xBB &&
                (unsigned char)line[2] == 0xBF)
                line = line.substr(3);
            first = false;
        }
        line = Trim(line);
        if (line.empty() || line[0] == ';' || line[0] == '#') continue;
        if (line.front() == '[' && line.back() == ']') {
            out.push_back({Trim(line.substr(1, line.size() - 2))});
            cur = &out.back();
            continue;
        }
        size_t eq = line.find('=');
        if (eq == std::string::npos) continue;
        cur->kv.push_back({Trim(line.substr(0, eq)), Trim(line.substr(eq + 1))});
    }
    fclose(f);
    return true;
}

static bool ParseBool(const std::string& v, bool def) {
    if (v.empty()) return def;
    std::string l = Lower(v);
    return l == "1" || l == "true" || l == "yes" || l == "on";
}

static FILE* OpenLog(const std::string& name) {
    std::string path = g_logDir + "\\" + name + ".log";
    return _fsopen(path.c_str(), "a", _SH_DENYNO);
}

// ---------------------------------------------------------------- config
static void CloseAll() {
    for (auto& c : g_channels)
        if (c.fp) fclose(c.fp);
    g_channels.clear();
    if (g_allFp) { fclose(g_allFp); g_allFp = nullptr; }
}

static void LoadConfig() {
    std::vector<IniSection> secs;
    if (!ReadIni(g_iniPath, secs)) {
        DebugLog("Cannot read %s - filter idle", g_iniPath.c_str());
        CloseAll();
        return;
    }
    CloseAll();

    for (auto& s : secs) {
        if (_stricmp(s.name.c_str(), "General") == 0) {
            g_enabled = ParseBool(s.get("Enabled"), true);
            g_caseSensitive = ParseBool(s.get("CaseSensitive"), false);
            g_captureAll = ParseBool(s.get("CaptureAll"), false);
            g_requireMonitor = ParseBool(s.get("RequireMonitor"), true);
            g_reloadMs = (DWORD)atoi(s.get("ReloadIntervalMs", "250").c_str());
            if (g_reloadMs < 150) g_reloadMs = 150;
            std::string ld = s.get("LogDir", "AdminFilter\\logs");
            g_logDir = (ld.size() > 1 && ld[1] == ':') ? ld : g_baseDir + "\\" + ld;
        }
    }
    CreateDirectoryA((g_baseDir + "\\AdminFilter").c_str(), nullptr);
    CreateDirectoryA(g_logDir.c_str(), nullptr);

    bool lower = !g_caseSensitive;
    for (auto& s : secs) {
        if (_strnicmp(s.name.c_str(), "Channel:", 8) != 0) continue;
        if (!ParseBool(s.get("Enabled"), true)) continue;
        Channel c;
        c.name = Trim(s.name.substr(8));
        if (c.name.empty()) continue;
        c.match = SplitList(s.get("Match"), lower);
        c.startsWith = SplitList(s.get("StartsWith"), lower);
        c.exclude = SplitList(s.get("Exclude"), lower);
        std::string re = s.get("Regex");
        if (!re.empty()) {
            try {
                auto fl = std::regex::ECMAScript | std::regex::optimize;
                if (lower) fl |= std::regex::icase;
                c.re = std::regex(re, fl);
                c.hasRe = true;
            } catch (...) {
                DebugLog("Channel %s: invalid Regex '%s' (ignored)", c.name.c_str(), re.c_str());
            }
        }
        std::string act = Lower(s.get("Action", "move"));
        c.action = act == "copy" ? ACT_COPY : act == "drop" ? ACT_DROP : ACT_MOVE;
        c.playerChat = ParseBool(s.get("PlayerChat"), false);
        if (c.match.empty() && c.startsWith.empty() && !c.hasRe) {
            DebugLog("Channel %s has no Match/StartsWith/Regex (ignored)", c.name.c_str());
            continue;
        }
        if (c.action != ACT_DROP) c.fp = OpenLog(c.name);
        g_channels.push_back(std::move(c));
    }
    if (g_captureAll) g_allFp = OpenLog("_all");
    DebugLog("Config loaded: %u channel(s), enabled=%d, captureAll=%d", (unsigned)g_channels.size(),
             g_enabled, g_captureAll);
}

static void MaybeReload() {
    DWORD now = GetTickCount();
    if (now - g_lastCheck < g_reloadMs) return;
    g_lastCheck = now;
    FILETIME ft;
    if (!GetFileTime(g_iniPath, ft)) return;
    if (CompareFileTime(&ft, &g_iniTime) != 0) {
        g_iniTime = ft;
        LoadConfig();
    }
}

// ---------------------------------------------------------------- filter
static bool Matches(const Channel& c, const std::string& plain, const std::string& cmp) {
    for (auto& e : c.exclude)
        if (cmp.find(e) != std::string::npos) return false;
    size_t lead = cmp.find_first_not_of(' ');
    if (lead == std::string::npos) lead = 0;
    for (auto& s : c.startsWith)
        if (cmp.compare(lead, s.size(), s) == 0) return true;
    for (auto& m : c.match)
        if (cmp.find(m) != std::string::npos) return true;
    if (c.hasRe && std::regex_search(plain, c.re)) return true;
    return false;
}

static void WriteLine(FILE* fp, const char* tag, DWORD color, const char* prefix, const char* text) {
    if (!fp) return;
    time_t t = time(nullptr);
    tm lt; localtime_s(&lt, &t);
    // Format: HH:MM:SS \t RRGGBB \t tag \t prefix \t text(with {RRGGBB} codes)
    fprintf(fp, "%02d:%02d:%02d\t%06X\t%s\t%s\t%s\n", lt.tm_hour, lt.tm_min, lt.tm_sec,
            (unsigned)(color & 0xFFFFFF), tag, Sanitize(prefix).c_str(), Sanitize(text).c_str());
    fflush(fp);
}

static bool IsEventActive(const std::string& eventName) {
    HANDLE h = OpenEventA(SYNCHRONIZE, FALSE, eventName.c_str());
    if (!h) return false;
    CloseHandle(h);
    return true;
}

static bool IsChannelActive(const Channel& c) {
    if (!g_requireMonitor) return true;
    if (!IsEventActive("Local\\AdminFilter_Master")) return false;
    if (c.action == ACT_DROP) return true;
    return IsEventActive("Local\\AdminFilter_Ch_" + Lower(c.name));
}

// returns true if message should still be shown in-game
static bool Process(int type, const char* text, const char* prefix, DWORD color) {
    MaybeReload();
    if (!text) return true;

    std::string plain = StripColors(text);
    std::string cmp = g_caseSensitive ? plain : Lower(plain);

    for (auto& c : g_channels) {
        if (type == CHAT_CHAT && !c.playerChat) continue;  // players can't spoof tags
        if (!Matches(c, plain, cmp)) continue;
        if (g_allFp) WriteLine(g_allFp, c.name.c_str(), color, prefix, text);
        if (!g_enabled || !IsChannelActive(c)) return true;  // monitor/channel off -> keep in-game!
        if (c.action != ACT_DROP) WriteLine(c.fp, c.name.c_str(), color, prefix, text);
        return c.action == ACT_COPY;
    }
    if (g_allFp) WriteLine(g_allFp, "-", color, prefix, text);
    return true;
}

// ---------------------------------------------------------------- hook
static void __fastcall HookedAddEntry(void* self, void* /*edx*/, int type, const char* text, const char* prefix,
                                      DWORD textColor, DWORD prefixColor) {
    bool show = true;
    try {
        show = Process(type, text, prefix, textColor);
    } catch (...) {
        show = true;
    }
    if (show) g_origAddEntry(self, type, text, prefix, textColor, prefixColor);
}

static uintptr_t ParseHex(const std::string& s, uintptr_t def) {
    if (s.empty()) return def;
    return (uintptr_t)strtoul(s.c_str(), nullptr, 0);
}

static DWORD WINAPI InitThread(LPVOID) {
    HMODULE samp = nullptr;
    while (!(samp = GetModuleHandleA("samp.dll"))) Sleep(100);

    // read hook settings (only once - changing these requires restart)
    std::vector<IniSection> secs;
    ReadIni(g_iniPath, secs);
    uintptr_t offset = 0x67650;           // CChat::AddEntry, 0.3.DL-R1 (verified, ret 0x14)
    DWORD expectedEP = 0xFDB60;           // samp.dll entry point, 0.3.DL-R1
    bool force = false;
    for (auto& s : secs)
        if (_stricmp(s.name.c_str(), "General") == 0) {
            offset = ParseHex(s.get("AddEntryOffset"), offset);
            expectedEP = (DWORD)ParseHex(s.get("ExpectedEntryPoint"), expectedEP);
            force = ParseBool(s.get("ForceHook"), false);
        }

    auto base = (uintptr_t)samp;
    auto dos = (IMAGE_DOS_HEADER*)base;
    auto nt = (IMAGE_NT_HEADERS*)(base + dos->e_lfanew);
    DWORD ep = nt->OptionalHeader.AddressOfEntryPoint;
    DebugLog("samp.dll @ %08X, entry point 0x%X (expected 0x%X)", (unsigned)base, (unsigned)ep,
             (unsigned)expectedEP);
    if (ep != expectedEP && !force) {
        DebugLog("Version mismatch! Not hooking (set ForceHook=1 to override). Filter disabled.");
        return 0;
    }

    g_iniTime = {};
    g_lastCheck = 0;

    void* target = (void*)(base + offset);

    // Safety: verify the function prologue so a wrong offset can never crash the game.
    // 0.3.DL-R1 CChat::AddEntry starts with: push ebp; push esi; mov ebp,ecx; push edi
    static const unsigned char kPrologue[] = {0x55, 0x56, 0x8B, 0xE9, 0x57};
    if (!force && memcmp(target, kPrologue, sizeof(kPrologue)) != 0) {
        const unsigned char* b = (const unsigned char*)target;
        DebugLog("Prologue mismatch at %08X (%02X %02X %02X %02X %02X). Not hooking (ForceHook=1 to override).",
                 (unsigned)(uintptr_t)target, b[0], b[1], b[2], b[3], b[4]);
        return 0;
    }

    if (MH_Initialize() != MH_OK) { DebugLog("MH_Initialize failed"); return 0; }
    if (MH_CreateHook(target, (void*)&HookedAddEntry, (void**)&g_origAddEntry) != MH_OK ||
        MH_EnableHook(target) != MH_OK) {
        DebugLog("Hook failed at %08X", (unsigned)(uintptr_t)target);
        return 0;
    }
    DebugLog("Hooked CChat::AddEntry @ %08X", (unsigned)(uintptr_t)target);
    return 0;
}

BOOL APIENTRY DllMain(HMODULE hModule, DWORD reason, LPVOID) {
    if (reason == DLL_PROCESS_ATTACH) {
        g_self = hModule;
        DisableThreadLibraryCalls(hModule);
        char path[MAX_PATH];
        GetModuleFileNameA(hModule, path, MAX_PATH);
        std::string p = path;
        g_baseDir = p.substr(0, p.find_last_of("\\/"));
        g_iniPath = g_baseDir + "\\AdminFilter.ini";
        g_logDir = g_baseDir + "\\AdminFilter\\logs";
        CreateDirectoryA((g_baseDir + "\\AdminFilter").c_str(), nullptr);
        g_debugLogPath = g_baseDir + "\\AdminFilter\\AdminFilter.log";
        DebugLog("===== AdminFilter.asi loaded =====");
        CreateThread(nullptr, 0, InitThread, nullptr, 0, nullptr);
    }
    return TRUE;
}
