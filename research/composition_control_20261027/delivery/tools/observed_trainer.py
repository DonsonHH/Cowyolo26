"""Count actual optimiser calls and training batches without changing trainer math."""
from ultralytics.models.yolo.detect.train import DetectionTrainer
from common import state_digest


class ObservedTrainer(DetectionTrainer):
    def __init__(self,*args,**kwargs):
        self.observed_batches=0;self.observed_optimizer_steps=0;self.optimizer_step_batch_indices=[]
        self.initial_model_digest=None
        super().__init__(*args,**kwargs)

    def get_model(self,*args,**kwargs):
        model=super().get_model(*args,**kwargs)
        self.initial_model_digest=state_digest(model)
        return model

    def optimizer_step(self):
        super().optimizer_step()
        self.observed_optimizer_steps+=1
        self.optimizer_step_batch_indices.append(self.observed_batches)
