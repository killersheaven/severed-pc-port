// ---- Stage 13 (1/2): buffer map + released-object tracker -------------------------------------------------------
// Buffer map: pointer -> BufInfo, open addressing with tombstones. Replaces the stage 6-12 table, which stopped
// recording after 16,384 VB/IB creations (later buffers then matched stale entries -> wrong lengths in the guards).
// Entries are removed when the buffer's external refcount reaches 0 (Release hook below).
static const unsigned kBufMapN = 65536;            // power of two
static BufInfo g_bufMap[kBufMapN];
static unsigned g_bufUsed = 0, g_bufLive = 0, g_bufRebuilds = 0;
#define BUF_TOMB ((void*)1)
static inline unsigned PtrHash(void* p, unsigned mask) { uintptr_t v = (uintptr_t)p; v ^= v >> 13; v *= 0x9E3779B1u; return (unsigned)(v >> 8) & mask; }
static BufInfo* FindBuf(void* p)
{
    if (!p || p == BUF_TOMB) return nullptr;
    unsigned h = PtrHash(p, kBufMapN - 1);
    for (unsigned k = 0; k < kBufMapN; ++k, h = (h + 1) & (kBufMapN - 1)) { void* q = g_bufMap[h].p; if (!q) return nullptr; if (q == p) return &g_bufMap[h]; }
    return nullptr;
}
static void BufRebuild()    // caller holds g_d3dCs
{
    BufInfo* tmp = (BufInfo*)VirtualAlloc(nullptr, sizeof(g_bufMap), MEM_COMMIT | MEM_RESERVE, 0x04 /*PAGE_READWRITE*/);
    if (!tmp) return;
    memcpy(tmp, g_bufMap, sizeof(g_bufMap)); memset(g_bufMap, 0, sizeof(g_bufMap)); g_bufUsed = g_bufLive = 0;
    for (unsigned i = 0; i < kBufMapN; ++i) if (tmp[i].p && tmp[i].p != BUF_TOMB)
    { unsigned h = PtrHash(tmp[i].p, kBufMapN - 1); while (g_bufMap[h].p) h = (h + 1) & (kBufMapN - 1); g_bufMap[h] = tmp[i]; ++g_bufUsed; ++g_bufLive; }
    ++g_bufRebuilds;
    // tmp is intentionally not freed (no VirtualFree import in the shim); 1.5 MB per rebuild, rebuilds are rare
}
static BufInfo* BufPut(void* p)     // caller holds g_d3dCs; returns the (cleared) slot for p
{
    if (g_bufUsed > kBufMapN * 3 / 4) BufRebuild();
    unsigned h = PtrHash(p, kBufMapN - 1); BufInfo* tomb = nullptr;
    for (unsigned k = 0; k < kBufMapN; ++k, h = (h + 1) & (kBufMapN - 1))
    {
        BufInfo& e = g_bufMap[h];
        if (e.p == p) { memset(&e, 0, sizeof(e)); e.p = p; return &e; }
        if (e.p == BUF_TOMB) { if (!tomb) tomb = &e; continue; }
        if (!e.p) { BufInfo* s = tomb ? tomb : &e; if (!tomb) ++g_bufUsed; ++g_bufLive; memset(s, 0, sizeof(*s)); s->p = p; return s; }
    }
    return nullptr;
}
static void BufDel(void* p)         // caller holds g_d3dCs
{
    BufInfo* e = FindBuf(p);
    if (e) { e->p = BUF_TOMB; if (g_bufLive) --g_bufLive; }
}

