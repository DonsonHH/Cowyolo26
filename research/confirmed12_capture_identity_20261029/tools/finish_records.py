from pathlib import Path
from datetime import datetime,timezone
import ast,hashlib,json,subprocess,sys
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    graphics=load(ROOT/'results/review_images_record.json');sheets=[]
    for index,row in enumerate(graphics['pages']):
        assert sha(Path(row['path']))==row['sha256']
        notes=['E001-003 source boxes and oriented crops agree; all five reject and source identity remains unknown.',
               'E004-006 include dense adjacent cows; E005 has onlyC26 slight threshold crossing, other conditions reject.',
               'E007-009 show neighbouring-body edges or partial crops and all rejections; no omitted source case.',
               'E010 showsC27/C28 candidate009; E011/012 remain rejected. Crop and source labels readable.'][index]
        sheets.append({'path':row['path'],'sha256':row['sha256'],'image_panels':6,'actual_visual_review':'PASS','observations':notes})
    sheets.append({'path':graphics['candidate_comparison_path'],'sha256':graphics['candidate_comparison_sha256'],
                   'image_panels':6,'actual_visual_review':'PASS',
                   'observations':'Three real threshold-crossing condition pairs shown: E005C26ID020 and E010C27/C28ID009. Actual gallery image borders, differing orientation and unverified status remain visible.'})
    assert len(sheets)==5 and sum(r['image_panels'] for r in sheets)==30
    record={'status':'FIVE_CAPTURE_AND_CANDIDATE_SHEETS_THIRTY_IMAGE_PANELS_ACTUALLY_VIEWED',
        'created_UTC':datetime.now(timezone.utc).isoformat(),'sheets':sheets,
        'source_identity_reference_independently_accepted':False,'threshold_crossing_is_identity_success':False,'whole_goal_complete':False}
    target=ROOT/'evidence/visual_review.json';assert not target.exists();target.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    test=subprocess.run([sys.executable,str(ROOT/'input/test_snapshot_bank.py')],capture_output=True,text=True,encoding='utf-8')
    assert test.returncode==0 and 'Ran 8 tests' in test.stderr and test.stderr.rstrip().endswith('OK')
    output=ROOT/'evidence/snapshot_tests.txt';assert not output.exists();output.write_text(test.stdout+test.stderr,encoding='utf-8')
    for name in ['run_chain.py','identity_worker.py','verify_remote.py','render_review.py']:ast.parse((ROOT/'tools'/name).read_text(encoding='utf-8'))
    link='<C:/Users/Donson/Documents/ChatGPT/奶牛/confirmed12_capture_identity_20261029/12事件原图抓拍与身份查询结果.md>'
    paragraphs={
      '研究进度.md':f'最新完成[人工12头版本的原图抓拍与真实身份查询链路]({link})：冻结计数缓存驱动原视频实际解码，12事件均保存2560×1440照片，CPU后台完成60真实查询；10事件五配置全拒，E005候选020及E010候选009仍未核实。新进程重跑60查询、5自查询接口正对照、12源JPEG／36质量像素及1800图库分数复算通过；72交付栅格与5页30面板核查。无功能任务遗漏或EOF后完成，但未计算身份准确率、未模拟真实RF或前台YOLO负载。当前12头计数成果保持，下一步推进有标签裁剪域、读码异常链路与板上联合验证。',
      '研究总览_从想法到论文.md':f'最新[12事件抓拍与后台身份链路]({link})已实际运行：保留人工12头达标计数，12张原分辨率照片对应60次真实CPU模型查询，2事件出现匿名020／009候选、其余10事件全部拒识。权重、图库、阈值未改，源像素、因果选图、任务终态、图库分数及新进程重复前向均复核。两个候选没有独立身份参考，不能作为正确找回数；本轮检测来自缓存，尚无PYNQ-Z2联合性能。原关联基线与先前不利结果保持，下一步继续身份对应、裁剪域及真实读码／单板验收。',
      'phase3_diagnosis_20261026/方案与执行状态.md':f'新增完成[人工12头计数到原图抓拍与身份查询]({link})：12事件／12原图／12后台任务，五冻结配置共60实际CPU查询，全部EOF前完成。10事件全拒、2事件候选未核实；60新进程重复、5接口自查询、12源照片／36质量图及1800分数独立核查通过。只重放冻结检测观察，不报告本轮YOLO／PYNQ速度，不改变原12头版本或身份阈值。后续继续有标签身份／裁剪域和异常读码条件，板上前后台共同运行仍待实测。'}
    for name,paragraph in paragraphs.items():
        path=PROJECT/name;text=path.read_text(encoding='utf-8');assert 'confirmed12_capture_identity_20261029' not in text
        parts=text.split('\n\n',2);assert parts[0].startswith('# ') and '更新' in parts[1]
        path.write_text(parts[0]+'\n\n'+parts[1]+'\n\n'+paragraph+'\n\n'+parts[2],encoding='utf-8')
    path=PROJECT/'phase3_diagnosis_20261026/方案与执行状态.md';text=path.read_text(encoding='utf-8')
    row='| V2 人工12头链路更新 | 固定达标计数观察接入源图抓拍与真实CPU后台 | 12事件照片／任务终态、源像素、独立匹配及重复查询；身份未核实不认领找回 | 已完成12原图／60查询，10全拒／2未核实候选；无功能任务遗漏，实际RF和板上联合仍待验 |\n'
    lines=text.splitlines(keepends=True);index=next(i for i,l in enumerate(lines) if l.startswith('| V1 真实视频抓拍链路'))
    lines.insert(index+1,row);path.write_text(''.join(lines),encoding='utf-8')
    path=ROOT/'计划与验收.md';text=path.read_text(encoding='utf-8');assert '执行结果：' not in text
    text+='\n执行结果：130360／130361均COMPLETED／0:0，53秒／20秒；12事件全部抓拍并完成60真实查询，10全拒、2未核实候选。60新进程重跑和5接口正对照、12照片源SHA／36候选质量像素／1800图像分数及5页30面板核查通过，8既有行为测试通过。计数／身份权重和阈值保持，未新增检测前向或训练，未认领身份准确率或板上性能。见[结果与下一步](<C:/Users/Donson/Documents/ChatGPT/奶牛/confirmed12_capture_identity_20261029/12事件原图抓拍与身份查询结果.md>)。\n'
    path.write_text(text,encoding='utf-8')
    print(json.dumps({'visual_sheets':5,'visual_image_panels':30,'snapshot_tests':8,'research_entries_updated':3,'source_identity_accuracy':None}))
if __name__=='__main__':main()
