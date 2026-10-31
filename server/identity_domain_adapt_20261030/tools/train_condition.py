from pathlib import Path
from datetime import datetime, timezone
import os
os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"
import argparse, hashlib, json, random, socket, time, traceback
import numpy as np
from PIL import Image
import torch
import torch.nn.functional as F
from torchvision.models import mobilenet_v3_small
from frozen_training_primitives import BodyTransform, identity_batch, batch_hard_triplet

ROOT = Path(__file__).resolve().parents[1]


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save_new(path, value):
    assert not path.exists()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2)+"\n", encoding="utf-8")


def state_digest(model):
    digest = hashlib.sha256()
    for key, value in sorted(model.state_dict().items()):
        array = value.detach().cpu().contiguous().numpy()
        digest.update(key.encode()+str(array.dtype).encode()+str(array.shape).encode()+array.tobytes())
    return digest.hexdigest()


def execute(condition, smoke=False):
    assert os.environ.get("SLURM_JOB_ID") and socket.gethostname() != "mu01" and torch.cuda.is_available()
    torch.set_num_threads(4)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.use_deterministic_algorithms(True)
    protocol = load(ROOT / "protocol/run_v1.json")
    execution = load(ROOT / "protocol/execution_v1.json")
    assert execution["protocol_sha256"] == sha(ROOT / "protocol/run_v1.json")
    for name, digest in execution["code_hashes"].items():
        assert sha(ROOT/name) == digest, name
    assert sha(protocol["start_encoder_checkpoint"]) == protocol["start_encoder_sha256"]
    admission = load(ROOT / "results/input_admission.json")
    assert admission["admitted"]
    if not smoke:
        gate = load(ROOT/"results/smoke/summary.json")
        assert gate["status"] == "BOTH_ARMS_ONE_REAL_CUDA_UPDATE_PASS_FORMAL_WEIGHTS_UNTOUCHED"
        assert gate["discarded_optimizer_updates"] == 2 and gate["source_image_forwards"] == 64
    seed = condition["seed"]
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed); torch.cuda.manual_seed_all(seed)
    rng = random.Random(seed)
    rows = protocol["MultiCam_training_images"] if condition["arm"] == "M_continue" else protocol["Cows_training_images"]
    for row in rows:
        path = Path(row["remote_path"]) if "remote_path" in row else ROOT/row["relative_file"]
        expected = row.get("sha256")
        if expected is None:
            expected = next(record["sha256"] for record in admission["Cows_records"] if record["relative_file"]==row["relative_file"])
        assert sha(path) == expected
    labels = sorted({row["identity"] for row in rows})
    assert len(labels) == protocol["training_head_IDs"][condition["arm"]]
    class_index = {identity:index for index,identity in enumerate(labels)}
    full = mobilenet_v3_small(weights=None)
    encoder = torch.nn.Sequential(full.features, full.avgpool, torch.nn.Flatten()).cuda()
    source = torch.load(protocol["start_encoder_checkpoint"], map_location="cpu", weights_only=True)
    encoder.load_state_dict(source)
    assert all(torch.equal(value.detach().cpu(),source[key]) for key,value in encoder.state_dict().items())
    initial = state_digest(encoder)
    classifier = torch.nn.Parameter(torch.empty(len(labels),576,device="cuda"))
    torch.nn.init.normal_(classifier,std=.01)
    optimizer = torch.optim.AdamW(list(encoder.parameters())+[classifier],lr=protocol["learning_rate"],weight_decay=protocol["weight_decay"])
    transform = BodyTransform(augment=True)
    folder = ROOT / "results" / ("smoke" if smoke else "training") / condition["name"]
    folder.mkdir(parents=True,exist_ok=False)
    state = {"status":"RUNNING","condition":condition,"Slurm_job_id":os.environ["SLURM_JOB_ID"],"PID":os.getpid(),
             "formal":not smoke,"optimizer_updates":0,"training_image_forwards":0,"network_calls":0,
             "initial_encoder_state_digest":initial,"starting_checkpoint_sha256":protocol["start_encoder_sha256"],
             "training_IDs":labels,"training_images_available":len(rows),"input_size":224,"device":torch.cuda.get_device_name(0),
             "whole_goal_complete":False}
    cache = {}
    def image(row):
        path = Path(row["remote_path"]) if "remote_path" in row else ROOT/row["relative_file"]
        if str(path) not in cache:
            with Image.open(path) as source_image:
                source_image.load(); cache[str(path)] = source_image.convert("RGB")
        return cache[str(path)].copy()
    def count_forward(module,args):
        assert module.training and args[0].shape==(32,3,224,224)
        state["training_image_forwards"] += 32
        state["network_calls"] += 1
    encoder.register_forward_pre_hook(count_forward)
    expected_steps = 1 if smoke else 300
    started = time.monotonic()
    try:
        with (folder/"actual_updates.jsonl").open("x",encoding="utf-8") as stream:
            for step in range(1,expected_steps+1):
                encoder.train()
                indices = identity_batch(rows,rng,identities_per_batch=8,images_per_identity=4)
                selected = [rows[index] for index in indices]
                batch = torch.stack([transform(image(row)) for row in selected]).cuda()
                batch_labels = torch.tensor([class_index[row["identity"]] for row in selected],device="cuda")
                optimizer.zero_grad(set_to_none=True)
                features = F.normalize(encoder(batch),dim=1)
                ce = F.cross_entropy(16*F.linear(features,F.normalize(classifier,dim=1)),batch_labels)
                triplet = batch_hard_triplet(features,batch_labels,.3)
                loss = ce+triplet
                assert torch.isfinite(loss)
                loss.backward()
                gradients=[parameter.grad for parameter in encoder.parameters() if parameter.grad is not None]
                assert gradients and all(torch.isfinite(gradient).all() for gradient in gradients)
                nonzero=sum(bool(torch.count_nonzero(gradient)) for gradient in gradients)
                assert nonzero>0
                optimizer.step()
                state["optimizer_updates"] += 1
                pixels=batch.detach().cpu().contiguous().numpy()
                record={"update":step,"source_image_indices":indices,"identity_labels":[row["identity"] for row in selected],
                        "dates":[row["day"] for row in selected],"input_tensor_sha256":hashlib.sha256(pixels.tobytes()).hexdigest(),
                        "loss":float(loss.item()),"CE":float(ce.item()),"triplet":float(triplet.item()),
                        "gradient_tensors":len(gradients),"nonzero_gradient_tensors":nonzero,
                        "cumulative_training_image_forwards":state["training_image_forwards"]}
                stream.write(json.dumps(record)+"\n");stream.flush()
                if step==1:
                    np.savez_compressed(folder/"first4_actual_training_inputs.npz",input=pixels[:4])
                if step%20==0 or smoke:
                    print(json.dumps({"condition":condition["name"],"updates":step,"loss":record["loss"],"image_forwards":state["training_image_forwards"]}),flush=True)
        final_digest=state_digest(encoder)
        assert final_digest!=initial and state["optimizer_updates"]==state["network_calls"]==expected_steps
        assert state["training_image_forwards"]==expected_steps*32
        if not smoke:
            checkpoint=folder/"last_encoder.pt"
            torch.save({key:value.detach().cpu().clone() for key,value in encoder.state_dict().items()},checkpoint)
            torch.save(classifier.detach().cpu(),folder/"training_only_classifier.pt")
            state.update({"last_encoder_checkpoint":str(checkpoint),"last_encoder_sha256":sha(checkpoint)})
        state.update({"status":"ONE_DOMAIN_TRAINING_CONDITION_COMPLETE" if not smoke else "ONE_ARM_REAL_CUDA_SMOKE_UPDATE_PASS",
                      "final_encoder_state_digest":final_digest,"updates_journal_sha256":sha(folder/"actual_updates.jsonl"),
                      "elapsed_s":time.monotonic()-started,"new_calibration_or_development_image_forwards":0,
                      "final_reserved_ID_pixels_opened":False})
    except BaseException as error:
        state.update({"status":"FAILED","error":repr(error),"traceback":traceback.format_exc()})
        raise
    finally:
        save_new(folder/"terminal.json",state)
    return state


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--index",required=True,type=int);args=parser.parse_args()
    plan=load(ROOT/"protocol/run_v1.json");execute(plan["conditions"][args.index])
