"""Independent ZIP-library, scalar retrieval, AP and stratified-ID statistics audit."""
from pathlib import Path
from datetime import date,datetime,timezone
from collections import Counter,defaultdict
import hashlib,io,json,math,sys,zipfile
import numpy as np
from PIL import Image
from frozen_body_tensor import body_tensor

ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent;OUT=ROOT/"delivery/results/evaluation"
SOURCE=PROJECT/"independent_source_recheck_20261030"
load=lambda p:json.loads(p.read_text(encoding="utf-8-sig"))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
p=load(ROOT/"protocol/run_v1.json");e=load(ROOT/"protocol/execution_v1.json")
s=load(OUT/"summary.json")
assert s["status"]=="BOTH_FROZEN_ENCODERS90_BECA_TRANSFER_IMAGES180_FORWARDS8_FIXED_POLICIES_AND24_STRATIFIED_ID_CONTRASTS_COMPLETE"
assert s["actual_model_image_forwards"]==180 and s["actual_network_calls"]==16
assert s["new_training_updates"]==s["warmups"]==s["new_board_forwards"]==0 and s["paired_ID_contrasts"]==24
assert e["protocol_sha256"]==sha(ROOT/"protocol/run_v1.json")==s["protocol_sha256"]
assert s["execution_sha256"]==sha(ROOT/"protocol/execution_v1.json")
for name,digest in e["files_sha256"].items():assert sha(ROOT/name)==sha(ROOT/"delivery"/name)==digest
assert not set(p["roles"]["registered"]+p["roles"]["unknown"])&set(p["excluded_metadata_conflict_IDs"]+p["excluded_seen_QA_IDs"])
assert len(set(p["roles"]["registered"]+p["roles"]["unknown"]))==20

segments=[]
for member in p["images"]:
    alias=f'BECA_img_{member["index"]:02d}'
    header=ROOT/"evidence"/(alias+"_header_v1.bin");payload=ROOT/"evidence"/(alias+"_payload_v1.bin")
    for name,path in[("header",header),("payload",payload)]:
        report=load(ROOT/"evidence"/(alias+f"_{name}_v1.json"))
        assert report["strict_range_received"]and sha(path)==report["sha256"]
        assert e["created_UTC"]<report["created_UTC"]<s["created_UTC"]
    segments.append((member["source_record"]["local_header_offset"],header.read_bytes()+payload.read_bytes()))
directory=load(SOURCE/"results/BECA_directory_range_plan_v1.json")
segments.extend([(directory["central_directory_start"],(SOURCE/"evidence/BECA_central_directory_v1.bin").read_bytes()),
                 (directory["archive_declared_bytes"]-131072,(SOURCE/"evidence/BECA_zip_tail_dotnet_v1.bin").read_bytes())])

class SparseVerifiedFile(io.RawIOBase):
    def __init__(self):self.position=0
    def tell(self):return self.position
    def seekable(self):return True
    def readable(self):return True
    def seek(self,offset,whence=0):
        value=offset if whence==0 else self.position+offset if whence==1 else directory["archive_declared_bytes"]+offset
        assert 0<=value<=directory["archive_declared_bytes"];self.position=value;return value
    def read(self,size=-1):
        if size<0:size=directory["archive_declared_bytes"]-self.position
        size=min(size,directory["archive_declared_bytes"]-self.position)
        remaining=size;parts=[]
        while remaining:
            found=[(start,data)for start,data in segments if start<=self.position<start+len(data)]
            assert found,("Unreceived archive interval requested",self.position,remaining)
            start,data=max(found,key=lambda t:t[0]+len(t[1]))
            count=min(remaining,start+len(data)-self.position)
            parts.append(data[self.position-start:self.position-start+count]);self.position+=count;remaining-=count
        return b"".join(parts)

