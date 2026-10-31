"""Frozen content-only uint8 transforms; geometry and 114 padding stay fixed."""
import cv2
import numpy as np

GAMMA_LUT = np.rint(255 * (np.arange(256, dtype=np.float64) / 255) ** .7).astype(np.uint8)

def preprocess(image, condition, size=192):
    h,w=image.shape[:2]
    gain=min(size/h,size/w)
    nw,nh=round(w*gain),round(h*gain)
    resized=cv2.resize(image,(nw,nh),interpolation=cv2.INTER_LINEAR) if (nw,nh)!=(w,h) else image.copy()
    if condition=='gamma07':
        resized=cv2.LUT(resized,GAMMA_LUT)
    elif condition=='clahe_y2':
        ycc=cv2.cvtColor(resized,cv2.COLOR_BGR2YCrCb)
        ycc[:,:,0]=cv2.createCLAHE(clipLimit=2.,tileGridSize=(8,8)).apply(ycc[:,:,0])
        resized=cv2.cvtColor(ycc,cv2.COLOR_YCrCb2BGR)
    else:
        assert condition=='none',condition
    dx,dy=(size-nw)/2,(size-nh)/2
    padded=cv2.copyMakeBorder(resized,round(dy-.1),round(dy+.1),round(dx-.1),round(dx+.1),cv2.BORDER_CONSTANT,value=(114,114,114))
    tensor=np.ascontiguousarray(padded[...,::-1].transpose(2,0,1)[None],dtype=np.float32)*np.float32(1/255)
    return tensor,padded,{'new_width':nw,'new_height':nh,'left':round(dx-.1),'top':round(dy-.1),'gain':gain}
