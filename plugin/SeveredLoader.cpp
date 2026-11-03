// SeveredLoader.asi - Dead Space 2 (PC) plugin for the Severed DLC port.
// Stage 16: save/Continue diagnostics: StartLevel + SetStartCheckpoint callers, start-from-save (0xA732A0) data, Severed
//           checkpoint GUIDs named in the log. No behaviour change.
// Stage 15: D3D argument guard: SetTexture stage outside 0-15/256-260 (door crash: stage 177 overwrote d3d9's stream-table
//           pointer on the pure device), stream index >= 16, VS/PS constant ranges, render state >= 256: logged and dropped.
// Stage 14: lock guard: VB/IB/texture locks go through guarded private copies; writes past a lock are logged and
//           discarded (door crash = d3d9 stream records overwritten on d3d9's heap). d3d9 stream records checked per draw.
// Stage 13: ring of the last 64 draws dumped on crash; Release hooks on D3D resources -> released objects bound again
//           (use-after-free) are logged and neutralised ([Debug] StaleGuard=1); D3D objects on the crash stack identified.
// Stage 12: names the Mesh asset (MGAE) behind skipped draws / crashes by scanning the stack.
// Stage 11: DrawIndexedPrimitive guard: draws past the bound IB/VB are logged and skipped (quarry door crash).
// Stage 10: SetTexture guard (bad texture pointers logged + replaced with NULL; quarry door crash).
// Stage 9: logs the dynamic ring-buffer lock helper 0x13D2CE0 (big requests + last 64 on crash).
// Stage 8: F9 capture adds occlusion pixel counts per draw (OCC block) and vertex-position bounds / index ranges (VB/IB lines).
// Stage 7: [Render] AmbientScale / SeveredOnly + F10 (scales the engine ambient inside Severed levels); F9 capture logs stencil state.
// Stage 4: adds Severed to the episode list (gameobj+0x980) at the first GameMainLoop entry.
// Stage 3: Trigger=newgame (StartLevel 0xA40D40 index swap) + level-list dump.
// Stage 2i: safety patch off by default ([Launch] SafetyPatch=1), stream-load log (UStreamer::Load 0x859F20).
// Stage 2e: crash logger (vectored + unhandled filter) added.
// Stage 2: level launch override from plugins\\SeveredLoader.ini [Launch] Folder= / StreamList=.
// Trigger=game (default): the first level started from the menu (New Game / Load) is replaced, so the
// title screen and menus initialise the profile and input first. Trigger=boot: replaces the first
// main-menu load (skips the menu entirely; pause menu does not work then). Empty ini = no change.
// [Launch] Checkpoint= picks the start point (a checkpoint GUID from the level list). Also logs every level request.
//
// Loaded by MarkerPatch from the game's "plugins" folder.
// Build: i686-w64-mingw32-clang++ -O2 -shared -static -o SeveredLoader.asi SeveredLoader.cpp

#include <windows.h>
#include <stdio.h>
#include <string.h>
#include <stdint.h>
#include <stdlib.h>

static HMODULE g_self = nullptr;
static bool g_triggerNewGame = false;   // Trigger=newgame: New Game starts the level-list entry whose folder = [Launch] Folder
static bool Readable(uintptr_t p, size_t n); static void ModOf(char* out, size_t n, uintptr_t a); static void HexLine(const char* tag, uintptr_t a, size_t len);
static int g_staleGuard = 1;
static int g_lockGuardIni = 1;     // [Debug] LockGuard (copied into g_lockGuard once d3dcap.inc is in scope)      // [Debug] StaleGuard=0: log only (no NULL-ing, no skipped draws, no blocked double releases)
static char g_logPath[MAX_PATH];

static void Log(const char* fmt, ...)
{
    FILE* f = fopen(g_logPath, "a");
    if (!f) return;
    SYSTEMTIME t;
    GetLocalTime(&t);
    fprintf(f, "[%02d:%02d:%02d.%03d] ", t.wHour, t.wMinute, t.wSecond, t.wMilliseconds);
    va_list ap;
    va_start(ap, fmt);
    vfprintf(f, fmt, ap);
    va_end(ap);
    fputc('\n', f);
    fclose(f);
}

// ---- Stage 7: Severed ambient compensation --------------------------------------------------
// 0x846090 (ambient getter used for g_AmbientColor): out = LightManager[0x202130C]+0x50 * 2.0, the 2.0 loaded by
// movss xmm0,[0x1AAE2C8] at 0x8460AC (f3 0f 10 05 c8 e2 aa 01). We repoint that operand to g_ambMul so the
// summed ambient can be scaled while a Severed level is loaded. Callers: 0x13D7950 (material constants), 0x6D08C7.
static float g_ambMul = 2.0f;                 // value the engine multiplies the ambient sum by (engine default 2.0)
static float g_ambScale = 1.0f;               // [Render] AmbientScale (applied on top of 2.0 inside Severed)
static int g_ambSeveredOnly = 1;              // [Render] SeveredOnly=0 applies it everywhere
static volatile bool g_inSevered = false;     // current level folder is pdlc1_ch01_mng
static bool g_ambPatched = false;
static const float kAmbSteps[] = { 1.0f, 1.5f, 2.0f, 3.0f, 5.0f, 0.5f };
static void UpdateAmbient()
{
    float m = 2.0f * ((g_inSevered || !g_ambSeveredOnly) ? g_ambScale : 1.0f);
    if (m != g_ambMul) { g_ambMul = m; Log("ambient: multiplier %.3f (scale %.2f, in Severed: %s)", m, g_ambScale, g_inSevered ? "yes" : "no"); }
}
static void PatchAmbient()
{
    unsigned char* a = reinterpret_cast<unsigned char*>(0x8460AC);
    static const unsigned char orig[8] = { 0xF3, 0x0F, 0x10, 0x05, 0xC8, 0xE2, 0xAA, 0x01 };
    if (memcmp(a, orig, 8) != 0) { Log("ambient: unexpected bytes at 0x8460AC, not patched"); return; }
    DWORD old;
    VirtualProtect(a + 4, 4, PAGE_EXECUTE_READWRITE, &old);
    *reinterpret_cast<float**>(a + 4) = &g_ambMul;
    VirtualProtect(a + 4, 4, old, &old);
    FlushInstructionCache(GetCurrentProcess(), a, 8);
    g_ambPatched = true;
    Log("ambient: 0x8460AC now reads the plugin multiplier (AmbientScale %.2f, SeveredOnly %d; F10 cycles 1/1.5/2/3/5/0.5)", g_ambScale, g_ambSeveredOnly);
    UpdateAmbient();
}
static void PollAmbientKey()
{
    static bool down = false;
    bool now = (GetAsyncKeyState(VK_F10) & 0x8000) != 0;
    if (now && !down && g_ambPatched)
    {
        int n = sizeof(kAmbSteps) / sizeof(kAmbSteps[0]), k = 0;
        for (int i = 0; i < n; ++i) if (kAmbSteps[i] == g_ambScale) { k = (i + 1) % n; break; }
        g_ambScale = kAmbSteps[k];
        Log("ambient: F10 -> scale %.2f", g_ambScale);
        UpdateAmbient();
    }
    down = now;
}



