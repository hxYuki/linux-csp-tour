/* Wine 11.4 only. NtUserCallNoParam_DisplayModeChanged is 6 in its ntuser.h.
 * Refresh display metadata without applying a display mode or touching windows.
 */
typedef void *HANDLE;
typedef unsigned int UINT;
typedef unsigned long long UINT64;
typedef struct { int left, top, right, bottom; } RECT;
typedef struct { UINT size; RECT monitor, work; UINT flags; } MONITORINFO;
#define IMPORT __declspec(dllimport)
IMPORT UINT64 NtUserCallNoParam(UINT);
IMPORT int SetProcessDPIAware(void);
IMPORT HANDLE MonitorFromPoint(UINT64, UINT);
IMPORT int GetMonitorInfoA(HANDLE, MONITORINFO *);
IMPORT HANDLE GetStdHandle(UINT);
IMPORT int WriteFile(HANDLE, const void *, UINT, UINT *, void *);
IMPORT __declspec(noreturn) void ExitProcess(UINT);

static void text(const char *s) {
    UINT size = 0, written;
    while (s[size]) size++;
    WriteFile(GetStdHandle((UINT)-11), s, size, &written, 0);
}
static void number(int value) {
    char buf[16]; int i = 15; buf[i] = 0;
    if (value < 0) { text("-"); value = -value; }
    do { buf[--i] = '0' + value % 10; value /= 10; } while (value);
    text(buf + i);
}
void mainCRTStartup(void) {
    MONITORINFO info = {sizeof(MONITORINFO)};
    SetProcessDPIAware();
    if (!NtUserCallNoParam(6)) ExitProcess(1);
    if (!GetMonitorInfoA(MonitorFromPoint(0, 2), &info)) ExitProcess(2);
    if (info.work.right <= info.work.left || info.work.bottom <= info.work.top) ExitProcess(3);
    text("Wine display cache refreshed; primary work area ");
    number(info.work.left); text(","); number(info.work.top); text(",");
    number(info.work.right); text(","); number(info.work.bottom); text("\r\n");
    ExitProcess(0);
}
