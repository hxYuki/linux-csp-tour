#define EXPORT __declspec(dllexport)
typedef unsigned long long word;
EXPORT int getLocalBTState(void) { return 0; }
EXPORT const char *getLocalBTAddr(void) { return ""; }
EXPORT int init(void) { return 0; }
EXPORT void nativeExit(void) {}
EXPORT void scan(void) {}
EXPORT void setBTNotify(void *callback) {}
EXPORT void setCallbackByte(void *callback) {}
EXPORT void setNamePrefix(void *prefix) {}
EXPORT void setPairMode(int enabled) {}
EXPORT void setValidDeviceAddrList(void *list) {}
EXPORT void start(void) {}
EXPORT void stop(void) {}
EXPORT void writeValue(unsigned char *data, int length, int device) {}
EXPORT void setPCState(int state) {}