// ---- Stage 9: dynamic vertex/index ring-buffer lock helper 0x13D2CE0 (cdecl, 5+ args) ----------------
// size = align16(count*stride)+16 inside a 4 MB ring (0x400000) at [0x21287DC]; count = arg2 (arg5 when arg4 == 0x80000000),
// stride = arg3. Two door crashes (d3d9 Unlock / ntdll lock with the same bad pointer 0x15FFCF8F) come right after this.
// Logs requests over 256 KB at once and keeps the last 64 requests (caller + args) for the crash dump.
static const uintptr_t kDynLock = 0x13D2CE0;
static const unsigned char kDynLockBytes[5] = { 0x8B, 0x44, 0x24, 0x14, 0x53 };
extern "C" { unsigned char* g_dynTramp = nullptr; }
struct DynReq { uint32_t ret, a1, a2, a3, a4, a5; DWORD tick; };
static DynReq g_dynRing[64]; static volatile LONG g_dynN = 0;
static uint32_t g_dynMax = 0;
extern "C" void __cdecl OnDynLock(const uint32_t* sp)    // sp[0] = return address, sp[1..5] = args
{
    LONG n = g_dynN; g_dynN = n + 1;
    DynReq& r = g_dynRing[n & 63];
    r.ret = sp[0]; r.a1 = sp[1]; r.a2 = sp[2]; r.a3 = sp[3]; r.a4 = sp[4]; r.a5 = sp[5]; r.tick = GetTickCount();
    uint32_t count = (sp[4] == 0x80000000u) ? sp[5] : sp[2], stride = sp[3];
    unsigned long long size = (unsigned long long)count * stride;
    if (size > 0x40000ull || stride > 1024)
        Log("dynbuf: BIG request from 0x%08X: count %u stride %u = %llu bytes (args %08X %08X %08X %08X %08X)", sp[0], count, stride, size, sp[1], sp[2], sp[3], sp[4], sp[5]);
    if (size > g_dynMax) { g_dynMax = (uint32_t)(size > 0xFFFFFFFFull ? 0xFFFFFFFFu : size); if (g_dynMax > 0x10000) Log("dynbuf: new max request %u bytes from 0x%08X (count %u stride %u)", g_dynMax, sp[0], count, stride); }
}
static void DumpDynRing()
{
    LONG n = g_dynN; if (!n) return;
    Log("    dynbuf: last %d lock requests (oldest first; ret, args a1..a5, count*stride):", n < 64 ? (int)n : 64);
    for (LONG i = (n > 64 ? n - 64 : 0); i < n; ++i)
    {
        const DynReq& r = g_dynRing[i & 63];
        uint32_t count = (r.a4 == 0x80000000u) ? r.a5 : r.a2;
        Log("      #%ld ret %08X  %08X %08X %08X %08X %08X  -> %u x %u", (long)i, r.ret, r.a1, r.a2, r.a3, r.a4, r.a5, count, r.a3);
    }
}
extern "C" void DynLockStub();
asm(
    ".globl _DynLockStub\n"
    "_DynLockStub:\n"
    "  pushal\n"
    "  pushfl\n"
    "  leal 36(%esp), %eax\n"    // &return address (pushal 32 + pushfl 4)
    "  pushl %eax\n"
    "  call _OnDynLock\n"
    "  addl $4, %esp\n"
    "  popfl\n"
    "  popal\n"
    "  jmp *_g_dynTramp\n"
);
static void InstallDynLockHook()
{
    unsigned char* t = reinterpret_cast<unsigned char*>(kDynLock);
    if (memcmp(t, kDynLockBytes, 5) != 0) { Log("dynbuf hook: unexpected bytes at 0x%08X, not installed", (unsigned)kDynLock); return; }
    g_dynTramp = static_cast<unsigned char*>(VirtualAlloc(nullptr, 16, MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE));
    if (!g_dynTramp) return;
    memcpy(g_dynTramp, kDynLockBytes, 5);
    g_dynTramp[5] = 0xE9; *reinterpret_cast<int32_t*>(g_dynTramp + 6) = (int32_t)((kDynLock + 5) - ((uintptr_t)g_dynTramp + 10));
    DWORD old;
    VirtualProtect(t, 5, PAGE_EXECUTE_READWRITE, &old);
    t[0] = 0xE9; *reinterpret_cast<int32_t*>(t + 1) = (int32_t)((uintptr_t)&DynLockStub - (kDynLock + 5));
    VirtualProtect(t, 5, old, &old);
    FlushInstructionCache(GetCurrentProcess(), t, 5);
    Log("dynbuf hook installed at 0x%08X (logs requests > 256 KB; last 64 dumped on crash)", (unsigned)kDynLock);
}

// Same check MarkerPatch uses: the DRM strips the PE timestamp, the build keeps __DATE__ in .rdata.
// Only valid once the Steam stub has unpacked the image.
static bool IsBuildDate(uintptr_t va, const char* date)
{
    MEMORY_BASIC_INFORMATION mbi;
    if (!VirtualQuery(reinterpret_cast<void*>(va), &mbi, sizeof(mbi))) return false;
    if (mbi.State != MEM_COMMIT || (mbi.Protect & (PAGE_NOACCESS | PAGE_GUARD))) return false;
    return memcmp(reinterpret_cast<const void*>(va), date, strlen(date)) == 0;
}


// ---- GameMainLoop enter hook (Current build) ----------------------------------------------
// 0x40EE40: push ecx; push ebx; push esi; mov esi,ecx  (51 53 56 8B F1), thiscall, 1 stack arg, ret 4.
// It copies the request into this+0x04 and this+0x84 (the same fields "-stream a b" fills);
// this+0x104 / this+0x184 are read alongside them when the level request is built.
static const uintptr_t kGameLoopEnter = 0x40EE40;
static const unsigned char kGameLoopEnterBytes[5] = { 0x51, 0x53, 0x56, 0x8B, 0xF1 };
extern "C" { unsigned char* g_trampoline = nullptr; }
static volatile uintptr_t g_loopThis = 0;

static void DescribePtr(char* out, size_t n, uintptr_t p)
{
    MEMORY_BASIC_INFORMATION mbi;
    if (p && VirtualQuery(reinterpret_cast<void*>(p), &mbi, sizeof(mbi)) && mbi.State == MEM_COMMIT &&
        !(mbi.Protect & (PAGE_NOACCESS | PAGE_GUARD)))
    {
        const char* s = reinterpret_cast<const char*>(p);
        size_t i = 0;
        for (; i < 120 && s[i] >= 32 && s[i] < 127; ++i) {}
        if (i > 0 && s[i] == 0) { snprintf(out, n, "0x%08X \"%s\"", (unsigned)p, s); return; }
        const unsigned char* b = reinterpret_cast<const unsigned char*>(p);
        snprintf(out, n, "0x%08X [%02X %02X %02X %02X %02X %02X %02X %02X]", (unsigned)p, b[0], b[1], b[2], b[3], b[4], b[5], b[6], b[7]);
        return;
    }
    snprintf(out, n, "0x%08X", (unsigned)p);
}

static char g_launchFolder[128];
static char g_launchStream[128];
static char g_launchCheckpoint[128];

// Start-checkpoint handling, same calls as the game's own -checkpoint switch (0x40F51C):
//   CheckpointName ctor 0x4024E6 (thiscall, const char*), ToGuid 0x741420 (thiscall, out GUID*) -> GUID*,
//   SetStartCheckpoint 0xB757B0 (cdecl, const GUID*) writes the global at 0x2091820, dtor 0x401681 (thiscall).
// New Game / Load overwrite that global just before the level starts, so it is set again at GameMainLoop entry.
typedef void  (__attribute__((thiscall)) *NameCtorFn)(void* self, const char* s);
typedef void* (__attribute__((thiscall)) *NameToGuidFn)(void* self, void* outGuid);
typedef void  (__attribute__((thiscall)) *NameDtorFn)(void* self);
typedef void  (__cdecl *SetStartCheckpointFn)(const void* guid);
static const uintptr_t kStartCheckpointGuid = 0x2091820;
#include "stage16_saves.inc"

