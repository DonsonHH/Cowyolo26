import random,unittest
import torch
from PIL import Image
from training_primitives import BodyTransform,identity_batch,batch_hard_triplet

class TrainingContract(unittest.TestCase):
    def fixture(self):return [{'identity':str(identity),'day':day,'path':str(i)} for identity in range(10) for day in ['d1','d2'] for i in range(3)]
    def test_batches_balance_identities_and_dates(self):
        rows=self.fixture();indices=identity_batch(rows,random.Random(26));self.assertEqual(len(indices),32)
        groups={rows[i]['identity'] for i in indices};self.assertEqual(len(groups),8)
        for identity in groups:
            chosen=[i for i in indices if rows[i]['identity']==identity]
            self.assertEqual(len(chosen),4);self.assertEqual(len(set(chosen)),4)
            self.assertEqual(len({rows[i]['day'] for i in chosen}),2)
    def test_seeded_sampling_is_repeatable(self):
        self.assertEqual(identity_batch(self.fixture(),random.Random(26)),identity_batch(self.fixture(),random.Random(26)))
    def test_single_date_rejected(self):
        rows=[{**r,'day':'d1'} for r in self.fixture()]
        with self.assertRaises(ValueError):identity_batch(rows,random.Random(26))
    def test_letterbox_preserves_body_boundary(self):
        im=Image.new('RGB',(400,100),'red');tensor=BodyTransform()(im)
        restored=(tensor*torch.tensor([.229,.224,.225])[:,None,None]+torch.tensor([.485,.456,.406])[:,None,None])
        self.assertEqual(tuple(tensor.shape),(3,224,224))
        self.assertTrue(torch.allclose(restored[:,0,0],torch.tensor([127/255]*3),atol=1e-5))
        self.assertGreater(restored[0,112,0],.99);self.assertGreater(restored[0,112,-1],.99)
    def test_separated_identities_triplet_zero(self):
        z=torch.tensor([[1.,0.],[1.,0.],[0.,1.],[0.,1.]],requires_grad=True);labels=torch.tensor([0,0,1,1])
        loss=batch_hard_triplet(z,labels);self.assertEqual(loss.item(),0.)
    def test_bad_metric_geometry_has_finite_gradient(self):
        z=torch.tensor([[1.,0.],[0.,1.],[.99,.01],[.01,.99]],requires_grad=True);labels=torch.tensor([0,0,1,1])
        loss=batch_hard_triplet(z,labels);self.assertGreater(loss.item(),0);loss.backward();self.assertTrue(torch.isfinite(z.grad).all())
    def test_missing_positive_rejected(self):
        with self.assertRaises(ValueError):batch_hard_triplet(torch.eye(3),torch.arange(3))

if __name__=='__main__':unittest.main(verbosity=2)
