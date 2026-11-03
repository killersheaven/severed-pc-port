// ---- Stage 16: save / Continue / checkpoint diagnostics ------------------------------------------------------------
// Logs (no behaviour change): who calls StartLevel / SetStartCheckpoint and with what, plus the save data handed to the
// start-from-save routine 0xA732A0 (thiscall(this, saveData), ret 4; copies a folder + stream list + checkpoint string
// out of the save, SetStartCheckpoint(guid), then GameMainLoop->SetRequest(folder, streams)).
// Checkpoint GUIDs are derived from the name: X<user9>_<t7>_<c7>_v3 ->
//   u32 (t>>4 | user[8]<<24), u32 ((t&15)<<28 | c), user[0..7] ASCII.
struct SevCp { const char* label; const char* name; unsigned char g[16]; };
static SevCp g_sevCp[] = {
    { "initial", "XONTREALPR_CB22182_E50854D_v3" }, { "post_intro_inital", "XMARINELLO_CB806AB_62AC82F_v3" },
    { "se_pdlc1_01_02", "XA1019309X_CB35955_1403E82_v3" }, { "drill_tunnel", "XMARINELLO_CB806BD_94A94CA_v3" },
    { "elevator_hall", "XONTREALPR_CB22195_3C24AD4_v3" }, { "elevator_bottom", "XONTREALPR_CB22195_3C24ACE_v3" },
    { "se_pdlc1_01_04", "XA1019309X_CB6FA69_D84DF0F_v3" }, { "repair_room_entrance", "XONTREALPR_CB22195_3C24ABF_v3" },
    { "extraction_site", "XONTREALPR_CB22195_3C24AAC_v3" }, { "extraction_exit", "XMARINELLO_CB8077F_AA7CAE7_v3" },
    { "mining_camp_backtrack", "XONTREALPR_CB22195_3C24AB9_v3" }, { "entry_hall", "XMARINELLO_CB807EF_2DA6A31_v3" },
    { "post_moonquake", "XONTREALPR_CB22195_3C24AA3_v3" }, { "docking_station", "XONTREALPR_CB22195_3C24A9E_v3" },
    { "emergency_arrival", "XA1019309X_CB3F063_9B3373A_v3" }, { "morgue", "XA1019309X_CB3F021_442A6F3_v3" },
    { "se_pdlc1_02_04", "XA1019309X_CB6FA81_ADC565B_v3" }, { "hospital_entrance", "XA1019309X_CB3F021_91CD01D_v3" },
    { "surgery_pit", "XA1019309X_CB3F021_7425C27_v3" }, { "bathroom", "XONTREALPR_CB243CB_AB391A3_v3" },
    { "observation", "XA1019309X_CB3F021_B2490C1_v3" }, { "igc_pdlc1_02_01", "XA1019309X_CB6FA99_1FBADC9_v3" },
    { "safety_room", "XA1019309X_CB3F06B_82C4066_v3" }, { "igc_pdlc1_02_02", "XA1019309X_CB3F021_29CA6B9_v3" },
    { "landing_bay_end_fight", "XPRICE690X_CB8061A_6456EC1_v3" },
};
static const int kSevCpN = sizeof(g_sevCp) / sizeof(g_sevCp[0]);
static unsigned HexN(const char* s, int n) { unsigned v = 0; for (int i = 0; i < n; ++i) { char c = s[i]; v = v * 16 + (c >= '0' && c <= '9' ? c - '0' : c >= 'A' && c <= 'F' ? c - 'A' + 10 : c >= 'a' && c <= 'f' ? c - 'a' + 10 : 0); } return v; }
static void CpGuid(const char* n, unsigned char* g)
{
    unsigned t = HexN(n + 11, 7), c = HexN(n + 19, 7);
    uint32_t w0 = (t >> 4) | ((uint32_t)(unsigned char)n[9] << 24), w1 = ((t & 15u) << 28) | c;
    memcpy(g, &w0, 4); memcpy(g + 4, &w1, 4); memcpy(g + 8, n + 1, 8);
}
static void InitSevCp() { for (int i = 0; i < kSevCpN; ++i) CpGuid(g_sevCp[i].name, g_sevCp[i].g); }
static const char* SevCpLabel(const unsigned char* g)
{
    for (int i = 0; i < kSevCpN; ++i) if (!memcmp(g, g_sevCp[i].g, 16)) return g_sevCp[i].label;
    return nullptr;
}
static void DescribeGuid(char* out, size_t n, const unsigned char* g)
{
    const char* l = SevCpLabel(g);
    char asc[9]; for (int i = 0; i < 8; ++i) asc[i] = (g[8 + i] >= 32 && g[8 + i] < 127) ? g[8 + i] : '.'; asc[8] = 0;
    snprintf(n ? out : out, n, "%02X%02X%02X%02X %02X%02X%02X%02X [%s] %s%s", g[0], g[1], g[2], g[3], g[4], g[5], g[6], g[7], asc,
             l ? "SEVERED:" : "base/other", l ? l : "");
}

