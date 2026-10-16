#define main hkl_test_main
#include "test.c"
#undef main
int main(int argc,char **argv){
 assert(argc==3);unsigned char input[CAPTURE_ORIGINAL_LENGTH+1];int fd=open(argv[1],O_RDONLY);assert(fd>=0);long n=read(fd,input,sizeof(input));close(fd);assert(n==CAPTURE_ORIGINAL_LENGTH);
 struct jvmtiInterface_1_ funcs={0};funcs.Allocate=allocate;jvmtiEnv env=&funcs;jint outn=0;unsigned char *out=0;
 on_class(&env,0,0,0,"o0o002C239B89/O0o002C231F41",0,n,input,&outn,&out);assert(out&&outn==n+CAPTURE_EXTRA_CP_LENGTH+CAPTURE_CODE_DELTA);
 unsigned char expected[CAPTURE_ORIGINAL_LENGTH+CAPTURE_EXTRA_CP_LENGTH+CAPTURE_CODE_DELTA];fd=open(argv[2],O_RDONLY);assert(fd>=0);assert(read(fd,expected,sizeof(expected))==outn);close(fd);assert(equal_bytes(out,expected,outn));free(out);
 out=0;outn=0;input[20]^=1;capture_patch(&env,n,input,&outn,&out);assert(!out&&!outn);capture_patch(&env,n-1,input,&outn,&out);assert(!out&&!outn);return 0;
}
