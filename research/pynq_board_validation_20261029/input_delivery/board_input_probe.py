from pathlib import Path
from datetime import datetime,timezone
import json,os,time,hashlib,sys
import cv2,numpy as np
ROOT=Path(__file__).resolve().parent;out=ROOT/'input_probe';out.mkdir(exist_ok=False)
profile=json.loads((ROOT/'protocol.json').read_text());gate=json.loads((ROOT/'input_gate.json').read_text())
assert gate['network_forwards']==0 and gate['timing_repeats_each_photo_and_rule']==3
cv2.setNumThreads(1);old=Path(profile['source_root']);rows=[];allnative=True;allfirst=True
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def pixelsha(a):return hashlib.sha256(a.tobytes()).hexdigest()
def write(p,v):
    tmp=p.with_name(p.name+'.partial')
    with tmp.open('w') as f:json.dump(v,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
    tmp.replace(p)
def baseline(image,size):
    oriented=np.rot90(image,k=-1).copy();h,w=oriented.shape[:2];g=min(size/h,size/w);small=cv2.resize(oriented,(round(w*g),round(h*g)),interpolation=cv2.INTER_LINEAR)
    dx,dy=(size-small.shape[1])/2,(size-small.shape[0])/2
    return cv2.copyMakeBorder(small,round(dy-.1),round(dy+.1),round(dx-.1),round(dx+.1),cv2.BORDER_CONSTANT,value=(114,114,114))
def candidate(image,size,resize_first):
    if resize_first:
        h,w=image.shape[:2];g=min(size/h,size/w);small=cv2.resize(image,(round(w*g),round(h*g)),interpolation=cv2.INTER_LINEAR);oriented=cv2.rotate(small,cv2.ROTATE_90_CLOCKWISE)
    else:
        oriented=cv2.rotate(image,cv2.ROTATE_90_CLOCKWISE);h,w=oriented.shape[:2];g=min(size/h,size/w);oriented=cv2.resize(oriented,(round(w*g),round(h*g)),interpolation=cv2.INTER_LINEAR)
    dx,dy=(size-oriented.shape[1])/2,(size-oriented.shape[0])/2
    return cv2.copyMakeBorder(oriented,round(dy-.1),round(dy+.1),round(dx-.1),round(dx+.1),cv2.BORDER_CONSTANT,value=(114,114,114))
for i,source in enumerate(profile['source_images']):
    path=old/source['file'];assert sha(path)==source['sha256'];start=time.perf_counter_ns();native=cv2.imread(str(path));read_ms=(time.perf_counter_ns()-start)/1e6
    assert native.shape==(1440,2560,3);a=np.rot90(native,k=-1).copy();b=cv2.rotate(native,cv2.ROTATE_90_CLOCKWISE);same=np.array_equal(a,b);allnative&=same;assert same
    row={'index':i,'query_id':source['query_id'],'source_photo_sha256':source['sha256'],'native_source_BGR_sha256':pixelsha(native),
         'native_rotated_BGR_sha256':pixelsha(a),'native_cv2_rotate_pixel_exact':same,'JPEG_read_ms':read_ms,'size_conditions':[]}
    for size in gate['sizes']:
        reference=baseline(native,size);cvnative=candidate(native,size,False);smallfirst=candidate(native,size,True)
        assert np.array_equal(reference,cvnative);delta=np.abs(reference.astype(np.int16)-smallfirst.astype(np.int16));same=bool(np.array_equal(reference,smallfirst));allfirst&=same
        file=out/(str(i).zfill(2)+'_s'+str(size)+'_inputs.npz');np.savez_compressed(file,reference_BGR=reference,cv2native_BGR=cvnative,resizefirst_BGR=smallfirst)
        timing={}
        for name,fn in [('np_rot90_copy_native_baseline',lambda:baseline(native,size)),('cv2_rotate_native',lambda:candidate(native,size,False)),('cv2_resize_before_rotate',lambda:candidate(native,size,True))]:
            if i==0:fn()
            values=[]
            for rep in range(3):
                start=time.perf_counter_ns();image=fn();values.append((time.perf_counter_ns()-start)/1e6);assert image.shape==(size,size,3)
            timing[name]=values
        row['size_conditions'].append({'size':size,'reference_BGR_sha256':pixelsha(reference),'cv2native_BGR_sha256':pixelsha(cvnative),
          'resizefirst_BGR_sha256':pixelsha(smallfirst),'native_rotate_letterbox_exact':True,'resizefirst_letterbox_exact':same,
          'resizefirst_different_channels':int(np.count_nonzero(delta)),'resizefirst_maximum_uint8_delta':int(delta.max()),
          'array_file':file.name,'array_file_sha256':sha(file),'timing_ms':timing})
    rows.append(row);write(out/'progress.json',{'PID':os.getpid(),'completed_photos':len(rows),'network_forwards':0})
    write(out/('photo_'+str(i).zfill(2)+'.json'),row);print(json.dumps({'photo':i+1,'native_exact':allnative,'resize_first_all_exact_so_far':allfirst}),flush=True)
result={'status':'BOARD_INPUT12_NATIVE_AND36_LETTERBOX_CONDITIONS_COMPLETE','board_UTC_may_be_wrong':datetime.now(timezone.utc).isoformat(),
 'PID':os.getpid(),'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'protocol_sha256':sha(ROOT/'input_gate.json'),
 'profile_protocol_sha256':sha(ROOT/'protocol.json'),'rows':rows,'native_cv2_rotation_exact_all12':allnative,
 'cv2native_letterbox_exact_all36':True,'resizefirst_letterbox_exact_all36':allfirst,
 'timed_rule_photo_size_repeats':12*3*3*3,'new_network_forwards':0,'overlay_actions':0,'new_training_updates':0,
 'native_JPEG_image_input_not_camera_measurement':True,'whole_goal_complete':False}
write(out/'summary.json',result);os.sync();write(out/'terminal.json',{'status':result['status'],'PID':os.getpid(),'summary_sha256':sha(out/'summary.json')})
print(json.dumps({k:v for k,v in result.items() if k!='rows'}),flush=True)
