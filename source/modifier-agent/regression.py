from pathlib import Path
import argparse, tempfile
import subprocess, shutil
parser=argparse.ArgumentParser();parser.add_argument('fixture_dir',type=Path);args=parser.parse_args()
source=Path(__file__).resolve().parent
root=Path(tempfile.mkdtemp(prefix='tourbox-modifier-regression-'))
fixture=args.fixture_dir.resolve()
src=root/'harness-src'; out=root/'harness'; src.mkdir(exist_ok=True); out.mkdir(exist_ok=True)
files={
'org/apache/log4j/Logger.java': 'package org.apache.log4j; public class Logger { public void info(Object v) {} }',
'org/apache/log4j/LogManager.java': 'package org.apache.log4j; public class LogManager { public static Logger getLogger(Class<?> c) { return new Logger(); } }',
'o0o002C239BAC/O0o002C2322B5.java': 'package o0o002C239BAC; public class O0o002C2322B5 { public static boolean o0o002C2309D1=true, o0o002C2309D0=false; }',
'o0o002C239BAC/O0o002C233594.java': 'package o0o002C239BAC; public class O0o002C233594 { public static boolean o0o002C232820=false, o0o002C2328A0=true; public static java.util.List<O0o002C236D58> o0o002C232854=java.util.List.of(new O0o002C236D58(),new O0o002C236D58()); }',
'o0o002C239BAC/O0o002C236D58.java': 'package o0o002C239BAC; public class O0o002C236D58 { public boolean o0o002C236C11=true; }',
'o0o002C239B88/O0o002C235C7A.java': 'package o0o002C239B88; public class O0o002C235C7A { public static boolean o0o002C235C79() { return true; } }',
'o0o002C239BA7/O0o002C2341AE.java': '''package o0o002C239BA7; public class O0o002C2341AE {
public static int o0o002C233EEC(int key) { return 0; }
public static Integer o0o002C233EA4(int key) { return key; }
public static Integer o0o002C2341AD(int key) { return key; }
}''',
'com/tourbox/model/jna/LibA.java': '''package com.tourbox.model.jna; public interface LibA {
LibA INSTANCE = new LibA() { public void _ZZTWN2cv12cpu_014() {} public void _ZZTWN2cv12cpu_013(int v) {} };
void _ZZTWN2cv12cpu_014();
void _ZZTWN2cv12cpu_013(int v);
}''',
'o0o002C239B88/O0o002C235A99.java': '''package o0o002C239B88;
public class O0o002C235A99 {
public static int mask, downs, missing, expected;
public static java.util.List<String> events = new java.util.ArrayList<>();
public static void o0o002C2359E5(byte m, boolean down) {
 if (down) mask |= m; else mask &= ~m;
 events.add("modifier="+m+" down="+down+" state="+mask);
}
public static void o0o002C2359F2(short key) {
 downs++; if ((mask & expected) != expected || mask != expected) missing++;
 events.add("key="+key+" state="+mask);
}
public static void o0o002C235A09(short key) {}
public static short o0o002C235899(char key,int kind) { return (short)key; }
}''',
'ModifierRegression.java': '''import java.lang.reflect.*;
import java.util.*;
import o0o002C239BA7.O0o002C234E69;
import o0o002C239B88.O0o002C235A99;
public class ModifierRegression {
 static Class<?> cls=O0o002C234E69.class;
 static void set(String name,Object v) throws Exception { Field f=cls.getDeclaredField(name);f.setAccessible(true);f.set(null,v); }
 static Object task;
 static Timer testTimer=new Timer(true);
 static void reset() throws Exception {
  Class<?> t=Class.forName("o0o002C239BA7.O0o002C234E69$O0o002C234478");
  Constructor<?> c=t.getDeclaredConstructors()[0];c.setAccessible(true);
  task=c.newInstance((byte)0,0,0,false);
  set("o0o002C23445D",testTimer);set("o0o002C23445E",task);
  set("o0o002C23446A",new java.util.concurrent.ConcurrentHashMap<>());
  set("o0o002C23446B",new HashSet<Integer>());
  O0o002C234E69.o0o002C2346B0();
  O0o002C235A99.mask=0;O0o002C235A99.downs=0;O0o002C235A99.missing=0;O0o002C235A99.events.clear();
 }
 static void send(int mask,int key,boolean hold) {
  O0o002C235A99.expected=mask;
  O0o002C234E69.o0o002C2346B6(0,(byte)mask,key,false,hold,0,0,false);
 }
 static void release(int mask,int key) { O0o002C234E69.o0o002C234891(-1,(byte)mask,key,0,false); }
 static void check(String scenario, int count, boolean expectFailure) {
  if (O0o002C235A99.downs!=count) throw new AssertionError("missing ordinary key events: "+scenario);
  boolean fail=O0o002C235A99.missing>0;
  if (fail!=expectFailure) throw new AssertionError(scenario+" invalid="+O0o002C235A99.missing+" "+O0o002C235A99.events);
  System.out.println(scenario+" key_down="+count+" wrong_modifier="+O0o002C235A99.missing);
 }
 static void button(int mask,int key) {
  o0o002C239BAC.O0o002C233594.o0o002C232854.get(1).o0o002C236C11=false;
  O0o002C235A99.expected=mask;
  O0o002C234E69.o0o002C2346B6(1,(byte)mask,key,false,true,0,0,false);
 }
 static Object get(String name) throws Exception {Field f=cls.getDeclaredField(name);f.setAccessible(true);return f.get(null);}
 static void allReleased(String scenario) throws Exception {
  if(O0o002C235A99.mask!=0 || !((Set<?>)get("o0o002C23446B")).isEmpty() ||
      !((Map<?,?>)get("o0o002C23446A")).isEmpty())
   throw new AssertionError(scenario+" ALT_OR_KEY_STUCK state="+O0o002C235A99.mask+" "+O0o002C235A99.events);
 }
 static void r1Race(boolean baseline) throws Exception {
  reset();button(4,0);
  java.util.concurrent.atomic.AtomicReference<Throwable> error=new java.util.concurrent.atomic.AtomicReference<>();
  Thread rearm=new Thread(()->{try{button(4,0);}catch(Throwable e){error.set(e);}},"R1-release-rearms-A");
  synchronized(cls) {
   rearm.start();long deadline=System.nanoTime()+2_000_000_000L;
   while(rearm.getState()!=Thread.State.BLOCKED && System.nanoTime()<deadline)Thread.yield();
   if(rearm.getState()!=Thread.State.BLOCKED)throw new AssertionError("rearm did not reach production monitor");
   // Earlier R1 key-up commits after the rearm's entry-cache invalidation,
   // before the rearm obtains the production class monitor and presses Alt.
   release(4,0);
  }
  rearm.join(2000);if(rearm.isAlive())throw new AssertionError("deadlock");
  if(error.get()!=null)throw new AssertionError(error.get());
  release(4,0);
  if(baseline) {
   if(O0o002C235A99.mask!=4)throw new AssertionError("baseline did not reproduce Alt latch");
   System.out.println("R1_BASELINE_REPRODUCED modifier_state=4 after all releases");
  } else allReleased("R1 interleaved rearm");
 }
 static void r1Checks(boolean baseline) throws Exception {
  if(baseline){r1Race(true);return;}
  for(int i=0;i<100;i++)r1Race(false);
  System.out.println("R1 interleaved rearm: 100/100 released, no modifier or held-key residue");
  for(int comboMask:new int[]{0,4,10})for(int count:new int[]{1,2,3,10,32})for(boolean aFirst:new boolean[]{false,true}) {
   reset();button(4,0);
   for(int i=0;i<count;i++) {
    release(4,0);button(comboMask,78);
    if(i==count-1 && aFirst) {release(4,0);release(comboMask,78);}
    else {release(comboMask,78);button(4,0);}
   }
   release(4,0);allReleased("R1 count="+count+" A-first="+aFirst);
   if(O0o002C235A99.downs!=count || O0o002C235A99.missing!=0)throw new AssertionError("R1 shortcut output changed");
  }
  System.out.println("R1 sequential counts 1/2/3/10/32, both release orders: PASS");
  System.out.println("R1_REGRESSION_PASS");
 }
 public static void main(String[] args) throws Exception {
  if(args[0].startsWith("r1")){r1Checks(args[0].equals("r1-baseline"));return;}
  boolean original=args[0].equals("original");
  reset();
  // Exact observed sequence: A+SCROLL pulse, then A-only release, repeated
  // inside the 100ms hold timeout. Timer cache retains mask=4 after key-up.
  for(int i=0;i<57;i++) {send(4,(i%2==0)?91:93,false);release(4,0);}
  check("A+SCROLL with A-only releases",57,original);
  if(!original) {
   for(int mask: new int[]{0,2,4,8,6,12,14}) {
    reset();for(int i=0;i<100;i++){send(mask,(i%2==0)?91:93,false);release(mask,0);}
    check("repeat mask "+mask,100,false);
    if(O0o002C235A99.mask!=0)throw new AssertionError("modifier stuck");
   }
   reset();send(4,91,false);send(4,93,false);release(4,0);check("same held mask",2,false);
   reset();send(4,91,false);send(8,93,false);release(8,0);check("mask transition",2,false);
   reset();send(4,91,true);release(4,91);check("press and hold",1,false);
   reset();send(4,91,false);set("o0o002C23445F",0L);((Runnable)task).run();
   if(O0o002C235A99.mask!=0)throw new AssertionError("timer did not release");
   send(0,93,false);check("timer then ordinary knob",2,false);
  }
  System.out.println(original?"BASELINE_REPRODUCED":"REGRESSION_PASS");
 }
}'''
}
for name,text in files.items():
 p=src/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text)
