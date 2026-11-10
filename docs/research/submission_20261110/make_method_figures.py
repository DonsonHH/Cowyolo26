"""Original vector method diagrams; no third-party photos or experimental claims."""
from pathlib import Path
import hashlib
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch,Rectangle,Ellipse

root=Path(__file__).resolve().parent
out=root/'figures';out.mkdir(exist_ok=True)
BLUE='#0072B2';ORANGE='#D55E00';GRAY='#66717C';INK='#182734';GREEN='#009E73'
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':8,'pdf.fonttype':42,
                     'svg.fonttype':'none','axes.linewidth':.7})
def box(ax,x,y,w,h,text,color=BLUE,size=8):
    ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0.01,rounding_size=0.025',
        facecolor=color+'0C',edgecolor=color,linewidth=1.0))
    ax.text(x+w/2,y+h/2,text,ha='center',va='center',fontsize=size,color=INK)
def arrow(ax,a,b,color=GRAY,style='-'):
    ax.annotate('',xy=b,xytext=a,arrowprops=dict(arrowstyle='->',color=color,lw=1.0,linestyle=style))
def export(fig,name):
    for ext in ('pdf','svg','png'):fig.savefig(out/(name+'.'+ext),dpi=400,bbox_inches='tight',pad_inches=.04)
    plt.close(fig)

fig,ax=plt.subplots(figsize=(7.16,2.8));ax.set(xlim=(0,10),ylim=(0,4));ax.axis('off')
ax.text(.05,3.76,'Same graph. Same number of real calls. Different observations.',fontsize=10,weight='bold',color=INK)
for x,label in [(1.45,'0.0'),(2.9,'0.2'),(4.35,'0.4'),(5.8,'0.6'),(7.25,'0.8')]:
    ax.add_patch(Rectangle((x-.12,3.0),.24,.26,facecolor='#E3E7EB',edgecolor=GRAY,lw=.6))
    ax.text(x,3.43,label,ha='center',fontsize=8)
arrow(ax,(1.1,2.9),(8.2,2.9))
ax.text(8.4,3.17,'Source time (s)',va='center',fontsize=8)
ax.text(.05,2.2,'A',fontsize=11,weight='bold',color=BLUE)
ax.text(.05,1.25,'B',fontsize=11,weight='bold',color=ORANGE)
for x,y,text,c in [(1.45,2.23,'Global\nimage 0',BLUE),(4.35,2.23,'Global\nimage 2',BLUE),
                   (1.45,1.25,'Global\nimage 0',BLUE),(4.35,1.25,'Local crop\nof image 0',ORANGE)]:
    box(ax,x-.67,y-.28,1.34,.57,text,c)
arrow(ax,(2.17,2.23),(3.62,2.23),BLUE)
arrow(ax,(2.17,1.25),(3.62,1.25),ORANGE)
ax.text(2.9,.72,'Eligibility uses image 0 and past state;\nimage 2 content does not select the crop.',
        ha='center',va='center',fontsize=7.7,color=GRAY)
box(ax,6.0,1.3,3.7,1.24,'No local proposal:\nuse global image 2.\n\nTwo real calls per 0.8-s block.',GREEN,8)
ax.text(.05,.12,'Only measured positions can complete a passage. Same-image detections are fused before one tracking update.',
        fontsize=7.5,color=GRAY)
export(fig,'budget_schematic')

fig,ax=plt.subplots(figsize=(7.16,3.15));ax.set(xlim=(0,10),ylim=(0,4.6));ax.axis('off')
ax.text(5,4.36,'Global observation and local verification',ha='center',fontsize=13,weight='bold',color=INK)
ax.text(5,4.0,'Fixed detection budget for embedded cattle passage counting',ha='center',fontsize=9,color=GRAY)
for x,label in [(.2,'Observe'),(3.55,'Allocate'),(6.92,'Count and time')]:
    ax.text(x+.1,3.5,label,fontsize=10,weight='bold',color=INK)
box(ax,.2,.62,2.85,2.62,'',BLUE)
ax.add_patch(Rectangle((.75,1.0),1.7,1.9,fill=False,edgecolor=GRAY,lw=1))
for y in (1.45,2.46):ax.plot([.75,2.45],[y,y],color=ORANGE,lw=1.4)
for y in (1.42,2.1,2.78):
    ax.add_patch(Ellipse((1.6,y),.49,.56,facecolor='#E4E9EC',edgecolor=INK,lw=.9))
    ax.add_patch(Ellipse((1.6,y+.28),.25,.14,facecolor='white',edgecolor=INK,lw=.7))
arrow(ax,(2.75,1.2),(2.75,2.8),BLUE)
ax.text(1.62,.83,'Two separated zones',ha='center',fontsize=7)
arrow(ax,(3.08,2.0),(3.47,2.0))
box(ax,3.55,.62,2.85,2.62,'',ORANGE)
box(ax,3.85,2.43,2.25,.46,'Global image',BLUE)
arrow(ax,(4.98,2.39),(4.98,2.05))
box(ax,3.85,1.43,2.25,.54,'Next global image\nor same-image crop',ORANGE)
ax.text(4.98,1.08,'Same static detector graph',ha='center',fontsize=7.5,color=INK)
ax.text(4.98,.83,'Equal real call quota',ha='center',fontsize=8,weight='bold',color=ORANGE)
arrow(ax,(6.44,2.0),(6.84,2.0))
box(ax,6.92,.62,2.85,2.62,'',GREEN)
ax.text(8.35,2.72,'PYNQ-Z2',ha='center',fontsize=11,weight='bold',color=INK)
ax.text(8.35,2.17,'Directional passage totals\nActual global / local calls\nPublication age and queue',
        ha='center',va='center',fontsize=8.3,linespacing=1.6,color=INK)
ax.text(8.35,1.08,'Wall-paced source replay',ha='center',fontsize=8,color=GRAY)
ax.text(5,.18,'Temporary tracking IDs support counting; persistent cow identity is a separate task.',
        ha='center',fontsize=7.7,color=GRAY)
export(fig,'graphical_abstract')
manifest={'figure_source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
          'source':'Original matplotlib vector drawings; no dataset pixels or external assets.',
          'new_model_forwards':0,
          'files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.suffix in ('.pdf','.svg','.png')}}
(out/'METHOD_FIGURE_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(manifest,indent=2))
