"""Double precision clipped rotated-reference geometry and one-to-one pairing."""
import math
import numpy as np
def area(poly):
    return abs(sum(a[0]*b[1]-a[1]*b[0] for a,b in zip(poly,poly[1:]+poly[:1])))/2 if len(poly)>=3 else 0.
def clip(poly,box):
    p=[list(map(float,x)) for x in poly]
    for axis,value,keep_high in [(0,box[0],True),(0,box[2],False),(1,box[1],True),(1,box[3],False)]:
        result=[]
        if not p:break
        inside=lambda x:x[axis]>=value if keep_high else x[axis]<=value
        for a,b in zip(p,p[1:]+p[:1]):
            ina,inb=inside(a),inside(b)
            if ina:result.append(a)
            if ina!=inb:
                f=(value-a[axis])/(b[axis]-a[axis]);q=[a[j]+f*(b[j]-a[j]) for j in range(2)];q[axis]=float(value);result.append(q)
        p=result
    return p
def envelope(poly):
    assert poly;return [min(p[0] for p in poly),min(p[1] for p in poly),max(p[0] for p in poly),max(p[1] for p in poly)]
def reference(row,width=1280,height=720):
    x,y,w,h,theta=row['bbox_xywh_angle_rad'];cx=x+w/2;cy=y+h/2;c=math.cos(theta);s=math.sin(theta)
    full=[[cx+c*dx-s*dy,cy+s*dx+c*dy] for dx,dy in [(-w/2,-h/2),(w/2,-h/2),(w/2,h/2),(-w/2,h/2)]]
    visible=clip(full,[0,0,width,height]);varea=area(visible);assert varea>0
    aabb=envelope(visible);aabbarea=(aabb[2]-aabb[0])*(aabb[3]-aabb[1]);fraction=varea/(w*h)
    return {**row,'full_native_quad':full,'visible_native_polygon':visible,'full_reference_area':w*h,'visible_reference_area':varea,
    'visible_reference_fraction':fraction,'reference_complete':fraction>=1-1e-8,'visible_reference_AABB':aabb,
    'ideal_AABB_reference_fraction':varea/aabbarea,'ideal_AABB_exterior_fraction':1-varea/aabbarea,
    'long_side':max(w,h),'short_side':min(w,h),'long_axis_angle_rad_mod_pi':(theta+(math.pi/2 if h>w else 0))%math.pi}
def ious(refs,preds):
    if not refs or not preds:return np.zeros((len(refs),len(preds)))
    a=np.asarray(refs,dtype=float);b=np.asarray(preds,dtype=float)
    lo=np.maximum(a[:,None,:2],b[None,:,:2]);hi=np.minimum(a[:,None,2:],b[None,:,2:]);intersection=np.maximum(0,hi-lo).prod(2)
    aa=((a[:,2]-a[:,0])*(a[:,3]-a[:,1]))[:,None];bb=((b[:,2]-b[:,0])*(b[:,3]-b[:,1]))[None,:]
    return intersection/np.maximum(aa+bb-intersection,1e-30)
def assign(references,predictions,threshold=.5):
    from scipy.optimize import linear_sum_assignment
    n,m=len(references),len(predictions)
    if not n or not m:return [],ious(references,predictions)
    matrix=ious(references,predictions);size=n+m;bonus=size+1.
    reward=np.zeros((size,size));reward[:n,:m]=np.where(matrix>=threshold,bonus+matrix,-100*bonus)
    rr,cc=linear_sum_assignment(-reward)
    return [(int(i),int(j),float(matrix[i,j])) for i,j in zip(rr,cc) if i<n and j<m and matrix[i,j]>=threshold],matrix
def crop_box(box,width=1280,height=720):
    x1,y1,x2,y2=box
    return [max(0,math.floor(x1)),max(0,math.floor(y1)),min(width,math.ceil(x2)),min(height,math.ceil(y2))]
def crop_metrics(ref,box):
    intersection=area(clip(ref['visible_native_polygon'],box));varea=ref['visible_reference_area'];croparea=(box[2]-box[0])*(box[3]-box[1]);assert croparea>0
    coverage=min(1.,max(0.,intersection/varea));fraction=min(1.,max(0.,intersection/croparea));en=ref['visible_reference_AABB']
    rc=[(en[0]+en[2])/2,(en[1]+en[3])/2];pc=[(box[0]+box[2])/2,(box[1]+box[3])/2]
    return {'intersection_reference_crop_area':intersection,'reference_coverage':coverage,'reference_fraction_in_crop':fraction,
    'reference_exterior_fraction':1-fraction,'polygon_IoU':intersection/(varea+croparea-intersection),
    'center_error_native_px':math.hypot(rc[0]-pc[0],rc[1]-pc[1]),'crop_to_reference_envelope_width_ratio':(box[2]-box[0])/(en[2]-en[0]),
    'crop_to_reference_envelope_height_ratio':(box[3]-box[1])/(en[3]-en[1]),
    'passes_engineering_crop_gate':coverage>=.9 and 1-fraction<=.25}
def target(ref,box):
    x,y,w,h,a=ref['bbox_xywh_angle_rad'];cx=x+w/2;cy=y+h/2;cw=box[2]-box[0];ch=box[3]-box[1];theta=ref['long_axis_angle_rad_mod_pi']
    return [(cx-box[0])/cw,(cy-box[1])/ch,ref['long_side']/cw,ref['short_side']/ch,math.sin(2*theta),math.cos(2*theta)]
