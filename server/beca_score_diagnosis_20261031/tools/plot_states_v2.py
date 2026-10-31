from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]
source=ROOT/"results/score_diagnosis_v1.json";data=json.loads(source.read_text())
out=ROOT/"results/figures_v2";out.mkdir(exist_ok=False)
plt.rcParams.update({"font.family":"DejaVu Sans","font.size":11,"axes.spines.top":False,"axes.spines.right":False,"svg.fonttype":"none"})
colors={"old_C":"#375b91","new_C_domain_seed26":"#c45d25"}
fig,(ax,score_ax)=plt.subplots(1,2,figsize=(12.8,5.3),gridspec_kw={"width_ratios":[1.1,1]})
for model,label in[("old_C","Original encoder"),("new_C_domain_seed26","Cows-domain encoder")]:
    details=data["models"][model];states=details["threshold_states"]
    x=[r["W"]+r["FA"]for r in states];y=[r["C"]for r in states]
    ax.plot(x,y,color=colors[model],lw=1.8,marker="o",ms=3,label=label)
    max_c=details["constrained_correct_acceptance_upper_bounds"]["zero_observed_W_and_FA"]["max_C"]
    ax.scatter([0],[max_c],s=78,color=colors[model],edgecolors="white",zorder=5)
    ax.annotate(f"{max_c}/30 at zero errors",(0,max_c),xytext=(10,9),textcoords="offset points",fontsize=10,color=colors[model])
    primary=details["primary_workpoint"]
    ax.scatter([primary["W"]+primary["unknown_FA"]],[primary["C"]],marker="s",s=45,color=colors[model],zorder=5)
    ax.annotate(f'fixed: C={primary["C"]}, errors={primary["W"]+primary["unknown_FA"]}',
                (primary["W"]+primary["unknown_FA"],primary["C"]),
                xytext=(-10,14 if model=="old_C"else-25),ha="right",textcoords="offset points",fontsize=9,color=colors[model])
ax.set(xlabel="Observed wrong accepts: known W + unknown FA\n(30 known + 30 unknown queries)",ylabel="Correct accepts C / 30 known queries",
       title="All reachable absolute-score threshold states",xlim=(-1,48),ylim=(0,16))
ax.set_xticks(range(0,49,10));ax.set_yticks(range(0,17,2));ax.grid(axis="y",color="#dde2e8",lw=.6);ax.legend(loc="lower right",frameon=False,fontsize=10)
positions=[];labels=[];stats=[]
for base,(model,prefix)in enumerate([("old_C","Original"),("new_C_domain_seed26","Cows-domain")]):
    for j,(category,kind)in enumerate([("correct_rank1","correct rank-1"),("wrong_rank1","wrong rank-1"),("unknown","unknown")]):
        s=data["models"][model]["score_distributions"][category];pos=base*4+j+1
        positions.append(pos);labels.append(prefix+"\n"+kind+f' (n={s["queries"]})')
        score_ax.plot([s["minimum"],s["maximum"]],[pos,pos],color=colors[model],lw=3)
        score_ax.plot([s["median"]],[pos],marker="o",color="white",markeredgecolor=colors[model],markeredgewidth=1.5,ms=7)
        score_ax.text(s["maximum"]+.003,pos,f'{s["maximum"]:.3f}',va="center",fontsize=9)
score_ax.set_yticks(positions,labels);score_ax.invert_yaxis()
score_ax.set(xlabel="Maximum gallery-ID cosine score",title="Score overlap: min–max lines, median circles",xlim=(.745,.975))
score_ax.grid(axis="x",color="#dde2e8",lw=.6)

fig.suptitle("BECA fixed-transfer scores: post-hoc diagnostic",fontsize=15,y=.985)
fig.text(.5,.035,"Observed-label upper bounds only. No threshold was calibrated or selected for deployment.",ha="center",fontsize=10)
fig.subplots_adjust(left=.07,right=.98,bottom=.19,top=.84,wspace=.70)
paths=[]
for suffix in["png","svg"]:
    p=out/("threshold_score_overlap."+suffix);assert not p.exists();fig.savefig(p,dpi=160,facecolor="white")
    paths.append({"file":str(p.resolve()),"sha256":hashlib.sha256(p.read_bytes()).hexdigest()})
plt.close(fig)
manifest=ROOT/"results/figure_manifest_v2.json";assert not manifest.exists()
manifest.write_text(json.dumps({"created_UTC":datetime.now(timezone.utc).isoformat(),"source_SHA256":hashlib.sha256(source.read_bytes()).hexdigest(),
                                "files":paths,"new_model_forwards":0,"new_pixels_read":0,"rendering_visually_reviewed":False},indent=2)+chr(10))
print(json.dumps({"status":"SCORES_ONLY_FIGURE_WRITTEN","files":paths}))
