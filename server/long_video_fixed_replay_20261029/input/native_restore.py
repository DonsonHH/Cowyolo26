import numpy as np
from ultralytics.engine.results import Results

def inverse(boxes,height,crop_x):
    b=np.asarray(boxes,dtype=np.float64).reshape(-1,4)
    return np.stack([b[:,1]+crop_x,height-b[:,2],b[:,3]+crop_x,height-b[:,0]],axis=1)

def controls():
    x,h=716,1440
    native=np.array([[800.5,10.25,1000.75,1400.5],[716,0,2074,1440]],np.float64)
    rotated=np.stack([h-native[:,3],native[:,0]-x,h-native[:,1],native[:,2]-x],axis=1)
    assert np.array_equal(inverse(rotated,h,x),native)
    pixels=np.arange(3*5*3).reshape(3,5,3)
    assert np.array_equal(np.rot90(np.rot90(pixels,k=-1)),pixels)
    return {'crop_offset_corner_inverse_max_error':0,'pixel_inverse_exact':True}

def callback(holder,raw,seams):
    def restore_before_tracker(predictor):
        assert len(predictor.results)==1
        result=predictor.results[0];image=holder['image'];H,W=image.shape[:2]
        left,right=holder['crop'];assert result.orig_shape==(right-left,H)
        boxes=result.boxes;assert boxes.id is None and boxes.data.shape[1]==6
        original=boxes.xyxy.detach().cpu().numpy().astype(float)
        value=boxes.data.clone()
        value[:,0]=boxes.data[:,1]+left
        value[:,1]=H-boxes.data[:,2]
        value[:,2]=boxes.data[:,3]+left
        value[:,3]=H-boxes.data[:,0]
        mapped=Results(orig_img=image,path=result.path,names=result.names,speed=result.speed,boxes=value)
        actual=mapped.boxes.xyxy.detach().cpu().numpy().astype(float)
        expected=inverse(original,H,left)
        error=float(np.max(np.abs(actual-expected))) if len(actual) else 0
        assert error<=.0005
        predictor.results[0]=mapped
        for a,b,c in zip(original,actual,boxes.conf.detach().cpu().tolist()):
            raw.append({'frame':holder['frame'],'confidence':c,'u1':a[0],'v1':a[1],'u2':a[2],'v2':a[3],
                        'x1':b[0],'y1':b[1],'x2':b[2],'y2':b[3]})
        seams.append({'frame':holder['frame'],'raw_boxes':len(actual),'native_H':H,'native_W':W,
                      'crop_left':left,'crop_right':right,'inverse_rounding_error':error,'restored_before_tracker':True})
    return restore_before_tracker