static bool SetStartCheckpoint(const char* name)
{
    alignas(16) unsigned char nameObj[512] = {};
    alignas(16) unsigned char guid[16] = {};
    reinterpret_cast<NameCtorFn>(0x4024E6)(nameObj, name);
    void* g = reinterpret_cast<NameToGuidFn>(0x741420)(nameObj, guid);
    const unsigned char* before = reinterpret_cast<const unsigned char*>(kStartCheckpointGuid);
    Log("  start checkpoint before: %02X%02X%02X%02X %02X%02X%02X%02X %02X%02X%02X%02X %02X%02X%02X%02X",
        before[0], before[1], before[2], before[3], before[4], before[5], before[6], before[7],
        before[8], before[9], before[10], before[11], before[12], before[13], before[14], before[15]);
    if (g) reinterpret_cast<SetStartCheckpointFn>(0xB757B0)(g);
    reinterpret_cast<NameDtorFn>(0x401681)(nameObj);
    const unsigned char* after = reinterpret_cast<const unsigned char*>(kStartCheckpointGuid);
    Log("  start checkpoint set to \"%s\": %02X%02X%02X%02X %02X%02X%02X%02X %02X%02X%02X%02X %02X%02X%02X%02X", name,
        after[0], after[1], after[2], after[3], after[4], after[5], after[6], after[7],
        after[8], after[9], after[10], after[11], after[12], after[13], after[14], after[15]);
    return g != nullptr;
}
// ---- SetStartCheckpoint replacement (0xB757B0, cdecl, copies 16 bytes into 0x2091820) ----------
// New Game / Load call it with their own start point and the frontend reads the global before the
// level request reaches GameMainLoop, so the override has to happen here. Until the launch swap has
// fired, every call gets the configured checkpoint instead.
static const uintptr_t kSetStartCheckpoint = 0xB757B0;
static const unsigned char kSetStartCheckpointBytes[6] = { 0x8B, 0x44, 0x24, 0x04, 0x8B, 0x08 };
static unsigned char g_ourGuid[16];
static bool g_haveGuid = false;
static volatile bool g_launchDoneFlag = false;
static bool LaunchConfigured();

static void HexGuid(char* out, const unsigned char* g)
{
    snprintf(out, 40, "%02X%02X%02X%02X %02X%02X%02X%02X %02X%02X%02X%02X %02X%02X%02X%02X", g[0], g[1], g[2], g[3],
             g[4], g[5], g[6], g[7], g[8], g[9], g[10], g[11], g[12], g[13], g[14], g[15]);
}

static bool ComputeGuid(const char* name)
{
    alignas(16) unsigned char nameObj[512] = {};
    alignas(16) unsigned char guid[16] = {};
    reinterpret_cast<NameCtorFn>(0x4024E6)(nameObj, name);
    void* g = reinterpret_cast<NameToGuidFn>(0x741420)(nameObj, guid);
    if (g) memcpy(g_ourGuid, g, 16);
    reinterpret_cast<NameDtorFn>(0x401681)(nameObj);
    return g != nullptr;
}

extern "C" void __cdecl OnSetStartCheckpoint(const unsigned char* guid)
{
    unsigned char* dst = reinterpret_cast<unsigned char*>(kStartCheckpointGuid);
    const unsigned char* src = guid;
    char a[40], b[40];
    HexGuid(a, guid);
    if (!g_triggerNewGame && !g_launchDoneFlag && LaunchConfigured() && g_launchCheckpoint[0])
    {
        if (!g_haveGuid) g_haveGuid = ComputeGuid(g_launchCheckpoint);
        if (g_haveGuid) src = g_ourGuid;
    }
    memcpy(dst, src, 16);
    HexGuid(b, dst);
    { char m[160]; uintptr_t ra = (uintptr_t)__builtin_return_address(0); ModOf(m, sizeof(m), ra); char ds[160]; DescribeGuid(ds, sizeof(ds), dst);
      Log("SetStartCheckpoint(%s) -> %s%s | from %08X (%s) | %s", a, b, src == guid ? "" : "  [replaced with launch checkpoint]", (unsigned)ra, m, ds); }
}

static bool InstallSetterHook()
{
    unsigned char* target = reinterpret_cast<unsigned char*>(kSetStartCheckpoint);
    if (memcmp(target, kSetStartCheckpointBytes, 6) != 0)
    {
        Log("SetStartCheckpoint hook: unexpected bytes, not installed");
        return false;
    }
    DWORD old;
    VirtualProtect(target, 5, PAGE_EXECUTE_READWRITE, &old);
    target[0] = 0xE9;
    *reinterpret_cast<int32_t*>(target + 1) = static_cast<int32_t>(reinterpret_cast<uintptr_t>(&OnSetStartCheckpoint) - (kSetStartCheckpoint + 5));
    VirtualProtect(target, 5, old, &old);
    FlushInstructionCache(GetCurrentProcess(), target, 5);
    Log("SetStartCheckpoint hook installed at 0x%08X", (unsigned)kSetStartCheckpoint);
    return true;
}

static bool g_triggerBoot = false;
static int g_addEpisode = 1;              // [Menu] AddEpisode=0 turns it off
static char g_menuName[128], g_menuDesc[512];   // [Menu] Name / Description (literal text; PC never loads the console string table)
static int g_safetyPatch = 0;      // [Launch] SafetyPatch=1 re-enables the model-less component-update skip (stage 2h stopgap)
static int g_logStreams = 1;       // [Launch] LogStreams=0 turns off the stream-load log   // Trigger=boot: replace the first main-menu load; Trigger=game (default): replace the first level started from the menu
static volatile bool g_launchDone = false;
static bool LaunchConfigured() { return g_launchFolder[0] && g_launchStream[0]; }

static void LoadConfig()
{
    char ini[MAX_PATH];
    strcpy(ini, g_logPath);
    char* dot = strrchr(ini, '.');
    if (dot) strcpy(dot, ".ini");
    GetPrivateProfileStringA("Launch", "Folder", "", g_launchFolder, sizeof(g_launchFolder), ini);
    GetPrivateProfileStringA("Launch", "StreamList", "", g_launchStream, sizeof(g_launchStream), ini);
    GetPrivateProfileStringA("Launch", "Checkpoint", "", g_launchCheckpoint, sizeof(g_launchCheckpoint), ini);
    char trig[32];
    GetPrivateProfileStringA("Launch", "Trigger", "game", trig, sizeof(trig), ini);
    g_triggerBoot = _stricmp(trig, "boot") == 0;
    g_triggerNewGame = _stricmp(trig, "newgame") == 0;
    g_safetyPatch = GetPrivateProfileIntA("Launch", "SafetyPatch", 0, ini);
    g_logStreams = GetPrivateProfileIntA("Launch", "LogStreams", 1, ini);
    g_addEpisode = GetPrivateProfileIntA("Menu", "AddEpisode", 1, ini);
    { char sc[32]; GetPrivateProfileStringA("Render", "AmbientScale", "1.0", sc, sizeof(sc), ini); g_ambScale = (float)atof(sc);
      if (!(g_ambScale > 0.0f && g_ambScale < 50.0f)) g_ambScale = 1.0f; }
    g_ambSeveredOnly = GetPrivateProfileIntA("Render", "SeveredOnly", 1, ini);
    g_staleGuard = GetPrivateProfileIntA("Debug", "StaleGuard", 1, ini);
    g_lockGuardIni = GetPrivateProfileIntA("Debug", "LockGuard", 1, ini);
    Log("lock guard (VB/IB/texture lock overruns): %s", g_lockGuardIni ? "on" : "off");
    Log("stale guard (released D3D objects): %s", g_staleGuard ? "on (textures NULLed, draws with other released objects skipped, double releases blocked)" : "log only");
    GetPrivateProfileStringA("Menu", "Name", "Dead Space 2: Severed", g_menuName, sizeof(g_menuName), ini);
    GetPrivateProfileStringA("Menu", "Description", "Gabe Weller tries desperately to reach his wife as his security patrol in the Titan Mines falls apart.", g_menuDesc, sizeof(g_menuDesc), ini);
    Log("menu: add Severed episode %s", g_addEpisode ? "on" : "off");
    Log("safety patch: %s, stream-load log: %s", g_safetyPatch ? "on" : "off", g_logStreams ? "on" : "off");
    if (g_launchFolder[0] && g_launchStream[0])
        Log("launch override: folder \"%s\", stream list \"%s\", trigger %s (from %s)", g_launchFolder, g_launchStream,
            g_triggerNewGame ? "newgame (New Game starts this level through the game's own StartLevel)" : g_triggerBoot ? "boot (replaces the main menu)" : "game (replaces the first level started from the menu)", ini);
    if (g_launchFolder[0] && g_launchStream[0])
        Log("launch checkpoint: %s", g_launchCheckpoint[0] ? g_launchCheckpoint : "(none, the game's own start point is kept)");
    else
        Log("launch override: off (no [Launch] Folder/StreamList in %s)", ini);
}