inputs=load(OUT/"input_hashes.json");admission=load(ROOT/"results/pixel_admission.json")
assert len(inputs)==len(admission["rows"])==len(p["images"])==90
pixels=set();JPEGs=set()
with zipfile.ZipFile(SparseVerifiedFile())as archive:
    for index,(row,audit,feature_input)in enumerate(zip(p["images"],admission["rows"],inputs)):
        data=archive.read(row["source_record"]["name"])
        path=ROOT/row["local_relative_file"]
        assert data==path.read_bytes()==(ROOT/"delivery"/row["local_relative_file"]).read_bytes()
        assert len(data)==row["source_record"]["uncompressed_size"]and sha(path)==audit["sha256"]
        with Image.open(path)as im:im.load();image=im.convert("RGB")
        assert list(image.size)==audit["dimensions_WH"]
        pixel=hashlib.sha256(image.tobytes()).hexdigest();assert pixel==audit["RGB_pixel_SHA256"]
        pixels.add(pixel);JPEGs.add(audit["sha256"])
        x=body_tensor(image);digest=hashlib.sha256(x.tobytes()).hexdigest()
        assert digest==audit["input_tensor_sha256"]==feature_input["input_tensor_sha256"]and feature_input["index"]==index
        if index in e["tensor_anchor_indices"]:
            with np.load(OUT/"input_anchors"/f"index{index}.npz")as a:assert a["input"].tobytes()==x.tobytes()
assert len(pixels)==len(JPEGs)==90
prior=load(SOURCE/"results/BECA_visual_QA_manifest_v1.json")
assert pixels.isdisjoint({r["RGB_pixel_SHA256"]for r in prior["records"]})
assert JPEGs.isdisjoint({r["JPEG_sha256"]for r in prior["records"]})
for ID in p["roles"]["registered"]:
    gg=[r for r in p["images"]if r["publisher_identity"]==ID and r["purpose"]=="gallery"]
    qq=[r for r in p["images"]if r["publisher_identity"]==ID and r["purpose"]=="known_query"]
    assert len(gg)==len(qq)==3 and len({r["date"]for r in gg+qq})==6
    assert (date.fromisoformat(min(r["date"]for r in qq))-date.fromisoformat(max(r["date"]for r in gg))).days>=30
gi=[i for i,r in enumerate(p["images"])if r["purpose"]=="gallery"]
qi=[i for i,r in enumerate(p["images"])if r["purpose"]!="gallery"]
labels=sorted(p["roles"]["registered"])
outcomes=load(OUT/"all_outcomes.json");decisions=load(OUT/"all_decisions.json")
intervals=load(OUT/"per_ID_intervals.json");contrasts=load(OUT/"paired_ID_differences.json")
assert len(outcomes)==8 and len(decisions)==480 and len(contrasts)==24
group_of={r["ID"]:r["native_group"]for r in p["assignments"]}
rng=np.random.default_rng(e["bootstrap_seed"])
replayed_draws={}
for role in["registered","unknown"]:
    IDs=sorted(p["roles"][role]);blocks=[]
    for shed in sorted({group_of[ID]for ID in IDs}):
        positions=np.array([i for i,ID in enumerate(IDs)if group_of[ID]==shed])
        blocks.append(rng.choice(positions,size=(2000,len(positions)),replace=True))
    draw=np.hstack(blocks);replayed_draws[role]=draw
    expected=Counter(group_of[ID]for ID in IDs)
    assert all(Counter(group_of[IDs[j]]for j in r)==expected for r in draw)
with np.load(OUT/"bootstrap_ID_indices.npz")as a:
    assert np.array_equal(a["known"],replayed_draws["registered"])and np.array_equal(a["unknown"],replayed_draws["unknown"])

