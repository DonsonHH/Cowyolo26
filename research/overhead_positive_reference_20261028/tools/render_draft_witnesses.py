"""Assemble explicitly selected original-pixel witnesses for a provisional visual reference."""
from pathlib import Path
import argparse,hashlib,json
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def font(n):return ImageFont.truetype('C:/Windows/Fonts/arial.ttf',n)
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--corrected',action='store_true');args=parser.parse_args()
    out=ROOT/'results'/('draft_witnesses_v2' if args.corrected else 'draft_witnesses');out.mkdir(exist_ok=False)
    # Initial visual hypotheses from all1Hz contact panels. Witnesses must still
    # be inspected; these entries are not event ground truth or model output.
    definitions=[
      ('R01','group_passage','Leading right cow, mostly dark torso with white transverse/rump marking',2590,2650),
      ('R02','group_passage','Left cow behind leading cow, large white body patches and black shoulders',2615,2690),
      ('R03','group_passage','Right cow in first group, dark torso with narrow white transverse marks',2630,2705),
      ('R04','group_passage','Rear-left cow in first group, predominantly white speckled torso',2650,2705),
      ('R05','group_passage','Separate black-white patched cow after first group/person',2860,2925),
      ('R06','group_passage','Separate dark cow with small white rump marking around131s',3310,3375),
      ('R07','group_passage','Dark cow with tiny dorsal white spot, following around140s',3520,3625),
      ('R08','group_passage','Next predominantly dark cow, small white mark near rump',3620,3700),
      ('R09','group_passage','Right member of later pair, dirty pale rump and dark torso',3740,3850),
      ('R10','group_passage','Left member of later pair, white neck band and dorsal stripe',3740,3825),
      ('R11','group_passage','Final group cow, broad white back with large dark patches',3910,4025),
      ('R12','late_single','Later isolated predominantly white cow with a few dark back spots',5200,5325)
    ]
    if args.corrected:
        corrections={'R01':(2605,2665),'R02':(2645,2690),'R03':(2655,2705),'R04':(2670,2715)}
        definitions=[(ID,window,description,*(corrections.get(ID,(A,B)))) for ID,window,description,A,B in definitions]
    rows=[]
    for ID,window,description,A,B in definitions:
        frames=[A,A+5,A+10,B,B+5,B+10];panels=[];witnesses=[]
        for i,frame in enumerate(frames):
            path=ROOT/'focused_delivery/results/focused'/window/f'ROI_{frame:05d}.jpg'
            with Image.open(path) as im:
                im.load();assert im.size==(1050,1440);small=im.convert('RGB').resize((420,576))
            d=ImageDraw.Draw(small)
            for y in [576,864]:d.line([(0,y*.4),(419,y*.4)],fill='#25d9cb',width=3)
            panel=Image.new('RGB',(420,620),'#111827');d=ImageDraw.Draw(panel)
            d.text((8,4),f"{ID} | {'A witness' if i<3 else 'B witness'} | frame0 {frame}",font=font(20),fill='white')
            d.text((8,26),f'{frame/25:.2f}s | original native crop',font=font(18),fill='#fbbf24')
            panel.paste(small,(0,44));panels.append(panel)
            witnesses.append({'region_hypothesis':'A' if i<3 else 'B','frame0':frame,'time_s_nominal':frame/25,
                              'source_image':str(path.relative_to(ROOT)),'source_sha256':sha(path),
                              'manual_centre_verified':False})
        sheet=Image.new('RGB',(1260,1280),'#111827');d=ImageDraw.Draw(sheet)
        d.text((12,6),f'PROVISIONAL {ID}: raw witnesses, no model boxes; centre and association still to inspect',font=font(22),fill='white')
        for i,panel in enumerate(panels):sheet.paste(panel,((i%3)*420,40+(i//3)*620))
        dest=out/(ID+'_A_B_witnesses.jpg');sheet.save(dest,quality=95)
        rows.append({'reference_ID':ID,'window':window,'description':description,'witnesses':witnesses,
                     'contact':dest.relative_to(ROOT).as_posix(),'contact_sha256':sha(dest),'status':'CANDIDATE_WITNESSES_PENDING_VISUAL_CHECK'})
    result={'status':'TWELVE_CANDIDATE_NATIVE_WITNESS_SHEETS_PREPARED','reference_authority':'assistant provisional, not human or publisher GT',
            'candidate_count_is_not_accepted_truth':True,'candidates':rows,'revision':'v2' if args.corrected else 'v1',
            'correction_reason':'First four A witnesses shifted to more visible torsos; R01/R04 B witnesses moved away from the destination boundary. Original sheets retained.' if args.corrected else None,
            'new_model_predictions':0,'whole_goal_complete':False}
    (out/'manifest.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps({'candidate_sheets':len(rows),'panels':sum(len(r['witnesses']) for r in rows)}),flush=True)
if __name__=='__main__':main()