static void AddSeveredEpisode();
extern "C" void __cdecl OnGameLoopEnter(uintptr_t arg, uintptr_t self)
{
    AddSeveredEpisode();
    char a[200], f[128], st[128];
    DescribePtr(a, sizeof(a), arg);
    char* folder = reinterpret_cast<char*>(self + 0x04);
    char* stream = reinterpret_cast<char*>(self + 0x84);
    snprintf(f, sizeof(f), "%s", folder);
    snprintf(st, sizeof(st), "%s", stream);
    Log("GameMainLoop enter: this=0x%08X arg=%s fields at entry: \"%s\" \"%s\"", (unsigned)self, a, f, st);
    g_inSevered = strstr(f, "pdlc1_ch01_mng") != nullptr;
    UpdateAmbient();
    bool isMenu = _stricmp(stream, "frontend.str") == 0;
    bool fire = g_triggerBoot ? isMenu : (!isMenu && stream[0]);
    if (!g_launchDone && !g_triggerNewGame && g_launchFolder[0] && g_launchStream[0] && fire)
    {
        g_launchDone = true;
        strncpy(folder, g_launchFolder, 127); folder[127] = 0;
        strncpy(stream, g_launchStream, 127); stream[127] = 0;
        Log("  -> replaced %s request with \"%s\" \"%s\"", isMenu ? "main-menu" : "level", folder, stream);
        if (g_launchCheckpoint[0]) SetStartCheckpoint(g_launchCheckpoint);
        g_launchDoneFlag = true;
    }
    g_loopThis = self;
}

extern "C" void HookStub();
asm(
    ".globl _HookStub\n"
    "_HookStub:\n"
    "  pushal\n"
    "  pushfl\n"
    "  pushl %ecx\n"            // self
    "  pushl 44(%esp)\n"        // arg (ret at +36+4, arg at +40+4)
    "  call _OnGameLoopEnter\n"
    "  addl $8, %esp\n"
    "  popfl\n"
    "  popal\n"
    "  jmp *_g_trampoline\n"
);

static bool InstallGameLoopHook()
{
    unsigned char* target = reinterpret_cast<unsigned char*>(kGameLoopEnter);
    if (memcmp(target, kGameLoopEnterBytes, 5) != 0)
    {
        Log("GameMainLoop hook: unexpected bytes %02X %02X %02X %02X %02X, not installed",
            target[0], target[1], target[2], target[3], target[4]);
        return false;
    }
    g_trampoline = static_cast<unsigned char*>(VirtualAlloc(nullptr, 16, MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE));
    if (!g_trampoline) return false;
    memcpy(g_trampoline, kGameLoopEnterBytes, 5);
    g_trampoline[5] = 0xE9;
    *reinterpret_cast<int32_t*>(g_trampoline + 6) = static_cast<int32_t>((kGameLoopEnter + 5) - (reinterpret_cast<uintptr_t>(g_trampoline) + 10));
    DWORD old;
    VirtualProtect(target, 5, PAGE_EXECUTE_READWRITE, &old);
    target[0] = 0xE9;
    *reinterpret_cast<int32_t*>(target + 1) = static_cast<int32_t>(reinterpret_cast<uintptr_t>(&HookStub) - (kGameLoopEnter + 5));
    VirtualProtect(target, 5, old, &old);
    FlushInstructionCache(GetCurrentProcess(), target, 5);
    Log("GameMainLoop hook installed at 0x%08X", (unsigned)kGameLoopEnter);
    return true;
}

static LONG WINAPI UnhandledFilter(EXCEPTION_POINTERS* ep);
static void SafeStr(char* out, size_t n, uintptr_t p)
{
    MEMORY_BASIC_INFORMATION mbi;
    out[0] = 0;
    if (!p || !VirtualQuery(reinterpret_cast<void*>(p), &mbi, sizeof(mbi)) || mbi.State != MEM_COMMIT ||
        (mbi.Protect & (PAGE_NOACCESS | PAGE_GUARD))) return;
    const char* s = reinterpret_cast<const char*>(p);
    size_t i = 0;
    for (; i + 1 < n && i < 127 && s[i]; ++i) out[i] = (s[i] >= 32 && s[i] < 127) ? s[i] : '?';
    out[i] = 0;
}

// Watches the loop object's request fields and logs every change.
static void WatchLoopFields()
{
    char last[4][128] = {};
    for (;;)
    {
        uintptr_t self = g_loopThis;
        if (self)
        {
            static const unsigned offs[4] = { 0x04, 0x84, 0x104, 0x184 };
            for (int k = 0; k < 4; ++k)
            {
                char cur[128];
                SafeStr(cur, sizeof(cur), self + offs[k]);
                if (strcmp(cur, last[k]) != 0)
                {
                    Log("  loop+0x%03X = \"%s\"", offs[k], cur);
                    strcpy(last[k], cur);
                }
            }
        }
        static int tick = 0;
        if ((++tick % 20) == 0) SetUnhandledExceptionFilter(UnhandledFilter);
        Sleep(50);
    }
}


// ---- crash logger: records any access violation / fatal exception with registers and stack ----
static void ModOf(char* out, size_t n, uintptr_t a)
{
    HMODULE m = nullptr; out[0] = 0;
    if (GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
                           reinterpret_cast<LPCSTR>(a), &m) && m)
    {
        char p[MAX_PATH]; GetModuleFileNameA(m, p, MAX_PATH);
        const char* b = strrchr(p, '\\'); b = b ? b + 1 : p;
        snprintf(out, n, "%s+0x%X", b, (unsigned)(a - reinterpret_cast<uintptr_t>(m)));
    }
}
static bool Readable(uintptr_t p, size_t n)
{
    MEMORY_BASIC_INFORMATION mbi;
    if (!VirtualQuery(reinterpret_cast<void*>(p), &mbi, sizeof(mbi)) || mbi.State != MEM_COMMIT ||
        (mbi.Protect & (PAGE_NOACCESS | PAGE_GUARD))) return false;
    return p + n <= reinterpret_cast<uintptr_t>(mbi.BaseAddress) + mbi.RegionSize;
}

