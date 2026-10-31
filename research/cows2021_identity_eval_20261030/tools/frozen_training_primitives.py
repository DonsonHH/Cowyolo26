from collections import defaultdict
import random
import torch
import torch.nn.functional as F
from PIL import Image,ImageOps
from torchvision.transforms import functional as TF
from torchvision.transforms import ColorJitter

class BodyTransform:
    def __init__(self,augment=False):
        self.augment=augment;self.colour=ColorJitter(brightness=.2,contrast=.2,saturation=.1)
    def __call__(self,image):
        image=image.convert('RGB')
        if self.augment:
            if torch.rand(())<.5:image=ImageOps.mirror(image)
            angle=float(torch.empty(1).uniform_(-8,8).item())
            image=TF.rotate(image,angle,interpolation=TF.InterpolationMode.BILINEAR,expand=True,fill=(127,127,127))
            image=self.colour(image)
        image=ImageOps.pad(image,(224,224),method=Image.Resampling.BILINEAR,color=(127,127,127),centering=(.5,.5))
        tensor=TF.to_tensor(image)
        return TF.normalize(tensor,[.485,.456,.406],[.229,.224,.225])

def identity_batch(rows,rng,identities_per_batch=8,images_per_identity=4):
    byid=defaultdict(list)
    for i,row in enumerate(rows):byid[row['identity']].append(i)
    identities=sorted(byid)
    if len(identities)<identities_per_batch:raise ValueError('Insufficient training identities')
    selected=[]
    for identity in rng.sample(identities,identities_per_batch):
        days=defaultdict(list)
        for i in byid[identity]:days[rows[i]['day']].append(i)
        if len(days)<2:raise ValueError('Cross-date positives required')
        first_days=rng.sample(sorted(days),2);indices=[rng.choice(days[d]) for d in first_days]
        remaining=[i for i in byid[identity] if i not in indices]
        indices+=rng.sample(remaining,images_per_identity-2)
        assert len(set(indices))==images_per_identity
        selected.extend(indices)
    return selected

def batch_hard_triplet(embedding,labels,margin=.3):
    distance=torch.cdist(embedding,embedding,p=2)
    same=labels[:,None]==labels[None,:]
    positive=same&~torch.eye(len(labels),device=labels.device,dtype=torch.bool)
    negative=~same
    if not positive.any(1).all() or not negative.any(1).all():raise ValueError('Every anchor needs a positive and a negative')
    hardest_positive=distance.masked_fill(~positive,-torch.inf).max(1).values
    hardest_negative=distance.masked_fill(~negative,torch.inf).min(1).values
    return F.relu(hardest_positive-hardest_negative+margin).mean()
