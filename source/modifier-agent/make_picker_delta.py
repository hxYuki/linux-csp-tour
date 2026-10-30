from pathlib import Path
import argparse,difflib,hashlib
p=argparse.ArgumentParser();p.add_argument('original',type=Path);p.add_argument('patched',type=Path);p.add_argument('header',type=Path);a=p.parse_args()
b=a.original.read_bytes();c=a.patched.read_bytes()
assert hashlib.sha256(b).hexdigest()=='e576c475651521cca58550c93cd5bc84da0a70a3adbae57eba9df045f76caa05'
h=2166136261
for n in b:h=((h^n)*16777619)&0xffffffff
parts=[]
for tag,i,j,k,l in difflib.SequenceMatcher(None,b,c,autojunk=False).get_opcodes():
 if tag!='equal':parts.append((i,j-i,c[k:l]))
s=f'#define PICKER_CLASS "o0o002C239BAC/O0o002C23488D"\n#define PICKER_INPUT_LENGTH {len(b)}u\n#define PICKER_OUTPUT_LENGTH {len(c)}u\n#define PICKER_FNV 0x{h:08x}u\n'
s+='typedef struct {unsigned int offset, remove, add; const unsigned char *data;} PickerEdit;\n'
for i,(_,_,data) in enumerate(parts):s+=f'static const unsigned char picker_data_{i}[]={{'+','.join(f'0x{v:02x}' for v in data or b'\0')+'};\n'
s+='static const PickerEdit picker_edits[]={\n'
for i,(offset,remove,data) in enumerate(parts):s+=f' {{{offset}u,{remove}u,{len(data)}u,picker_data_{i}}},\n'
s+='};\n'
a.header.write_text(s)
print('Picker delta:',len(parts),'edits,',sum(len(x[2]) for x in parts),'replacement bytes, input',len(b),'output',len(c))