// MSVC RTTI: vtable[-1] -> CompleteObjectLocator {sig, off, cdOff, TypeDescriptor*, ...}; TypeDescriptor+8 = ".?AVName@@"
static bool RttiName(uintptr_t obj, char* out, size_t n)
{
    out[0] = 0;
    if (obj < 0x10000 || !Readable(obj, 4)) return false;
    uintptr_t vt = *reinterpret_cast<uintptr_t*>(obj);
    if (vt < 0x401000 || vt > 0x3800000 || !Readable(vt - 4, 4)) return false;
    uintptr_t col = *reinterpret_cast<uintptr_t*>(vt - 4);
    if (!Readable(col, 16)) return false;
    uintptr_t td = *reinterpret_cast<uintptr_t*>(col + 12);
    if (!Readable(td + 8, 4)) return false;
    const char* nm = reinterpret_cast<const char*>(td + 8);
    if (nm[0] != '.' || nm[1] != '?') return false;
    size_t i = 0;
    for (; i + 1 < n && i < 120 && nm[i] >= 32 && nm[i] < 127; ++i) out[i] = nm[i];
    out[i] = 0;
    return i > 3;
}
static void HexLine(const char* tag, uintptr_t a, size_t len)
{
    char buf[700]; int p = 0;
    if (!Readable(a, len)) { Log("    %s %08X: (unreadable)", tag, (unsigned)a); return; }
    const unsigned char* b = reinterpret_cast<const unsigned char*>(a);
    for (size_t k = 0; k < len && p < 690; ++k) p += snprintf(buf + p, sizeof(buf) - p, "%02X", b[k]);
    Log("    %s %08X: %s", tag, (unsigned)a, buf);
}

// ---- Stage 12: find loaded Mesh assets ("MGAE") referenced from the stack (directly or one object deep) and log names.
static void MeshName(uintptr_t m, char* out, size_t n)
{
    out[0] = 0;
    if (!Readable(m + 0x20, 4)) return;
    uint32_t no = *(const uint32_t*)(m + 0x20);
    if (no > 0x4000000 || !Readable(m + no, 8)) return;
    SafeStr(out, n, m + no);
}
static void FindMeshes(const char* tag, uintptr_t esp)
{
    uintptr_t seen[24]; int ns = 0;
    for (int i = 0; i < 768 && ns < 12; ++i)
    {
        uintptr_t a = esp + 4 * i;
        if (!Readable(a, 4)) break;
        uintptr_t v = *(uintptr_t*)a;
        if (v < 0x10000 || !Readable(v, 4)) continue;
        for (int k = -1; k < 48 && ns < 12; ++k)
        {
            uintptr_t m = v;
            if (k >= 0) { if (!Readable(v + 4 * k, 4)) break; m = *(uintptr_t*)(v + 4 * k); if (m < 0x10000 || !Readable(m, 4)) continue; }
            if (*(const uint32_t*)m != 0x4541474Du) continue;    // "MGAE"
            bool dup = false; for (int j = 0; j < ns; ++j) if (seen[j] == m) dup = true;
            if (dup) continue;
            seen[ns++] = m;
            char nm[128]; MeshName(m, nm, sizeof(nm));
            Log("    %s: mesh 0x%08X \"%s\" (stack[%03X]%s%d) recs %u", tag, (unsigned)m, nm, i * 4, k >= 0 ? " ->+" : "", k >= 0 ? k * 4 : 0,
                Readable(m + 0x34, 4) ? *(const uint32_t*)(m + 0x34) : 0);
        }
    }
    if (!ns) Log("    %s: no Mesh asset found near the stack", tag);
}

static void DumpExtra(CONTEXT* c)
{
    const DWORD regs[7] = { c->Eax, c->Ebx, c->Ecx, c->Edx, c->Esi, c->Edi, c->Ebp };
    const char* rn[7] = { "EAX", "EBX", "ECX", "EDX", "ESI", "EDI", "EBP" };
    char nm[128];
    for (int i = 0; i < 7; ++i)
        if (RttiName(regs[i], nm, sizeof(nm))) Log("    %s object type %s", rn[i], nm);
    // objects referenced from the stack
    int shown = 0;
    for (int i = 0; i < 256 && shown < 24; ++i)
    {
        uintptr_t a = c->Esp + 4 * i;
        if (!Readable(a, 4)) break;
        uintptr_t v = *reinterpret_cast<uintptr_t*>(a);
        if (v > 0x10000 && (v < 0x401000 || v > 0x3800000) && RttiName(v, nm, sizeof(nm)))
        {
            Log("    stack[%03X] -> %08X %s", i * 4, (unsigned)v, nm); ++shown;
        }
    }
    // code around EIP and the first return addresses (for offline disassembly)
    HexLine("code-eip", c->Eip - 96, 192);
    int found = 0;
    for (int i = 0; i < 1024 && found < 14; ++i)
    {
        uintptr_t a = c->Esp + 4 * i;
        if (!Readable(a, 4)) break;
        uintptr_t v = *reinterpret_cast<uintptr_t*>(a);
        if (v >= 0x401000 && v < 0x1B00000 && Readable(v - 5, 1))
        {
            const unsigned char* b = reinterpret_cast<const unsigned char*>(v);
            if (b[-5] == 0xE8 || b[-6] == 0xFF || b[-2] == 0xFF || b[-3] == 0xFF)   // looks like a call site
            { char t[24]; snprintf(t, sizeof(t), "code-ret%02d", found); HexLine(t, v - 160, 192); ++found; }
        }
    }
}
static void DumpDrawRing(); static void ScanD3DObjects(CONTEXT* c); static void DumpArgGuard();
static volatile LONG g_crashLogged = 0;
static void DumpException(const char* kind, EXCEPTION_POINTERS* ep)
{
    EXCEPTION_RECORD* er = ep->ExceptionRecord; CONTEXT* c = ep->ContextRecord;
    char mod[160]; ModOf(mod, sizeof(mod), (uintptr_t)er->ExceptionAddress);
    Log("=== %s exception 0x%08X at 0x%08X (%s) thread %u", kind, (unsigned)er->ExceptionCode,
        (unsigned)(uintptr_t)er->ExceptionAddress, mod, (unsigned)GetCurrentThreadId());
    if (er->ExceptionCode == EXCEPTION_ACCESS_VIOLATION && er->NumberParameters >= 2)
        Log("    %s address 0x%08X", er->ExceptionInformation[0] == 0 ? "read" : er->ExceptionInformation[0] == 1 ? "write" : "execute",
            (unsigned)er->ExceptionInformation[1]);
    Log("    EAX=%08X EBX=%08X ECX=%08X EDX=%08X ESI=%08X EDI=%08X EBP=%08X ESP=%08X EIP=%08X",
        (unsigned)c->Eax, (unsigned)c->Ebx, (unsigned)c->Ecx, (unsigned)c->Edx, (unsigned)c->Esi, (unsigned)c->Edi,
        (unsigned)c->Ebp, (unsigned)c->Esp, (unsigned)c->Eip);
    if (Readable(c->Eip, 16))
    {
        const unsigned char* b = reinterpret_cast<const unsigned char*>(c->Eip);
        Log("    code: %02X %02X %02X %02X %02X %02X %02X %02X %02X %02X %02X %02X %02X %02X %02X %02X",
            b[0], b[1], b[2], b[3], b[4], b[5], b[6], b[7], b[8], b[9], b[10], b[11], b[12], b[13], b[14], b[15]);
    }
    // registers that point at readable memory: show 32 bytes (strings / object heads help identify the asset)
    const DWORD regs[7] = { c->Eax, c->Ebx, c->Ecx, c->Edx, c->Esi, c->Edi, c->Ebp };
    const char* rn[7] = { "EAX", "EBX", "ECX", "EDX", "ESI", "EDI", "EBP" };
    for (int i = 0; i < 7; ++i)
        if (regs[i] > 0x10000 && Readable(regs[i], 32))
        {
            const unsigned char* b = reinterpret_cast<const unsigned char*>(regs[i]);
            char hex[100], txt[33];
            for (int k = 0; k < 32; ++k) { sprintf(hex + 3 * k, "%02X ", b[k]); txt[k] = (b[k] >= 32 && b[k] < 127) ? b[k] : '.'; }
            txt[32] = 0;
            Log("    [%s] %s %s", rn[i], hex, txt);
        }
    // stack: return-address candidates (inside a loaded module's code)
    char line[1024]; int pos = 0, found = 0;
    for (int i = 0; i < 1024 && found < 40; ++i)
    {
        uintptr_t a = c->Esp + 4 * i;
        if (!Readable(a, 4)) break;
        uintptr_t v = *reinterpret_cast<uintptr_t*>(a);
        if (v >= 0x401000 && v < 0x1B00000)
        {
            pos += snprintf(line + pos, sizeof(line) - pos, " %08X", (unsigned)v);
            if (++found % 10 == 0) { Log("    stack:%s", line); pos = 0; }
        }
    }
    if (pos) Log("    stack:%s", line);
    if (c->Eip == 0x1076765 && Readable(c->Esi, 0x130))    // bone-palette build: dump the skinning object
    {
        uintptr_t o = c->Esi;
        unsigned n = *reinterpret_cast<unsigned*>(o + 0xBC);
        uintptr_t tab = *reinterpret_cast<uintptr_t*>(o + 0x11C), pal = *reinterpret_cast<uintptr_t*>(o + 0x120);
        Log("    skin object 0x%08X: count(+0xBC)=%u index table(+0x11C)=0x%08X palette(+0x120)=0x%08X EDI(bone)=%u", (unsigned)o, n, (unsigned)tab, (unsigned)pal, (unsigned)c->Edi);
        HexLine("obj+0x80", o + 0x80, 0xB0);
        if (Readable(tab, 4 * (n < 200 ? n : 200))) HexLine("index table", tab, 4 * (n < 120 ? n : 120));
        char nm[128]; for (unsigned k = 0x80; k < 0x130; k += 4) { uintptr_t v = *reinterpret_cast<uintptr_t*>(o + k); if (RttiName(v, nm, sizeof(nm))) Log("    obj+0x%X -> %s", k, nm); }
    }
    DumpExtra(c);
    FindMeshes("crash", c->Esp);
    DumpDynRing();
    DumpArgGuard();
    ScanD3DObjects(c);
    DumpDrawRing();
    Log("    raw stack:");
    for (int r = 0; r < 8; ++r)
    {
        uintptr_t a = c->Esp + 32 * r;
        if (!Readable(a, 32)) break;
        const DWORD* w = reinterpret_cast<const DWORD*>(a);
        Log("      %08X: %08X %08X %08X %08X %08X %08X %08X %08X", (unsigned)a,
            (unsigned)w[0], (unsigned)w[1], (unsigned)w[2], (unsigned)w[3], (unsigned)w[4], (unsigned)w[5], (unsigned)w[6], (unsigned)w[7]);
    }
}
static LONG CALLBACK VectoredHandler(EXCEPTION_POINTERS* ep)
{
    DWORD code = ep->ExceptionRecord->ExceptionCode;
    if (code == EXCEPTION_ACCESS_VIOLATION || code == EXCEPTION_ILLEGAL_INSTRUCTION || code == EXCEPTION_INT_DIVIDE_BY_ZERO ||
        code == EXCEPTION_STACK_OVERFLOW || code == EXCEPTION_PRIV_INSTRUCTION || code == 0xC0000409 /* stack buffer overrun */ ||
        code == EXCEPTION_ARRAY_BOUNDS_EXCEEDED)
    {
        if (InterlockedIncrement(&g_crashLogged) <= 2) DumpException("first-chance", ep);
    }
    return EXCEPTION_CONTINUE_SEARCH;
}
static LONG WINAPI UnhandledFilter(EXCEPTION_POINTERS* ep)
{
    DumpException("UNHANDLED (game is crashing)", ep);
    return EXCEPTION_CONTINUE_SEARCH;
}


