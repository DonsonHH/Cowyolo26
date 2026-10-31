from pathlib import Path
from datetime import date, datetime, timezone
from collections import Counter, defaultdict, deque
import hashlib, json

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


prior = load(PROJECT / "cows2021_identity_eval_20261030/protocol/run_v1.json")
rows = load(PROJECT / "cows2021_identity_intake_20261030/results/test8670_members.json")
used = set(sum(prior["roles"].values(), []))
by_id = defaultdict(lambda: defaultdict(list))
for row in rows:
    if row["date"] <= "2020-03-04":
        by_id[row["publisher_identity"]][row["date"]].append(row)
unused = []
for identity, dates in by_id.items():
    eligible_dates = sorted(day for day, images in dates.items() if len(images) >= 3)
    train_dates = {day: images for day, images in dates.items() if day <= "2020-02-27"}
    if identity not in used and len(eligible_dates) >= 2 and (date.fromisoformat(eligible_dates[-1]) - date.fromisoformat(eligible_dates[0])).days >= 7 and len(train_dates) >= 2 and sum(map(len,train_dates.values())) >= 12:
        unused.append(identity)
ranked = sorted(unused,key=lambda identity:hashlib.sha256(("Cows2021-domain-train-20261030-v1:"+identity).encode()).hexdigest())
assert len(ranked) == 36
training_IDs, future_IDs = ranked[:16], ranked[16:]
assert len(training_IDs) == 16 and len(future_IDs) == 20
new_train = []
for identity in training_IDs:
    dates = sorted(day for day in by_id[identity] if day <= "2020-02-27")
    queues = {day:deque(sorted(by_id[identity][day],key=lambda row:row["file_name"])) for day in dates}
    selected = []
    while len(selected) < 32 and any(queues.values()):
        for day in dates:
            if queues[day] and len(selected)<32:
                selected.append(queues[day].popleft())
    assert len(selected)>=12 and len({row["date"] for row in selected})>=2
    for row in selected:
        new_train.append({**row,"identity":row["identity_namespace"],"day":row["date"],"source_domain":"Cows2021",
                          "relative_file":"input/cows_train/"+identity+"/"+row["file_name"],
                          "URL":prior["source_base_URL"]+identity+"/"+row["file_name"]})
assert set(training_IDs).isdisjoint(used|set(future_IDs))
old_audit = load(PROJECT / "identity_training_20261026/delivery/results/input_audit/manifest.json")
old_train = [{**row,"identity":"MultiCam2023:"+row["identity"],"source_domain":"MultiCam2023",
              "remote_path":"/share/home/renly/projects/idcoo_research_20261026/identity_training/"+row["relative_path"]} for row in old_audit if row["split"]=="train"]
old_retention = [{**row,"identity":"MultiCam2023:"+row["identity"],"source_domain":"MultiCam2023",
                  "remote_path":"/share/home/renly/projects/idcoo_research_20261026/identity_training/"+row["relative_path"]} for row in old_audit if row["split"] in ["evaluation_gallery","evaluation_query"]]
assert len(old_train)==580 and len(old_retention)==90
assert len({row["identity"] for row in old_train})==20
for row in new_train:
    assert row["publisher_identity"] in training_IDs and row["date"]<="2020-02-27"
start = load(PROJECT / "pynq_identity_ncnn_20261029/protocol/encoder_v1.json")["encoder_condition"]
conditions = [{"index":index,"arm":arm,"seed":seed,"name":arm+"_seed"+str(seed)} for index,(seed,arm) in enumerate((seed,arm) for seed in [26,27,28] for arm in ["M_continue","C_domain"])]
protocol = {"status":"FROZEN_BEFORE_FIRST_NEW_TRAIN_ID_JPEG_OR_CUDA_UPDATE","created_UTC":datetime.now(timezone.utc).isoformat(),
            "start_encoder_checkpoint":start["checkpoint"],"start_encoder_sha256":start["checkpoint_sha256"],
            "training_identity_rank_prefix":"Cows2021-domain-train-20261030-v1:","Cows_training_IDs":training_IDs,
            "future_final_ID_candidates_pixels_closed":future_IDs,"prior_Cows_calibration_development_IDs":prior["roles"],
            "Cows_training_images":new_train,"MultiCam_training_images":old_train,"MultiCam_retention_images":old_retention,
            "conditions":conditions,"formal_updates_per_condition":300,"pseudo_epochs":15,"batches_per_pseudo_epoch":20,
            "batch_IDs":8,"images_per_ID":4,"input_size":224,"optimizer":"AdamW","learning_rate":.0001,"weight_decay":.0001,
            "loss":"CE16x_cosine_class_logits_plus_batch_hard_Euclidean_triplet_margin0.3_on_unit_features",
            "same_domain_only_classifier_and_triplet_negatives":True,"training_head_IDs":{"M_continue":20,"C_domain":16},
            "augmentation":"Existing frozen BodyTransform(augment=True),same parameters;not pixel-identical batches across arms",
            "checkpoint_selection":"last300_only;all6 jointly frozen before any calibration/development forward;no best epoch or seed selection",
            "primary_seed_preselected":26,"expected_formal_training_updates":1800,"expected_formal_training_image_forwards":57600,
            "expected_discarded_smoke_updates":2,"expected_smoke_image_forwards":64,
            "Cows_evaluation_source_protocol_sha256":sha(PROJECT / "cows2021_identity_eval_20261030/protocol/run_v1.json"),
            "Cows_evaluation_source_directory":"/share/home/renly/projects/idcoo_research_20261026/cows2021_identity_eval_20261030",
            "Cows_development_gallery_ID_counts":[20,20],"Cows_reference_per_ID":3,"Cows_unknown_queries_reused_per_fold":120,
            "original_threshold":start["threshold"],"calibration_unknown_empirical_FAR_limit":.05,
            "expected_new_model_evaluation_image_forwards":3780,"evaluation_warmup_forwards":0,
            "reserved_ID_pixels_allowed":False,"reserved2020_03_05_to2020_03_11_pixels_allowed":False,
            "new_board_forwards":0,"physical_crossyear_cow_ID_mapping_verified":False,
            "plan_sha256":sha(ROOT / "计划与验收.md"),"whole_goal_complete":False}
(ROOT / "protocol").mkdir(exist_ok=False)
(ROOT / "evidence").mkdir(exist_ok=False)
(ROOT / "results").mkdir(exist_ok=False)
output=ROOT / "protocol/run_v1.json";output.write_text(json.dumps(protocol,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"protocol_sha256":sha(output),"Cows_train_IDs":16,"new_train_images":len(new_train),"new_train_counts":dict(Counter(row["publisher_identity"] for row in new_train)),
                  "future_final_candidate_IDs":20,"formal_training_updates_planned":1800,"new_pixels_read_at_freeze":0}))