// 0xA732A0 start-from-save: prologue 81 EC 3C 01 00 00 (sub esp, 0x13C)
static const uintptr_t kFromSave = 0xA732A0;
static const unsigned char kFromSaveBytes[6] = { 0x81, 0xEC, 0x3C, 0x01, 0x00, 0x00 };
extern "C" { unsigned char* g_fsTramp = nullptr; }
static void LogStrings(const char* tag, uintptr_t p, size_t len)
{
    if (!Readable(p, len)) { Log("    %s %08X: unreadable", tag, (unsigned)p); return; }
    const unsigned char* b = (const unsigned char*)p;
    char line[600]; int pos = 0;
    for (size_t i = 0; i < len && pos < 560; )
    {
        size_t j = i; while (j < len && b[j] >= 32 && b[j] < 127) ++j;
        if (j - i >= 4) { pos += snprintf(line + pos, sizeof(line) - pos, " +%03X\"%.*s\"", (unsigned)i, (int)(j - i < 80 ? j - i : 80), (const char*)b + i); i = j; }
        else ++i;
    }
    Log("    %s %08X strings:%s", tag, (unsigned)p, pos ? line : " (none)");
}
extern "C" void __cdecl OnFromSave(uintptr_t self, const uint32_t* sp)   // sp[0] = return address, sp[1] = save data
{
    char m[160]; ModOf(m, sizeof(m), sp[0]);
    Log("FROM-SAVE 0xA732A0(this=%08X, data=%08X) from %08X (%s); current start checkpoint before: ", (unsigned)self, sp[1], sp[0], m);
    char d[160]; DescribeGuid(d, sizeof(d), (const unsigned char*)kStartCheckpointGuid); Log("    start checkpoint now: %s", d);
    LogStrings("save data", sp[1], 0x200);
    HexLine("save data[0..0x60]", sp[1], 0x60);
}
extern "C" void FromSaveStub();
asm(
    ".globl _FromSaveStub\n"
    "_FromSaveStub:\n"
    "  pushal\n"
    "  pushfl\n"
    "  leal 36(%esp), %eax\n"    // &return address
    "  pushl %eax\n"
    "  pushl %ecx\n"
    "  call _OnFromSave\n"
    "  addl $8, %esp\n"
    "  popfl\n"
    "  popal\n"
    "  jmp *_g_fsTramp\n"
);
static void InstallFromSaveHook()
{
    unsigned char* t = (unsigned char*)kFromSave;
    if (memcmp(t, kFromSaveBytes, 6) != 0) { Log("from-save hook: unexpected bytes at 0x%08X, not installed", (unsigned)kFromSave); return; }
    g_fsTramp = (unsigned char*)VirtualAlloc(nullptr, 16, MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE);
    if (!g_fsTramp) return;
    memcpy(g_fsTramp, kFromSaveBytes, 6);
    g_fsTramp[6] = 0xE9; *(int32_t*)(g_fsTramp + 7) = (int32_t)((kFromSave + 6) - ((uintptr_t)g_fsTramp + 11));
    DWORD old; VirtualProtect(t, 6, PAGE_EXECUTE_READWRITE, &old);
    t[0] = 0xE9; *(int32_t*)(t + 1) = (int32_t)((uintptr_t)&FromSaveStub - (kFromSave + 5)); t[5] = 0x90;
    VirtualProtect(t, 6, old, &old); FlushInstructionCache(GetCurrentProcess(), t, 6);
    Log("from-save hook installed at 0x%08X (log only)", (unsigned)kFromSave);
}