// ---- null-safety patches for objects whose assets are not converted yet ----

// ---- UStreamer::Load hook (0x859F20): thiscall (this, const char* name, float priority, bool flag), ret 0xC ----
// Prologue 53 55 56 57 8B F9 (push ebx/ebp/esi/edi; mov edi,ecx) = 6 bytes of whole instructions.
static const uintptr_t kStreamLoad = 0x859F20;
static const unsigned char kStreamLoadBytes[6] = { 0x53, 0x55, 0x56, 0x57, 0x8B, 0xF9 };
extern "C" { unsigned char* g_streamTramp = nullptr; }
extern "C" void __cdecl OnStreamLoad(uintptr_t self, uintptr_t name, uint32_t prio, uint32_t flag)
{
    char s[200];
    SafeStr(s, sizeof(s), name);
    float f; memcpy(&f, &prio, 4);
    Log("stream load: \"%s\" prio %.2f flag %u (streamer 0x%08X)", s, f, flag & 0xFF, (unsigned)self);
}
extern "C" void StreamHookStub();
asm(
    ".globl _StreamHookStub\n"
    "_StreamHookStub:\n"
    "  pushal\n"
    "  pushfl\n"
    "  pushl 48(%esp)\n"        // flag  (ret at +36; args at +40,+44,+48 before our pushes)
    "  pushl 48(%esp)\n"        // prio
    "  pushl 48(%esp)\n"        // name
    "  pushl %ecx\n"
    "  call _OnStreamLoad\n"
    "  addl $16, %esp\n"
    "  popfl\n"
    "  popal\n"
    "  jmp *_g_streamTramp\n"
);
static void InstallStreamHook()
{
    unsigned char* t = reinterpret_cast<unsigned char*>(kStreamLoad);
    if (memcmp(t, kStreamLoadBytes, 6) != 0) { Log("stream hook: unexpected bytes at 0x%08X, not installed", (unsigned)kStreamLoad); return; }
    g_streamTramp = static_cast<unsigned char*>(VirtualAlloc(nullptr, 16, MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE));
    if (!g_streamTramp) return;
    memcpy(g_streamTramp, kStreamLoadBytes, 6);
    g_streamTramp[6] = 0xE9;
    *reinterpret_cast<int32_t*>(g_streamTramp + 7) = (int32_t)((kStreamLoad + 6) - ((uintptr_t)g_streamTramp + 11));
    DWORD old;
    VirtualProtect(t, 6, PAGE_EXECUTE_READWRITE, &old);
    t[0] = 0xE9; *reinterpret_cast<int32_t*>(t + 1) = (int32_t)((uintptr_t)&StreamHookStub - (kStreamLoad + 5)); t[5] = 0x90;
    VirtualProtect(t, 6, old, &old);
    FlushInstructionCache(GetCurrentProcess(), t, 6);
    Log("stream-load hook installed at 0x%08X", (unsigned)kStreamLoad);
}


