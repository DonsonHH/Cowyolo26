"""Fixed geometry; no score-driven crop selection."""
import math
from PIL import Image
def apply_rule(image,rule,group):
    image=image.convert('RGB');w,h=image.size
    applies=rule['apply_to']=='gallery_and_query' or rule['apply_to']=='query_only' and group.endswith('query')
    box=(0,0,w,h)
    if applies:
        fw,fh=rule['center_width'],rule['center_height']
        if fw!=1 or fh!=1:
            box=(math.floor((1-fw)*w/2),math.floor((1-fh)*h/2),math.ceil((1+fw)*w/2),math.ceil((1+fh)*h/2))
            assert 0<=box[0]<box[2]<=w and 0<=box[1]<box[3]<=h
            image=image.crop(box)
        if rule['rotation_CCW']==180:image=image.transpose(Image.Transpose.ROTATE_180)
        elif rule['rotation_CCW']!=0:raise ValueError('Unregisteredrotation')
    return image,{'input_dimensions':[w,h],'crop_box':list(box),'rotation_CCW':rule['rotation_CCW'] if applies else 0,'output_dimensions':list(image.size)}
