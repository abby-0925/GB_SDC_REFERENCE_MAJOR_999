#!/usr/bin/env python3
import argparse, pathlib, os, hashlib
p=argparse.ArgumentParser();p.add_argument('--base',default='/public/home/tanghui/GB_SDC_TrackVis');p.add_argument('--patients',default=None);p.add_argument('--references',default=None);p.add_argument('--group-size',type=int,default=999);p.add_argument('--allow-partial',action='store_true');a=p.parse_args()
b=pathlib.Path(a.base); src=pathlib.Path(a.patients or b/'manifests/ALL_patients_SDC_ids.txt'); rs=pathlib.Path(a.references or b/'manifests/ALL_patients_SDC_references.txt');out=b/'ref_major_v1';m=out/'manifests';m.mkdir(parents=True,exist_ok=True)
allp=[x.strip() for x in src.read_text().splitlines() if x.strip()]; refs=[x.strip() for x in rs.read_text().splitlines() if x.strip()]
assert len(refs)==601 and len(set(refs))==601;assert len(allp)==len(set(allp))
# Only run after old jobs ended, avoid overlapping patient outputs.
valid=[]; skipped=[]
for pat in allp:
    d=b/'results_fast_index'/pat
    mark=d/'MERGE_SUCCESS.txt'
    expected=f'MERGE_SUCCESS {pat} 601'
    names=['SDC_reference_count.nii.gz','SDC_probability.nii.gz','SDC_binary_p50.nii.gz']
    if mark.is_file() and mark.read_text().strip()==expected and all((d/n).is_file() and (d/n).stat().st_size>0 for n in names):skipped.append(pat)
    else:valid.append(pat)
assert a.group_size>0
for i in range(0,len(valid),a.group_size):
    group=f'g{i//a.group_size:03d}';target=m/f'{group}.patients.txt';text='\n'.join(valid[i:i+a.group_size])+'\n'
    if target.exists() and target.read_text()!=text:raise RuntimeError('Frozen group changed: '+str(target))
    target.write_text(text) if not target.exists() else None
refout=m/'references.txt'; reftext='\n'.join(refs)+'\n'
if refout.exists() and refout.read_text()!=reftext:raise RuntimeError('References changed')
refout.write_text(reftext) if not refout.exists() else None
(m/'skipped_completed.txt').write_text('\n'.join(skipped)+'\n')
print('Total',len(allp),'Already completed',len(skipped),'Remaining',len(valid),'Groups',(len(valid)+a.group_size-1)//a.group_size)
print('FIRST GROUP:',m/'g000.patients.txt')
