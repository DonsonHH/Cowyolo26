import torch

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