derived={};score_cells=pair_cells=decision_count=0;subgroups=[];near_threshold=[]
for model in["old_C","new_C_domain_seed26"]:
    with np.load(OUT/model/"all_features.npz")as a:raw=a["raw"].copy();features=a["normalized"].copy()
    assert raw.shape==features.shape==(90,576)and np.isfinite(raw).all()and np.isfinite(features).all()
    norm=raw.astype(float)/np.sqrt((raw.astype(float)**2).sum(axis=1))[:,None]
    assert np.max(np.abs(norm-features))<1e-7
    with np.load(OUT/model/"pair_and_ID_scores.npz")as a:
        saved_pairs=a["pair_scores"].copy();saved_scores=a["ID_scores"].copy()
        assert a["query_indices"].tolist()==qi and a["gallery_indices"].tolist()==gi
    retrieval=load(OUT/model/"retrieval_unthresholded.json");assert len(retrieval)==60
    own=[]
    for k,index in enumerate(qi):
        scores_by_image=[math.fsum(float(a)*float(b)for a,b in zip(features[index],features[j]))for j in gi]
        assert max(abs(a-b)for a,b in zip(scores_by_image,saved_pairs[k]))<1e-12;pair_cells+=30
        values={ID:max(scores_by_image[j]for j,g in enumerate(gi)if p["images"][g]["publisher_identity"]==ID)for ID in labels}
        order=sorted(labels,key=lambda ID:(-values[ID],ID));original=retrieval[k]
        assert original["source_index"]==index and original["identity"]==p["images"][index]["publisher_identity"]
        assert original["predicted_id"]==order[0]and original["top5_IDs"]==order[:5]
        assert max(abs(values[ID]-original["all_ID_scores"][ID])for ID in labels)<1e-12
        assert np.max(np.abs(saved_scores[k]-[values[ID]for ID in labels]))<1e-12;score_cells+=10
        assert abs(original["score"]-values[order[0]])<1e-12
        if original["is_known"]:
            ordered=sorted(range(30),key=lambda j:(-scores_by_image[j],gi[j]))
            relevance=[p["images"][gi[j]]["publisher_identity"]==original["identity"]for j in ordered]
            hits=0;precision_sum=0
            for rank,correct in enumerate(relevance,1):
                if correct:hits+=1;precision_sum+=hits/rank
            assert hits==3 and abs(precision_sum/3-original["AP"])<1e-15
        else:assert original["AP"]is None
        own.append(original)
    for policy,tau in e["threshold_policies"][model].items():
        expected=[r for r in decisions if r["model"]==model and r["policy"]==policy];assert len(expected)==60
        for original,row in zip(own,expected):
            assert all(original[k]==row[k]for k in original)and row["threshold"]==tau
            assert row["accepted"]==(original["score"]>=tau);decision_count+=1
            if abs(original["score"]-tau)<1e-7:near_threshold.append({"model":model,"policy":policy,"source_index":row["source_index"]})
        known=[r for r in expected if r["is_known"]];unknown=[r for r in expected if not r["is_known"]]
        C=sum(r["accepted"]and r["identity"]==r["predicted_id"]for r in known)
        W=sum(r["accepted"]and r["identity"]!=r["predicted_id"]for r in known)
        U=sum(not r["accepted"]for r in known);FA=sum(r["accepted"]for r in unknown)
        summary=next(r for r in outcomes if r["model"]==model and r["policy"]==policy)
        assert [summary[k]for k in["C","W","U","unknown_FA"]]==[C,W,U,FA]and C+W+U==30
        assert summary["known_Top1"]==sum(r["predicted_id"]==r["identity"]for r in known)
        assert summary["known_Top5"]==sum(r["identity"]in r["top5_IDs"]for r in known)
        assert abs(summary["known_mAP"]-math.fsum(r["AP"]for r in known)/30)<1e-15
        assert summary["accepted_wrong_fraction"]==((W+FA)/(C+W+FA)if C+W+FA else None)
        own_rates={}
        for metric in["Top1","AP","C","W","U","FA"]:
            role="unknown"if metric=="FA"else"registered";IDs=sorted(p["roles"][role]);rates=[]
            for ID in IDs:
                subset=[r for r in expected if r["identity"]==ID];assert len(subset)==3
                if metric=="AP":rate=sum(r["AP"]for r in subset)/3
                elif metric=="Top1":rate=sum(r["predicted_id"]==ID for r in subset)/3
                elif metric=="C":rate=sum(r["accepted"]and r["predicted_id"]==ID for r in subset)/3
                elif metric=="W":rate=sum(r["accepted"]and r["predicted_id"]!=ID for r in subset)/3
                elif metric=="U":rate=sum(not r["accepted"]for r in subset)/3
                else:rate=sum(r["accepted"]for r in subset)/3
                rates.append(rate)
            samples=np.array([math.fsum(rates[j]for j in draw)/10 for draw in replayed_draws[role]])
            saved=intervals[model+":"+policy][metric]
            assert saved["IDs"]==IDs and np.max(np.abs(np.array(saved["rates"])-rates))<1e-15
            assert abs(saved["macro_mean"]-math.fsum(rates)/10)<1e-15
            assert np.max(np.abs(np.quantile(samples,[.025,.975])-saved["percentile95"]))<1e-15
            own_rates[metric]=rates
        derived[model+":"+policy]=own_rates
        if policy==p["primary_policy"]:
            for shed in sorted(set(group_of.values())):
                kk=[r for r in known if r["native_group"]==shed];uu=[r for r in unknown if r["native_group"]==shed]
                subgroups.append({"model":model,"native_group":shed,"known_queries":len(kk),"unknown_queries":len(uu),
                                 "Top1":sum(r["identity"]==r["predicted_id"]for r in kk),
                                 "C":sum(r["accepted"]and r["identity"]==r["predicted_id"]for r in kk),
                                 "W":sum(r["accepted"]and r["identity"]!=r["predicted_id"]for r in kk),
                                 "U":sum(not r["accepted"]for r in kk),"FA":sum(r["accepted"]for r in uu),
                                 "known_mAP":math.fsum(r["AP"]for r in kk)/len(kk)})