// ---- StartLevel (0xA40D40): thiscall(this = game object [0x201C0E4], int mode, int levelIndex), ret 8 ----
// Reads level-list entry this->levels[levelIndex] (this+0x980 = array of 0x68-byte entries, this+0x984 = count):
// +0x20 folder, +0x30 stream list, +0x40 (-> loop+0x184), +0x50 start checkpoint name, +0x64 type (0 = listed SP level).
// Called by New Game (mode 1, index 0) at 0xAAE73D / 0xAAEDCE and with a stored index at 0xA934B8.
// Prologue: 8B 44 24 04 (mov eax,[esp+4]) 83 EC 30 (sub esp,0x30) = 7 bytes.
static const uintptr_t kStartLevel = 0xA40D40;
static const unsigned char kStartLevelBytes[7] = { 0x8B, 0x44, 0x24, 0x04, 0x83, 0xEC, 0x30 };
extern "C" { unsigned char* g_slTramp = nullptr; }
static bool g_levelsDumped = false;
static volatile bool g_newGameDone = false;
static void EntryStr(char* out, size_t n, uintptr_t entry, unsigned off)
{
    out[0] = 0;
    if (!Readable(entry + off, 4)) return;
    SafeStr(out, n, *reinterpret_cast<uintptr_t*>(entry + off));
}
static void DumpLevels(uintptr_t self)
{
    if (!Readable(self + 0x980, 8)) { Log("level list: game object 0x%08X unreadable", (unsigned)self); return; }
    uintptr_t arr = *reinterpret_cast<uintptr_t*>(self + 0x980);
    unsigned n = *reinterpret_cast<unsigned*>(self + 0x984);
    Log("level list: %u entries at 0x%08X", n, (unsigned)arr);
    for (unsigned i = 0; i < n && i < 400; ++i)
    {
        uintptr_t e = arr + 0x68 * i;
        if (!Readable(e, 0x68)) { Log("  [%u] unreadable", i); break; }
        char a[96], b[96], c[96], d[96], z[96];
        EntryStr(z, sizeof(z), e, 0x10); EntryStr(a, sizeof(a), e, 0x20); EntryStr(b, sizeof(b), e, 0x30);
        EntryStr(c, sizeof(c), e, 0x40); EntryStr(d, sizeof(d), e, 0x50);
        const uint32_t* w = reinterpret_cast<const uint32_t*>(e);
        Log("  [%3u] +10 \"%s\" folder \"%s\" streams \"%s\" +40 \"%s\" start \"%s\" type %u | %08X %08X %08X %08X %08X %08X", i, z, a, b, c, d,
            (unsigned)w[0x64 / 4], (unsigned)w[0], (unsigned)w[1], (unsigned)w[2], (unsigned)w[3], (unsigned)w[0x60 / 4], (unsigned)w[0x5C / 4]);
    }
}
static int FindLevel(uintptr_t self, const char* folder)
{
    if (!Readable(self + 0x980, 8)) return -1;
    uintptr_t arr = *reinterpret_cast<uintptr_t*>(self + 0x980);
    unsigned n = *reinterpret_cast<unsigned*>(self + 0x984);
    for (unsigned i = 0; i < n && i < 400; ++i)
    {
        char a[128]; EntryStr(a, sizeof(a), arr + 0x68 * i, 0x20);
        size_t L = strlen(a); while (L && (a[L - 1] == '\\' || a[L - 1] == '/')) a[--L] = 0;
        if (_stricmp(a, folder) == 0) return (int)i;
    }
    return -1;
}
extern "C" { uint32_t g_slRet = 0; }
extern "C" void __cdecl OnStartLevel(uintptr_t self, int mode, int* pIndex)
{
    if (!g_levelsDumped) { g_levelsDumped = true; DumpLevels(self); }
    uintptr_t arr = Readable(self + 0x980, 4) ? *reinterpret_cast<uintptr_t*>(self + 0x980) : 0;
    char a[96] = "", b[96] = "", d[96] = "";
    if (arr) { uintptr_t e = arr + 0x68 * *pIndex; EntryStr(a, sizeof(a), e, 0x20); EntryStr(b, sizeof(b), e, 0x30); EntryStr(d, sizeof(d), e, 0x50); }
    { char m[160]; ModOf(m, sizeof(m), g_slRet); char ds[160]; DescribeGuid(ds, sizeof(ds), (const unsigned char*)kStartCheckpointGuid);
      Log("StartLevel(mode %d, index %d) this=0x%08X from %08X (%s): \"%s\" \"%s\" start \"%s\" | current start checkpoint %s", mode, *pIndex, (unsigned)self, (unsigned)g_slRet, m, a, b, d, ds); }
    if (g_triggerNewGame && !g_newGameDone && g_launchFolder[0])
    {
        int k = FindLevel(self, g_launchFolder);
        if (k < 0) { Log("  newgame: no level-list entry with folder \"%s\", not replaced", g_launchFolder); return; }
        g_newGameDone = true;
        *pIndex = k;
        uintptr_t e = arr + 0x68 * k; EntryStr(a, sizeof(a), e, 0x20); EntryStr(b, sizeof(b), e, 0x30); EntryStr(d, sizeof(d), e, 0x50);
        Log("  -> index replaced with %d: \"%s\" \"%s\" start \"%s\"", k, a, b, d);
    }
}
extern "C" void StartLevelStub();
asm(
    ".globl _StartLevelStub\n"
    "_StartLevelStub:\n"
    "  pushal\n"
    "  pushfl\n"
    "  movl 36(%esp), %eax\n"
    "  movl %eax, _g_slRet\n"
    "  leal 44(%esp), %eax\n"   // &levelIndex (ret +36, mode +40, index +44)
    "  pushl %eax\n"
    "  pushl 44(%esp)\n"        // mode (now at +44 after one push)
    "  pushl %ecx\n"
    "  call _OnStartLevel\n"
    "  addl $12, %esp\n"
    "  popfl\n"
    "  popal\n"
    "  jmp *_g_slTramp\n"
);
static bool InstallStartLevelHook()
{
    unsigned char* t = reinterpret_cast<unsigned char*>(kStartLevel);
    if (memcmp(t, kStartLevelBytes, 7) != 0) { Log("StartLevel hook: unexpected bytes at 0x%08X, not installed", (unsigned)kStartLevel); return false; }
    g_slTramp = static_cast<unsigned char*>(VirtualAlloc(nullptr, 16, MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE));
    if (!g_slTramp) return false;
    memcpy(g_slTramp, kStartLevelBytes, 7);
    g_slTramp[7] = 0xE9;
    *reinterpret_cast<int32_t*>(g_slTramp + 8) = (int32_t)((kStartLevel + 7) - ((uintptr_t)g_slTramp + 12));
    DWORD old;
    VirtualProtect(t, 7, PAGE_EXECUTE_READWRITE, &old);
    t[0] = 0xE9; *reinterpret_cast<int32_t*>(t + 1) = (int32_t)((uintptr_t)&StartLevelStub - (kStartLevel + 5)); t[5] = 0x90; t[6] = 0x90;
    VirtualProtect(t, 7, old, &old);
    FlushInstructionCache(GetCurrentProcess(), t, 7);
    Log("StartLevel hook installed at 0x%08X%s", (unsigned)kStartLevel, g_triggerNewGame ? " (New Game -> configured level)" : " (log only)");
    return true;
}

