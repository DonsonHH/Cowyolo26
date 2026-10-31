"""Integer right-angle image permutations with synchronized normalized boxes."""
import hashlib,json
from collections import Counter
import torch
from observed_trainer import ObservedTrainer
def rotate_training_batch(images,boxes,batch_indices,turns):
    assert images.ndim==4 and images.shape[-2]==images.shape[-1]
    assert boxes.ndim==2 and boxes.shape[1]==4 and len(boxes)==len(batch_indices)
    assert len(turns)==len(images)
    turns=torch.as_tensor(turns,dtype=torch.long,device='cpu');assert ((turns>=0)&(turns<=3)).all()
    output=images.clone();target=boxes.clone()
    for k in [1,2,3]:
        ids=torch.nonzero(turns==k).flatten().to(images.device)
        if ids.numel():output[ids]=torch.rot90(images[ids],k,dims=(-2,-1))
    if len(boxes):
        per_box=turns.to(boxes.device)[batch_indices.to(device=boxes.device,dtype=torch.long)]
        for k in [1,2,3]:
            mask=per_box==k;v=boxes[mask]
            if not len(v):continue
            x,y,w,h=v.unbind(1)
            if k==1:new=torch.stack([y,1-x,h,w],1)
            elif k==2:new=torch.stack([1-x,1-y,w,h],1)
            else:new=torch.stack([1-y,x,h,w],1)
            target[mask]=new
    return output,target
class FactorialTrainer(ObservedTrainer):
    right_angle_enabled=False
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.rotation_generator=torch.Generator(device='cpu');self.rotation_generator.manual_seed(710026+int(self.args.seed))
        self.rotation_schedule=[];self.rotation_counts=Counter();self.rotation_label_rows=0;self.preprocess_image_count=0
    def preprocess_batch(self,batch):
        batch=super().preprocess_batch(batch);images=batch['img'];self.preprocess_image_count+=len(images)
        if not self.right_angle_enabled:return batch
        turns=torch.randint(0,4,(len(images),),generator=self.rotation_generator)
        before_area=batch['bboxes'][:,2]*batch['bboxes'][:,3]
        output,boxes=rotate_training_batch(images,batch['bboxes'],batch['batch_idx'],turns)
        assert torch.equal(before_area,boxes[:,2]*boxes[:,3])
        assert output.shape==images.shape and boxes.shape==batch['bboxes'].shape and torch.isfinite(boxes).all()
        batch['img']=output;batch['bboxes']=boxes
        values=turns.tolist();self.rotation_schedule.append({'training_batch':self.observed_batches,'turns':values})
        self.rotation_counts.update(values);self.rotation_label_rows+=len(boxes)
        return batch
class RightAngleTrainer(FactorialTrainer):
    right_angle_enabled=True
