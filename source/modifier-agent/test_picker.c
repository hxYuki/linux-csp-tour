#include <assert.h>
#include <fcntl.h>
#include <stdlib.h>
#include <unistd.h>
#include "compat.c"
HANDLE GetStdHandle(DWORD k) { (void)k; return (HANDLE)2; }
BOOL WriteFile(HANDLE h, const void *b, DWORD n, DWORD *done, void *o) {
    (void)h; (void)o;
    long result = write(2,b,n); *done=result < 0 ? 0 : (DWORD)result;
    return result >= 0;
}
static int allocation_fail;
static jvmtiError allocate(jvmtiEnv *env,jlong n,unsigned char **out) {
    (void)env;
    if (allocation_fail) return JVMTI_ERROR_OUT_OF_MEMORY;
    *out=malloc((size_t)n); return *out ? JVMTI_ERROR_NONE : JVMTI_ERROR_OUT_OF_MEMORY;
}
int main(int argc,char **argv) {
 assert(argc==3);unsigned char b[PICKER_INPUT_LENGTH+1];
 int fd=open(argv[1],O_RDONLY);assert(fd>=0);assert(read(fd,b,sizeof(b))==PICKER_INPUT_LENGTH);close(fd);
 struct jvmtiInterface_1_ f={0};f.Allocate=allocate;jvmtiEnv env=&f;
 jint n=0;unsigned char *out=0;
 on_class(&env,0,0,0,PICKER_CLASS,0,PICKER_INPUT_LENGTH,b,&n,&out);
 assert(out && n==PICKER_OUTPUT_LENGTH);
 fd=open(argv[2],O_WRONLY|O_CREAT|O_TRUNC,0600);assert(fd>=0);assert(write(fd,out,n)==n);close(fd);free(out);out=0;n=0;
 b[30]^=1;on_class(&env,0,0,0,PICKER_CLASS,0,PICKER_INPUT_LENGTH,b,&n,&out);assert(!out && !n);b[30]^=1;
 on_class(&env,0,0,0,PICKER_CLASS,0,PICKER_INPUT_LENGTH-1,b,&n,&out);assert(!out && !n);
 allocation_fail=1;on_class(&env,0,0,0,PICKER_CLASS,0,PICKER_INPUT_LENGTH,b,&n,&out);assert(!out && !n);
 return 0;
}
