"""Independent intersection by enumerating contained corners and segment crossings."""
import math
def polygon_area(points):
    if len(points)<3:return 0.
    origin=points[0]
    return abs(sum((points[i][0]-origin[0])*(points[i+1][1]-origin[1])-(points[i][1]-origin[1])*(points[i+1][0]-origin[0]) for i in range(1,len(points)-1)))/2
def corners(bbox):
    x,y,w,h,theta=bbox;cx=x+w/2;cy=y+h/2;radius=math.hypot(w,h)/2
    points=[]
    for dx,dy in [(-w,-h),(w,-h),(w,h),(-w,h)]:
        angle=math.atan2(dy,dx)+theta;points.append([cx+radius*math.cos(angle),cy+radius*math.sin(angle)])
    return points
def cross(a,b):return a[0]*b[1]-a[1]*b[0]
def inside_convex(point,poly):
    products=[cross([b[0]-a[0],b[1]-a[1]],[point[0]-a[0],point[1]-a[1]]) for a,b in zip(poly,poly[1:]+poly[:1])]
    return all(v>=-1e-7 for v in products) or all(v<=1e-7 for v in products)
def intersection(poly,box):
    x1,y1,x2,y2=box;rectangle=[[x1,y1],[x2,y1],[x2,y2],[x1,y2]]
    points=[p for p in poly if x1-1e-8<=p[0]<=x2+1e-8 and y1-1e-8<=p[1]<=y2+1e-8]
    points.extend(p for p in rectangle if inside_convex(p,poly))
    for a,b in zip(poly,poly[1:]+poly[:1]):
        r=[b[0]-a[0],b[1]-a[1]]
        for c,d in zip(rectangle,rectangle[1:]+rectangle[:1]):
            s=[d[0]-c[0],d[1]-c[1]];den=cross(r,s)
            if abs(den)<1e-14:continue
            delta=[c[0]-a[0],c[1]-a[1]];t=cross(delta,s)/den;u=cross(delta,r)/den
            if -1e-10<=t<=1+1e-10 and -1e-10<=u<=1+1e-10:points.append([a[0]+t*r[0],a[1]+t*r[1]])
    unique=[]
    for p in points:
        if not any(math.hypot(p[0]-q[0],p[1]-q[1])<1e-7 for q in unique):unique.append(p)
    if len(unique)<3:return []
    center=[sum(p[k] for p in unique)/len(unique) for k in range(2)]
    return sorted(unique,key=lambda p:math.atan2(p[1]-center[1],p[0]-center[0]))
def envelope(points):return [min(p[0] for p in points),min(p[1] for p in points),max(p[0] for p in points),max(p[1] for p in points)]
def iou(a,b):
    iw=max(0.,min(a[2],b[2])-max(a[0],b[0]));ih=max(0.,min(a[3],b[3])-max(a[1],b[1]));inter=iw*ih
    return inter/((a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-inter)
def independent_best_matching(matrix,threshold=.5):
    n=len(matrix);m=len(matrix[0]) if n else 0;best=(-1,-1.);winners=0
    def search(i,used,count,total):
        nonlocal best,winners
        if i==n:
            if count>best[0] or count==best[0] and total>best[1]+1e-12:best=(count,total);winners=1
            elif count==best[0] and abs(total-best[1])<=1e-12:winners+=1
            return
        search(i+1,used,count,total)
        for j in range(m):
            if j not in used and matrix[i][j]>=threshold:search(i+1,used|{j},count+1,total+matrix[i][j])
    search(0,set(),0,0.)
    return best,winners
def quad_roundtrip_error(reference,target,box):
    width=box[2]-box[0];height=box[3]-box[1];cx=box[0]+target[0]*width;cy=box[1]+target[1]*height
    longside=target[2]*width;shortside=target[3]*height;angle=math.atan2(target[4],target[5])/2
    reconstructed=corners([cx-longside/2,cy-shortside/2,longside,shortside,angle])
    return max(min(math.hypot(a[0]-b[0],a[1]-b[1]) for b in reconstructed) for a in reference)