// Released-object tracker. Release (vtable slot 2) is hooked on every resource vtable seen in a Create/Set call.
// When the external refcount reaches 0 the pointer is marked dead (time, caller). Binding a dead pointer again
// (SetTexture/SetStreamSource/SetIndices/SetVertexDeclaration/SetVertexShader/SetPixelShader) is a use-after-free
// in the engine; so is a second Release on it. Creating a new object at the same address clears the mark.
enum { K_TEX = 1, K_VB, K_IB, K_DECL, K_VS, K_PS, K_OTHER };
static const char* KindName(int k) { static const char* n[] = { "?", "texture", "vertex buffer", "index buffer", "vertex decl", "vertex shader", "pixel shader", "object" }; return (k >= 0 && k <= 7) ? n[k] : "?"; }
struct DeadObj { void* p; void* vt; uint32_t relRet; DWORD tick; uint32_t info; uint16_t kind; uint16_t nrel; };
static const unsigned kDeadN = 65536;
static DeadObj g_dead[kDeadN];
static unsigned g_deadUsed = 0, g_deadResets = 0;
static DeadObj* DeadFind(void* p)
{
    if (!p || p == BUF_TOMB) return nullptr;
    unsigned h = PtrHash(p, kDeadN - 1);
    for (unsigned k = 0; k < kDeadN; ++k, h = (h + 1) & (kDeadN - 1)) { void* q = g_dead[h].p; if (!q) return nullptr; if (q == p) return &g_dead[h]; }
    return nullptr;
}
static void DeadMark(void* p, void* vt, uint32_t ret, int kind, uint32_t info)   // caller holds g_d3dCs
{
    DeadObj* e = DeadFind(p);
    if (!e)
    {
        if (g_deadUsed > kDeadN * 3 / 4) { memset(g_dead, 0, sizeof(g_dead)); g_deadUsed = 0; ++g_deadResets; }
        unsigned h = PtrHash(p, kDeadN - 1);
        while (g_dead[h].p && g_dead[h].p != BUF_TOMB) h = (h + 1) & (kDeadN - 1);
        e = &g_dead[h]; if (!e->p) ++g_deadUsed;
    }
    e->p = p; e->vt = vt; e->relRet = ret; e->tick = GetTickCount(); e->info = info; e->kind = (uint16_t)kind; e->nrel = 1;
}
static void DeadClear(void* p)       // caller holds g_d3dCs (or is a Create hook on the render thread)
{
    DeadObj* e = DeadFind(p);
    if (e) e->p = BUF_TOMB;
}