for contrast in contrasts:
    metric=contrast["metric"];policy=contrast["policy"]
    a=derived["old_C:"+policy][metric];b=derived["new_C_domain_seed26:"+policy][metric]
    delta=np.array(b)-np.array(a);assert np.max(np.abs(delta-contrast["new_minus_old_per_ID"]))<1e-15
    assert abs(float(delta.mean())-contrast["mean_difference"])<1e-15
    samples=np.array([math.fsum(float(delta[j])for j in draw)/10 for draw in replayed_draws["unknown"if metric=="FA"else"registered"]])
    assert np.max(np.abs(np.quantile(samples,[.025,.975])-contrast["percentile95"]))<1e-15
assert pair_cells==3600 and score_cells==1200 and decision_count==480
result={"status":"BECA_ALL90_ZIP_CRC_INPUTS180_FEATURES3600_PAIRS1200_ID_SCORES480_DECISIONS24_STRATIFIED_CONTRASTS_INDEPENDENTLY_RECOMPUTED",
        "created_UTC":datetime.now(timezone.utc).isoformat(),"image_inputs":90,"model_image_forwards":180,"network_calls":16,
        "input_tensor_anchors":len(e["tensor_anchor_indices"]),"gallery_pair_cells":3600,"ID_score_cells":1200,
        "fixed_decisions":480,"per_ID_interval_sets":8,"paired_ID_contrasts":24,"near1e7_threshold_endpoints":near_threshold,
        "main_outcomes":[r for r in outcomes if r["policy"]==p["primary_policy"]],"primary_shed_subgroups":subgroups,
        "BECA_selected20_IDs_now_seen":True,"new_forwards_by_verification":0,"new_training_updates":0,
        "BECA_remaining_labels_independently_certified":False,"current12_identity_or_counting_GT_obtained":False,
        "new_board_results_obtained":False,"Cows_reserved_date_pixels_opened":False,"default_model_or_threshold_changed":False,
        "whole_goal_complete":False}
out=ROOT/"results/independent_verification.json";assert not out.exists()
out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+chr(10),encoding="utf-8")
print(json.dumps(result,ensure_ascii=False))