subprocess.run(['javac','-cp',str(fixture),'-d',str(out),*[str(src/n) for n in files]],check=True)
for name in ['O0o002C234E69.class','O0o002C234E69$O0o002C234477.class','O0o002C234E69$O0o002C234478.class','O0o002C235269.class']:
 p=out/'o0o002C239BA7'/name;p.parent.mkdir(exist_ok=True);shutil.copyfile(fixture/'o0o002C239BA7'/name,p)
print('Built original-bytecode regression harness')

cp=str(out)+':'+str(fixture)
subprocess.run(['java','-Xverify:all','-cp',cp,'ModifierRegression','original'],check=True)
subprocess.run(['java','-Xverify:all','-cp',cp,'ModifierRegression','r1-baseline'],check=True)
# v1 fixed rotary shortcuts but left the button-path exit unchanged.
original=(out/'o0o002C239BA7/O0o002C234E69.class').read_bytes()
v1=bytearray(original);v1[14653:14659]=bytes.fromhex('1b041db80266')
(out/'o0o002C239BA7/O0o002C234E69.class').write_bytes(v1)
print('Testing v1 R1 baseline',flush=True)
subprocess.run(['java','-Xverify:all','-cp',cp,'ModifierRegression','r1-baseline'],check=True)
jdk=Path(shutil.which('javac')).resolve().parent.parent
subprocess.run(['clang','-std=c11','-fdeclspec','-Wno-ignored-attributes','-I'+str(jdk/'include'),'-I'+str(jdk/'include/linux'),str(source/'test.c'),'-o',str(root/'test-patch')],check=True)
subprocess.run([str(root/'test-patch'),str(fixture/'o0o002C239BA7/O0o002C234E69.class'),str(out/'o0o002C239BA7/O0o002C234E69.class')],check=True)
subprocess.run(['java','-Xverify:all','-cp',cp,'ModifierRegression','patched'],check=True)
subprocess.run(['java','-Xverify:all','-cp',cp,'ModifierRegression','r1'],check=True)
shutil.rmtree(root)