typedef ULONG (STDMETHODCALLTYPE *PFN_Release)(void*);
struct RelHook { void** vt; PFN_Release orig; PFN_Release origAddRef; int kind; };
static RelHook g_rel[96]; static volatile LONG g_nrel = 0;
static unsigned g_doubleRelN = 0, g_resurrectN = 0;
// AddRef on a released pointer (e.g. after GetTexture on a still-bound object) brings it back: clear the dead mark.
static ULONG STDMETHODCALLTYPE h_AddRef(void* o)
{
    void** vt = *(void***)o; PFN_Release orig = nullptr; LONG n = g_nrel;
    for (LONG i = 0; i < n; ++i) if (g_rel[i].vt == vt) { orig = g_rel[i].origAddRef; break; }
    if (!orig) orig = g_rel[0].origAddRef;
    if (DeadFind(o))
    {
        EnterCriticalSection(&g_d3dCs); DeadClear(o); LeaveCriticalSection(&g_d3dCs);
        if (++g_resurrectN <= 10) { uintptr_t ra = (uintptr_t)__builtin_return_address(0); char m[160]; ModOf(m, sizeof(m), ra); Log("release guard: AddRef on released object %p from 0x%08X (%s), mark cleared (#%u)", o, (unsigned)ra, m, g_resurrectN); }
    }
    return orig(o);
}
static void LogStackRets(const char* tag, uintptr_t esp, int max);
static void FindMeshes(const char* tag, uintptr_t esp);
static ULONG STDMETHODCALLTYPE h_Release(void* o)
{
    void** vt = *(void***)o;
    PFN_Release orig = nullptr; int kind = K_OTHER;
    LONG n = g_nrel;
    for (LONG i = 0; i < n; ++i) if (g_rel[i].vt == vt) { orig = g_rel[i].orig; kind = g_rel[i].kind; break; }
    if (!orig) { orig = g_rel[0].orig; Log("release hook: vtable %p not registered (object %p), using first original", vt, o); }
    uintptr_t ra = (uintptr_t)__builtin_return_address(0);
    DeadObj* d = DeadFind(o);
    if (d)
    {
        // Release on an object whose external refcount already reached 0: engine double release (destroys it while still used/bound)
        ++g_doubleRelN; ++d->nrel;
        if (g_doubleRelN <= 30 || (g_doubleRelN & 1023) == 0)
        {
            char m[160], m2[160]; ModOf(m, sizeof(m), ra); ModOf(m2, sizeof(m2), d->relRet);
            Log("release guard: DOUBLE RELEASE #%u of %s %p from 0x%08X (%s); first reached 0 %lu ms ago from 0x%08X (%s), info 0x%08X -> %s",
                g_doubleRelN, KindName(d->kind), o, (unsigned)ra, m, (unsigned long)(GetTickCount() - d->tick), (unsigned)d->relRet, m2, (unsigned)d->info,
                g_staleGuard ? "BLOCKED (object kept alive)" : "passed through");
            if (g_doubleRelN <= 4) { uintptr_t here; asm volatile("movl %%esp, %0" : "=r"(here)); LogStackRets("    release guard stack:", here, 16); FindMeshes("release guard", here); }
        }
        if (g_staleGuard) return 0;
    }
    uint32_t info = 0;
    if (kind == K_VB || kind == K_IB) { BufInfo* b = FindBuf(o); if (b) info = b->len; }
    ULONG r = orig(o);
    if (r == 0)
    {
        EnterCriticalSection(&g_d3dCs);
        DeadMark(o, vt, (uint32_t)ra, kind, info);
        if (kind == K_VB || kind == K_IB) BufDel(o);
        LeaveCriticalSection(&g_d3dCs);
    }
    return r;
}
// Hook Release on the vtable of p (once per vtable). Called from Create hooks and Set hooks.
static void WatchObj(void* p, int kind)
{
    if (!p || !g_d3dHi) return;
    void** vt = *(void***)p;
    LONG n = g_nrel;
    for (LONG i = 0; i < n; ++i) if (g_rel[i].vt == vt) return;
    EnterCriticalSection(&g_d3dCs);
    n = g_nrel;
    bool have = false; for (LONG i = 0; i < n; ++i) if (g_rel[i].vt == vt) have = true;
    if (!have && n < 96 && vt[2] != (void*)h_Release)
    {
        g_rel[n].vt = vt; g_rel[n].orig = (PFN_Release)vt[2]; g_rel[n].origAddRef = (PFN_Release)vt[1]; g_rel[n].kind = kind;
        InterlockedExchange(&g_nrel, n + 1);
        DWORD old; VirtualProtect(&vt[1], 2 * sizeof(void*), PAGE_EXECUTE_READWRITE, &old);
        vt[1] = (void*)h_AddRef; vt[2] = (void*)h_Release;
        VirtualProtect(&vt[1], 2 * sizeof(void*), old, &old);
        char m[160]; ModOf(m, sizeof(m), (uintptr_t)vt);
        Log("release hook: %s vtable %p (%s) hooked, #%ld", KindName(kind), vt, m, (long)(n + 1));
    }
    else if (!have && n >= 96) { static bool once = false; if (!once) { once = true; Log("release hook: vtable table full (96), %s vtable %p not hooked", KindName(kind), vt); } }
    LeaveCriticalSection(&g_d3dCs);
}
static unsigned g_staleN = 0;
static uint32_t g_staleMask = 0;    // bit 0-3 VB stream 0-3, bit 4 IB, bit 5 decl, bit 6 VS, bit 7 PS: dead object currently bound
// Returns true when p is a released object (and logs it).
static bool StaleCheck(const char* what, void* p, unsigned slot, uintptr_t ra)
{
    DeadObj* d = DeadFind(p);
    if (!d) return false;
    ++g_staleN;
    if (g_staleN <= 40 || (g_staleN & 1023) == 0)
    {
        char m[160], m2[160]; ModOf(m, sizeof(m), ra); ModOf(m2, sizeof(m2), d->relRet);
        Log("stale guard: RELEASED %s %p bound to slot %u from 0x%08X (%s), #%u; refcount reached 0 %lu ms ago from 0x%08X (%s), %s, info 0x%08X -> %s",
            what, p, slot, (unsigned)ra, m, g_staleN, (unsigned long)(GetTickCount() - d->tick), (unsigned)d->relRet, m2, KindName(d->kind), (unsigned)d->info,
            !g_staleGuard ? "passed through" : (d->kind == K_TEX ? "replaced with NULL" : "draws skipped while bound"));
        if (g_staleN <= 4) { uintptr_t here; asm volatile("movl %%esp, %0" : "=r"(here)); LogStackRets("    stale guard stack:", here, 16); FindMeshes("stale guard", here); }
    }
    return true;
}
static void LogStackRets(const char* tag, uintptr_t esp, int max)
{
    char st[700]; int pos = 0, f = 0;
    for (int i = 0; i < 512 && f < max; ++i)
    {
        uintptr_t a = esp + 4 * i; if (!Readable(a, 4)) break;
        uintptr_t v = *(uintptr_t*)a;
        if (v >= 0x401000 && v < 0x1B00000) { pos += snprintf(st + pos, sizeof(st) - pos, " %08X", (unsigned)v); ++f; }
    }
    Log("%s%s", tag, st);
}