// ---- Stage 4: register Severed as a second episode (what the console's .lvl handler does) ----
// Episode list = gameobj([0x201C0E4]) + 0x980: {Entry* data, u32 count, u32 capacity}, entries 0x68 bytes.
// 0xA91D30 (thiscall on the list) appends a zeroed entry and returns it; 0x73AAE0 (thiscall on a 16-byte string
// field) assigns a C string. Built-in episode is filled at 0xAA0C51..0xAA0CA4: +0x00 name, +0x10 help, +0x20 folder,
// +0x30 stream list, +0x40 (NULL), +0x50 start checkpoint, +0x60 = +0x64 = 0.
// Values from weller1.lvl: $weller1_map_name, $weller1_map_desc, pdlc1_ch01_mng, pdlc1_ch01_mng.str, XONTREALPR_CB22182_E50854D_v3.
static bool g_episodeAdded = false;
typedef void* (__thiscall *AppendEntryFn)(void* list);
typedef void (__thiscall *StrAssignFn)(void* str, const char* s);
static void AddSeveredEpisode()
{
    if (g_episodeAdded || !g_addEpisode) return;
    uintptr_t game = Readable(0x201C0E4, 4) ? *reinterpret_cast<uintptr_t*>(0x201C0E4) : 0;
    if (!game || !Readable(game + 0x980, 12)) { Log("episode: game object not ready"); return; }
    if (*reinterpret_cast<unsigned*>(game + 0x984) < 1) { Log("episode: built-in episode not there yet"); return; }
    g_episodeAdded = true;
    if (FindLevel(game, "pdlc1_ch01_mng") >= 0) { Log("episode: Severed already in the episode list"); return; }
    unsigned before = *reinterpret_cast<unsigned*>(game + 0x984);
    char* e = static_cast<char*>(reinterpret_cast<AppendEntryFn>(0xA91D30)(reinterpret_cast<void*>(game + 0x980)));
    if (!e) { Log("episode: append failed"); return; }
    StrAssignFn assign = reinterpret_cast<StrAssignFn>(0x73AAE0);
    assign(e + 0x00, g_menuName);      // console uses $weller1_map_name / $weller1_map_desc from level_select.str
    assign(e + 0x10, g_menuDesc);
    assign(e + 0x20, "pdlc1_ch01_mng");
    assign(e + 0x30, "pdlc1_ch01_mng.str");
    assign(e + 0x40, "");
    assign(e + 0x50, g_launchCheckpoint[0] ? g_launchCheckpoint : "XONTREALPR_CB22182_E50854D_v3");   // [Launch] Checkpoint= picks the New Game start point
    *reinterpret_cast<uint32_t*>(e + 0x60) = 0;
    *reinterpret_cast<uint32_t*>(e + 0x64) = 0;
    Log("episode: Severed added (episodes %u -> %u, entry at 0x%08X)", before, *reinterpret_cast<unsigned*>(game + 0x984), (unsigned)(uintptr_t)e);
    DumpLevels(game);
}

struct CodePatch { uintptr_t va; unsigned char orig[11]; const char* what; };
// 0x1091790 (component update, thiscall, no args): owner = [esi+0x2C]-0x10; uses owner+0x194 (the owner's model data)
// without a null check, and the calls after it (0x1074990, vfuncs +0x20/+0x24 -> 0x109224C) need it too.
// Severed entities whose model assets are not converted yet have owner+0x194 == 0.
// Patch: jump at 0x10917A7 to a stub: if [eax+0x194] == 0 -> return (pop esi; ret); else run the original flag test.
static const CodePatch kPatch = { 0x10917A7, { 0x8B, 0x48, 0x10, 0xC1, 0xE9, 0x03, 0xF6, 0xC1, 0x01, 0x74, 0x20 },
                                  "component update: skip when the owner has no model (owner+0x194 == 0)" };
static void ApplyPatches()
{
    unsigned char* a = reinterpret_cast<unsigned char*>(kPatch.va);
    if (memcmp(a, kPatch.orig, sizeof(kPatch.orig)) != 0) { Log("patch 0x%08X (%s): unexpected bytes, skipped", (unsigned)kPatch.va, kPatch.what); return; }
    unsigned char* stub = static_cast<unsigned char*>(VirtualAlloc(nullptr, 64, MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE));
    if (!stub) { Log("patch: VirtualAlloc failed"); return; }
    unsigned char* p = stub;
    auto jmp_abs = [&](unsigned char op, uintptr_t target) {   // op = 0xE9 jmp / 0x84 (jz, 0F 84)
        if (op == 0x84) { *p++ = 0x0F; *p++ = 0x84; } else *p++ = 0xE9;
        int32_t rel = (int32_t)(target - (uintptr_t)(p + 4)); memcpy(p, &rel, 4); p += 4;
    };
    *p++ = 0x85; *p++ = 0xC0;                       // test eax,eax
    *p++ = 0x75; *p++ = 0x02;                       // jnz +2
    *p++ = 0x5E; *p++ = 0xC3;                       // pop esi; ret   (no model: skip this update)
    *p++ = 0xF6; *p++ = 0x40; *p++ = 0x10; *p++ = 0x08;   // test byte [eax+0x10], 8
    jmp_abs(0x84, 0x10917D2);                       // jz 0x10917D2 (original "flag clear" path)
    jmp_abs(0xE9, 0x10917B2);                       // jmp 0x10917B2 (original "flag set" path)
    DWORD old;
    VirtualProtect(a, 11, PAGE_EXECUTE_READWRITE, &old);
    a[0] = 0xE9; int32_t rel = (int32_t)((uintptr_t)stub - (kPatch.va + 5)); memcpy(a + 1, &rel, 4);
    memset(a + 5, 0x90, 6);
    VirtualProtect(a, 11, old, &old);
    FlushInstructionCache(GetCurrentProcess(), a, 11);
    Log("patch 0x%08X applied (stub at 0x%08X): %s", (unsigned)kPatch.va, (unsigned)(uintptr_t)stub, kPatch.what);
}


#include "d3dcap.inc"

static DWORD WINAPI Worker(LPVOID)
{
    InstallD3DHooks();
    { HANDLE fb = CreateThread(nullptr, 0, D3DFallback, nullptr, 0, nullptr); if (fb) CloseHandle(fb); }
    HMODULE game = GetModuleHandleA(nullptr);
    char exe[MAX_PATH] = {};
    GetModuleFileNameA(game, exe, MAX_PATH);
    Log("SeveredLoader stage 16 (save/Continue diagnostics; D3D argument guard; lock guard + stream-record check; draw ring + released-object guard; mesh finder; draw guard; texture guard; dynbuf lock log; F9 capture: occlusion px + VB bounds + IB ranges; ambient scale + F10, stencil in F9 capture; F9 d3d9 frame capture + constants/shaders; menu text, Severed episode, Trigger=newgame via StartLevel, launch override, crash logger, stream-load log) loaded");
    Log("exe: %s, base 0x%08X", exe, static_cast<unsigned>(reinterpret_cast<uintptr_t>(game)));
    Log("command line: %s", GetCommandLineA());
    Log("MarkerPatch (dinput8.dll) present: %s", GetModuleHandleA("dinput8.dll") ? "yes" : "no");

    // Wait (up to 60 s) for the DRM stub to unpack the image, then identify the build.
    const char* build = "unknown";
    for (int i = 0; i < 600; ++i)
    {
        if (IsBuildDate(0x1B92078, "Feb 24 2011")) { build = "Current (Steam/EA App, Feb 24 2011)"; break; }
        if (IsBuildDate(0x1B91040, "Dec 14 2010")) { build = "V1_0 (Dec 14 2010)"; break; }
        Sleep(100);
    }
    Log("game build: %s", build);
    if (strncmp(build, "Current", 7) != 0) { Log("unsupported build, plugin idle"); return 0; }
    LoadConfig();
    g_lockGuard = g_lockGuardIni;
    PatchAmbient();
    if (!InstallGameLoopHook()) return 0;
    InitSevCp();
    InstallSetterHook();   // stage 16: always (log only when Trigger=newgame)
    InstallFromSaveHook();
    InstallStartLevelHook();   // always installed: logs StartLevel calls and the level list; swaps only with Trigger=newgame
    if (LaunchConfigured() && g_safetyPatch) ApplyPatches();
    if (g_logStreams) InstallStreamHook();
    InstallDynLockHook();
    WatchLoopFields();
    return 0;
}

BOOL WINAPI DllMain(HINSTANCE inst, DWORD reason, LPVOID)
{
    if (reason == DLL_PROCESS_ATTACH)
    {
        g_self = inst;
        DisableThreadLibraryCalls(inst);
        GetModuleFileNameA(inst, g_logPath, MAX_PATH);
        char* dot = strrchr(g_logPath, '.');
        if (dot) strcpy(dot, ".log"); else strcat(g_logPath, ".log");
        AddVectoredExceptionHandler(1, VectoredHandler);
        HANDLE h = CreateThread(nullptr, 0, Worker, nullptr, 0, nullptr);
        if (h) CloseHandle(h);
    }
    return TRUE;
}
