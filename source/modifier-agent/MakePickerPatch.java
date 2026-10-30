import java.nio.file.*;
import jdk.internal.org.objectweb.asm.*;

/** Add an execution-time liveness check to the existing delayed Alt restore. */
public class MakePickerPatch implements Opcodes {
 static final String OWNER="o0o002C239BAC/O0o002C23488D";
 static final String LR="o0o002C239B6C/O0o002C23589B";
 static final String HOLDER="o0o002C239B71/O0o002C235B41";
 static final String CSP="o0o002C239B89/O0o002C2342A9";
 static final String KEY="o0o002C239B89/O0o002C23296F";
 static int replacements;
 static void call(MethodVisitor m,String owner,String method,String desc){m.visitMethodInsn(INVOKESTATIC,owner,method,desc,false);}
 public static void main(String[] args) throws Exception {
  ClassReader reader=new ClassReader(Files.readAllBytes(Path.of(args[0])));
  ClassWriter writer=new ClassWriter(reader,0);
  ClassVisitor visitor=new ClassVisitor(ASM8,writer){
   public MethodVisitor visitMethod(int a,String n,String d,String s,String[] e){
    MethodVisitor target=super.visitMethod(a,n,d,s,e);
    return new MethodVisitor(ASM8,target){
     public void visitInvokeDynamicInsn(String name,String desc,Handle bootstrap,Object... values){
      Object[] copy=values.clone();
      for(int i=0;i<copy.length;i++)if(copy[i] instanceof Handle h && h.getOwner().equals(KEY) && h.getName().equals("o0o002C2322B1") && h.getDesc().equals("()V")){
       copy[i]=new Handle(H_INVOKESTATIC,OWNER,"wineRestorePickerAlt","()V",false);replacements++;
      }
      super.visitInvokeDynamicInsn(name,desc,bootstrap,copy);
     }
    };
   }
   public void visitEnd(){
    MethodVisitor m=super.visitMethod(ACC_PRIVATE|ACC_STATIC,"wineRestorePickerAlt","()V",null,null);
    m.visitCode();Label csp=new Label(),send=new Label(),done=new Label();
    call(m,LR,"o0o002C235678","()L"+LR+";");m.visitMethodInsn(INVOKEVIRTUAL,LR,"o0o002C2335C2","()Z",false);m.visitJumpInsn(IFEQ,csp);
    call(m,LR,"o0o002C235678","()L"+LR+";");m.visitMethodInsn(INVOKEVIRTUAL,LR,"o0o002C2336E5","()Z",false);m.visitJumpInsn(IFEQ,send);
    m.visitLabel(csp);m.visitFrame(F_SAME,0,null,0,null);
    call(m,HOLDER,"o0o002C232E92","()L"+CSP+";");m.visitMethodInsn(INVOKEVIRTUAL,CSP,"o0o002C2335C2","()Z",false);m.visitJumpInsn(IFEQ,done);
    call(m,HOLDER,"o0o002C235B35","()L"+HOLDER+";");m.visitMethodInsn(INVOKEVIRTUAL,HOLDER,"o0o002C2336E5","()Z",false);m.visitJumpInsn(IFNE,done);
    m.visitLabel(send);m.visitFrame(F_SAME,0,null,0,null);
    call(m,KEY,"o0o002C2322B1","()V");
    m.visitLabel(done);m.visitFrame(F_SAME,0,null,0,null);m.visitInsn(RETURN);m.visitMaxs(1,0);m.visitEnd();
    super.visitEnd();
   }
  };
  reader.accept(visitor,0);
  if(replacements!=1)throw new IllegalStateException("Expected exactly one Alt-restore bootstrap, got "+replacements);
  Files.write(Path.of(args[1]),writer.toByteArray());
 }
}
