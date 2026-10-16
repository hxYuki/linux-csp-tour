from pathlib import Path
import struct,hashlib,json,sys
u2=lambda b,p:struct.unpack_from('>H',b,p)[0]
u4=lambda b,p:struct.unpack_from('>I',b,p)[0]
p2=lambda x:struct.pack('>H',x)
p4=lambda x:struct.pack('>I',x)
if len(sys.argv) != 2: raise SystemExit('Usage: make_capture_patch.py PRIVATE_CAPTURE_CLASS')
p=Path(sys.argv[1])
b=p.read_bytes(); cp={};off=10;i=1;n=u2(b,8)
while i<n:
 tag=b[off];off+=1
 if tag==1:
  z=u2(b,off);cp[i]=b[off+2:off+2+z].decode();off+=2+z
 elif tag in (7,8,16,19,20):cp[i]=(tag,u2(b,off));off+=2
 elif tag in (3,4,9,10,11,12,17,18):cp[i]=(tag,b[off:off+4]);off+=4
 elif tag in (5,6):off+=8;i+=1
 elif tag==15:off+=3
 else:raise ValueError(tag)
 i+=1
cp_end=off;gdi=next(i for i,v in cp.items() if isinstance(v,tuple) and v[0]==7 and cp[v[1]]=='com/sun/jna/platform/win32/GDI32')
off+=6;off+=2+2*u2(b,off)
code_attr=None
for group in range(2):
 count=u2(b,off);off+=2
 for k in range(count):
  name,desc=cp[u2(b,off+2)],cp[u2(b,off+4)];na=u2(b,off+6);off+=8
  for j in range(na):
   attr=cp[u2(b,off)];ln=u4(b,off+2)
   if group==1 and name=='o0o002C231EAB' and attr=='Code':code_attr=off
   off+=6+ln
assert off==len(b) or off<len(b)
a=code_attr;assert a
c=a+14;cl=u4(b,a+10);assert cl==311
old=b[c+108:c+121];assert old==bytes.fromhex('b2012d2a190503b90147040057')
def utf(s):q=s.encode();return b'\x01'+p2(len(q))+q
extra=utf('BitBlt')+utf('(Lcom/sun/jna/platform/win32/WinDef$HDC;IIIILcom/sun/jna/platform/win32/WinDef$HDC;III)Z')+b'\x0c'+p2(n)+p2(n+1)+b'\x0b'+p2(gdi)+p2(n+2)+b'\x03'+p4(0x00cc0020)
# GDI32.INSTANCE, dst, 0,0,width,height,src,0,0,SRCCOPY; BitBlt; pop.
new=bytes.fromhex('b20136190503031c1d1904030313')+p2(n+4)+b'\xb9'+p2(n+3)+bytes([10,0,0x57])
delta=len(new)-len(old)
out=bytearray(b[:cp_end]+extra+b[cp_end:c+108]+new+b[c+121:]);out[8:10]=p2(n+5)
a2=a+len(extra);out[a2+2:a2+6]=p4(u4(b,a+2)+delta);out[a2+6:a2+8]=p2(10);out[a2+10:a2+14]=p4(cl+delta)
# Move debug entries past the nine inserted bytes. Branches and the only two
# stack-map frames precede the splice, and this method has no exception handlers.
end=c+cl; ex=u2(b,end);assert ex==0
z=end+2; count=u2(b,z);z+=2
for _ in range(count):
 kind=cp[u2(b,z)];sz=u4(b,z+2);q=z+6
 if kind=='LineNumberTable':
  for k in range(u2(b,q)):
   pos=q+2+4*k;start=u2(b,pos)
   if start>=121:struct.pack_into('>H',out,pos+len(extra)+delta,start+delta)
 elif kind in ('LocalVariableTable','LocalVariableTypeTable'):
  for k in range(u2(b,q)):
   pos=q+2+10*k;start=u2(b,pos);length=u2(b,pos+2)
   ns=start+(delta if start>=121 else 0);ne=start+length+(delta if start+length>=121 else 0)
   struct.pack_into('>HH',out,pos+len(extra)+delta,ns,ne-ns)
 elif kind=='StackMapTable':assert b[q:q+sz]==bytes.fromhex('0002fe003707011a010101')
 else:raise AssertionError(kind)
 z+=6+sz
Path('capture-patched.class').write_bytes(out)
h=2166136261
for x in b:h=((h^x)*16777619)&0xffffffff
meta={'class':'o0o002C239B89/O0o002C231F41','original_length':len(b),'original_sha256':hashlib.sha256(b).hexdigest(),'original_fnv':hex(h),'cp_end':cp_end,'cp_count':n,'code_attribute':a,'code_offset':c,'code_length':cl,'extra_cp_length':len(extra),'code_delta':delta,'patched_sha256':hashlib.sha256(out).hexdigest()}
Path('capture-patch.json').write_text(json.dumps(meta,indent=2)+'\n')
def arr(name,data):return 'static const unsigned char '+name+'[] = {'+','.join('0x%02x'%v for v in data)+'};\n'
header='/* Generated from verified Console 5.12.0 class by make_capture_patch.py. */\n'
for k,v in meta.items():
 if isinstance(v,int):header+='#define CAPTURE_'+k.upper()+' '+str(v)+'u\n'
header+='#define CAPTURE_FNV '+hex(h)+'u\n'+arr('capture_cp_extra',extra)+arr('capture_call_original',old)+arr('capture_call_replacement',new)
base=bytearray(b[:cp_end]+extra+b[cp_end:c+108]+new+b[c+121:])
fixups=[(i,x) for i,x in enumerate(out) if base[i]!=x]
header+='static const struct { unsigned int offset; unsigned char value; } capture_fixups[] = {'+','.join('{%du,0x%02x}'%v for v in fixups)+'};\n'
Path('capture_patch.h').write_text(header)
print(json.dumps(meta,indent=2))
