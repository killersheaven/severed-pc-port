// ---- Stage 15: D3D argument guard -----------------------------------------------------------------------------------
// The game creates a PURE device (flags 0x54), so d3d9 does not validate arguments. d3d9 10.0 SetTexture
// (d3d9+0x61C50) stores the texture at device+0x2BE8+stage*4 with no bounds check; the quarry door crash is
// SetTexture(stage 177): 0x2BE8 + 177*4 = 0x2EAC = d3d9's pointer to its 16 vertex-stream records -> next draw calls
// a texture vtable as a stream record. Valid: textures 0-15 and 256-260 (D3DDMAPSAMPLER, vertex samplers),
// streams 0-15, VS float constants 0-255, PS float constants 0-223, render states < 256 (valid ones < 210).
// Invalid calls are logged (caller, args, object, stack, mesh) and dropped (return D3D_OK).
struct ArgBad { const char* what; unsigned n; };
static ArgBad g_argBad[5] = { { "SetTexture stage", 0 }, { "SetStreamSource stream", 0 }, { "SetVertexShaderConstantF range", 0 }, { "SetPixelShaderConstantF range", 0 }, { "SetRenderState state", 0 } };
static uint32_t g_texStageHist[8]; static int g_texStageHistN = 0;   // distinct bad stages seen
static void ArgLog(int kind, uintptr_t ra, const char* fmt, ...)
{
    ArgBad& b = g_argBad[kind]; ++b.n;
    if (b.n > 25 && (b.n & 1023) != 0) return;
    char m[160]; ModOf(m, sizeof(m), ra);
    char msg[400]; va_list ap; va_start(ap, fmt); vsnprintf(msg, sizeof(msg), fmt, ap); va_end(ap);
    Log("arg guard: DROPPED %s #%u from 0x%08X (%s): %s", b.what, b.n, (unsigned)ra, m, msg);
    if (b.n <= 4)
    {
        uintptr_t here; asm volatile("movl %%esp, %0" : "=r"(here));
        LogStackRets("    arg guard stack:", here, 20);
        FindMeshes("arg guard", here);
        HexLine("    caller code", ra - 48, 64);
    }
}
static bool TexStageOk(DWORD st) { return st < 16 || (st >= 256 && st <= 260); }
static bool ArgCheckTex(DWORD st, void* t, uintptr_t ra)
{
    if (TexStageOk(st)) return true;
    bool seen = false; for (int i = 0; i < g_texStageHistN; ++i) if (g_texStageHist[i] == st) seen = true;
    if (!seen && g_texStageHistN < 8) g_texStageHist[g_texStageHistN++] = st;
    char d[400]; ObjDesc(d, sizeof(d), t);
    DWORD eff = st >= 256 ? st - 240 : st;
    ArgLog(0, ra, "stage %lu (0x%lX) -> would write device+0x%lX%s | texture %p %s", (unsigned long)st, (unsigned long)st,
           (unsigned long)(0x2BE8 + 4 * eff), eff == 0xB1 ? " = d3d9 STREAM TABLE POINTER (door crash)" : "", t, d);
    return false;
}
static void DumpArgGuard()
{
    Log("    arg guard: dropped SetTexture %u (stages seen: %d), SetStreamSource %u, VS const %u, PS const %u, RenderState %u",
        g_argBad[0].n, g_texStageHistN, g_argBad[1].n, g_argBad[2].n, g_argBad[3].n, g_argBad[4].n);
    for (int i = 0; i < g_texStageHistN; ++i) Log("      bad texture stage %lu", (unsigned long)g_texStageHist[i]);
}
