#!/usr/bin/env python3
"""Reduce one reference wave (up to ten) after every map job in the wave succeeded.
Only reducer publishes patient-level count. Map intermediates may be removed after wave commit.
"""
import argparse,os,json
from pathlib import Path
import numpy as np
import nibabel as nib
p=argparse.ArgumentParser();p.add_argument('--base',default='/public/home/tanghui/GB_SDC_TrackVis');p.add_argument('--group',required=True);p.add_argument('--wave',type=int,required=True);p.add_argument('--chunk',type=int,default=50);a=p.parse_args()
b=Path(a.base);root=b/'ref_major_v1';pats=[x.strip() for x in (root/'manifests'/f'{a.group}.patients.txt').read_text().splitlines() if x.strip()];refs=[x.strip() for x in (root/'manifests/references.txt').read_text().splitlines() if x.strip()];r0=a.wave*10;r1=min(len(refs),r0+10)
if not r0<r1:raise RuntimeError('invalid wave')
template=nib.load(str(b/'PRECISE/DIFF601'/'dummy')) if False else nib.load(str(Path('/public/home/tanghui/PRECISE/DIFF601')/refs[0]/f'{refs[0]}_T1_to_MNI2mm.nii.gz'))
state=root/'states'/a.group;state.mkdir(parents=True,exist_ok=True)
for ci,first in enumerate(range(0,len(pats),a.chunk)):
 subset=pats[first:first+a.chunk]; path=state/f'c{ci:03d}.npz';wave_done=state/f'c{ci:03d}_wave{a.wave:03d}.ok'
 if wave_done.exists():print('[REDUCE_SKIP]',ci,a.wave,flush=True);continue
 if path.exists():
  with np.load(path,allow_pickle=False) as z:
   already=int(z['next_ref']); saved=list(z['patients'])
  if already==r1 and saved==subset:
   wave_done.write_text(f'{r0}\t{r1}\n');print('[RECOVER_COMMIT]',ci,a.wave,flush=True);continue
 if path.exists():
  with np.load(path,allow_pickle=False) as z:
   acc=z['counts'].copy();done=int(z['next_ref']);saved=list(z['patients'])
  if saved!=subset or done!=r0:raise RuntimeError(f'Unexpected state chunk {ci}: next_ref={done} expected={r0}')
 else:
  if r0!=0:raise RuntimeError('Missing prior accumulated state for chunk '+str(ci))
  acc=np.zeros((len(subset),)+template.shape,dtype=np.uint16)
 for ri in range(r0,r1):
  loc=root/'maps'/a.group/f'r{ri:03d}'/f'c{ci:03d}.npz';ok=loc.with_suffix('.ok')
  if not ok.exists() or not loc.exists():raise RuntimeError('Map incomplete '+str(loc))
  with np.load(loc,allow_pickle=False) as z:
   if list(z['patients'])!=subset or str(z['ref'])!=refs[ri]:raise RuntimeError('Map manifest mismatch '+str(loc))
   masks=z['mask'];
   if masks.shape!=acc.shape or masks.dtype!=np.uint8:raise RuntimeError('Bad array '+str(loc))
   acc+=masks
 tmp=state/f'.c{ci:03d}.{os.getpid()}.npz';np.savez_compressed(tmp,counts=acc,patients=np.array(subset),next_ref=np.array(r1));os.replace(tmp,path)
 wave_done.write_text(f'{r0}\t{r1}\n');print('[REDUCED]',ci,r1,flush=True)
# Final publish only after reference 601, and only when ALL chunk states verified
if r1==601:
 for ci,first in enumerate(range(0,len(pats),a.chunk)):
  subset=pats[first:first+a.chunk];loc=state/f'c{ci:03d}.npz'
  with np.load(loc,allow_pickle=False) as z:
   assert int(z['next_ref'])==601;arr=z['counts'];assert list(z['patients'])==subset
   for i,pat in enumerate(subset):
    dest=root/'final'/pat;dest.mkdir(parents=True,exist_ok=True)
    prob=arr[i].astype(np.float32)/601
    for n,data,dtype in [('SDC_reference_count',arr[i],np.uint16),('SDC_probability',prob,np.float32),('SDC_binary_p50',(prob>=.5).astype(np.uint8),np.uint8)]:
     image=nib.Nifti1Image(data,template.affine,header=template.header.copy());image.set_data_dtype(dtype);tmp=dest/f'.{n}.part.nii.gz';nib.save(image,str(tmp));os.replace(tmp,dest/f'{n}.nii.gz')
    (dest/'MERGE_SUCCESS.txt').write_text(f'MERGE_SUCCESS {pat} 601\n')
 (state/'GROUP_DONE.txt').write_text(f'{a.group} 601\n')
print('[WAVE_DONE]',a.group,a.wave,flush=True)
