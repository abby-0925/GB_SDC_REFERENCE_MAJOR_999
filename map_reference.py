#!/usr/bin/env python3
"""One healthy reference per process, 50 patients per independently resumable chunk.
Uses the same fiber voxelization and FSL transformation helpers as the existing FAST prototype.
"""
import argparse,os,sys,tempfile,time,json
from pathlib import Path
import numpy as np
import nibabel as nib
p=argparse.ArgumentParser();p.add_argument('--base',default='/public/home/tanghui/GB_SDC_TrackVis');p.add_argument('--group',required=True);p.add_argument('--reference-index',type=int,required=True);p.add_argument('--patient-chunk',type=int,default=50);p.add_argument('--sample-step',type=float,default=.45);a=p.parse_args()
b=Path(a.base);sys.path.insert(0,str(b/'scripts'));import fast_batch as fast
root=b/'ref_major_v1'; pats=[x.strip() for x in (root/'manifests'/f'{a.group}.patients.txt').read_text().splitlines() if x.strip()];refs=[x.strip() for x in (root/'manifests/references.txt').read_text().splitlines() if x.strip()]
if not 0<=a.reference_index<len(refs):raise SystemExit('bad reference index')
ref=refs[a.reference_index]; d=fast.HROOT/ref; fa=d/f'{ref}_FA.nii.gz';tr=d/f'{ref}_track_s.trk';t1=d/f'{ref}_ses-001_T1w_biascorr_brain.nii.gz';t1fa=d/f'{ref}_T1_to_FA_mat';fat1=d/f'{ref}_FA_to_T1_mat';fwd=d/f'{ref}_T1_to_MNI2mm_warp.nii.gz';inv=b/'shared_invwarp'/ref/'invwarp_T1.nii.gz';template=fast.HROOT/refs[0]/f'{refs[0]}_T1_to_MNI2mm.nii.gz'
for f in [fa,tr,t1,t1fa,fat1,fwd,inv,template]:
 if not f.is_file() or not f.stat().st_size:raise RuntimeError(f'Missing {f}')
target=root/'maps'/a.group/f'r{a.reference_index:03d}';target.mkdir(parents=True,exist_ok=True)
# immutable patient chunk size per group
meta=target/'config.json'; conf={'group':a.group,'ref_index':a.reference_index,'ref':ref,'chunk':a.patient_chunk,'patients':pats,'sample_step':a.sample_step}
if meta.exists() and json.loads(meta.read_text())!=conf:raise RuntimeError('Changed map configuration')
if not meta.exists():meta.write_text(json.dumps(conf))
faimg=nib.load(str(fa));tmpl=nib.load(str(template));assert tmpl.ndim==3
inc,nfib,diff=fast.build_index(tr,faimg,a.sample_step);print(f'[INDEX] {ref} fibers={nfib} nnz={inc.nnz} difference_mm={diff:.5f}',flush=True)
for ci,first in enumerate(range(0,len(pats),a.patient_chunk)):
 out=target/f'c{ci:03d}.npz'; ok=target/f'c{ci:03d}.ok';subset=pats[first:first+a.patient_chunk]
 if ok.exists() and out.exists() and out.stat().st_size:
  try:
   with np.load(out,allow_pickle=False) as z:
    if list(z['patients'])==subset and str(z['ref'])==ref and z['mask'].shape==(len(subset),)+tmpl.shape:print('[SKIP]',ref,ci,flush=True);continue
  except Exception:pass
  raise RuntimeError('Broken committed chunk: '+str(out))
 masks=np.zeros((len(subset),)+tmpl.shape,dtype=np.uint8);stats=[];t0=time.time()
 with tempfile.TemporaryDirectory(prefix='sdc_ref_',dir=os.environ.get('SLURM_TMPDIR') if os.path.isdir(os.environ.get('SLURM_TMPDIR','')) else None) as td:
  tmp=Path(td)
  for pi,pat in enumerate(subset):
   lesion=fast.LROOT/pat/f'{pat}_lesion_mask_to_MNI152_2mm.nii.gz';le=nib.load(str(lesion))
   if le.shape!=tmpl.shape or not np.allclose(le.affine,tmpl.affine,atol=1e-3):raise RuntimeError('MNI mismatch '+pat)
   lt=tmp/'lesion_T1.nii.gz';lf=tmp/'lesion_FA.nii.gz';fm=tmp/'disconnect_FA.nii.gz';mm=tmp/'disconnect_MNI.nii.gz'
   fast.run(['/public/apps/neuroscience/fsl/6.0.4/bin/applywarp','--in='+str(lesion),'--ref='+str(t1),'--warp='+str(inv),'--interp=nn','--out='+str(lt)])
   fast.run(['/public/apps/neuroscience/fsl/6.0.4/bin/flirt','-in',str(lt),'-ref',str(fa),'-applyxfm','-init',str(t1fa),'-interp','nearestneighbour','-out',str(lf)])
   mask=nib.load(str(lf)).get_fdata(dtype=np.float32)>0.5
   if mask.shape!=faimg.shape[:3] or not np.any(mask):raise RuntimeError('Empty FA ROI '+pat+'/'+ref)
   vox,selected=fast.select_full_fibers(inc,mask)
   if selected:
    ni=nib.Nifti1Image(vox.reshape(faimg.shape[:3]),faimg.affine,header=faimg.header.copy());ni.set_data_dtype(np.uint8);nib.save(ni,str(fm))
    fast.run(['/public/apps/neuroscience/fsl/6.0.4/bin/applywarp','--in='+str(fm),'--ref='+str(template),'--warp='+str(fwd),'--premat='+str(fat1),'--interp=nn','--out='+str(mm)])
    im=nib.load(str(mm));
    if im.shape!=tmpl.shape or not np.allclose(im.affine,tmpl.affine,atol=1e-3):raise RuntimeError('Output geometry mismatch '+pat)
    masks[pi]=np.asarray(im.dataobj)>0
   stats.append([pat,int(selected)])
 tmpout=target/f'.c{ci:03d}.{os.getpid()}.npz';np.savez_compressed(tmpout,mask=masks,patients=np.array(subset),ref=np.array(ref),selected=np.array([v for _,v in stats],dtype=np.int32));os.replace(tmpout,out)
 # commit marker last
 ok.write_text(f'{ref}\t{ci}\t{len(subset)}\n');print(f'[CHUNK_DONE] ref={ref} chunk={ci} n={len(subset)} seconds={time.time()-t0:.1f}',flush=True)
print('[REFERENCE_DONE]',a.group,ref,flush=True)
