from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,subprocess,sys
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    plots=load(ROOT/'results/plot_verification.json');sheets=[]
    for row in plots['files']:
        if not row['path'].endswith('.png'):continue
        assert sha(Path(row['path']))==row['sha256']
        note='All12 row counts, six state colors, pressure separation, legends and synthetic-data caveat readable.' if 'controlled_outcomes' in row['path'] else \
             'Twelve counted intervals,5green7amber, source seconds, and two-window E007 detail at9460/9480 checked; open track98 stays open in causal detail, retrospective labels explained.'
        sheets.append({'path':row['path'],'sha256':row['sha256'],'actual_visual_review':'PASS','observations':note})
    assert len(sheets)==2
    visual={'status':'TWO_RF_STATE_AND_CAUSAL_WINDOW_FIGURES_ACTUALLY_VIEWED',
            'created_UTC':datetime.now(timezone.utc).isoformat(),'figures':sheets,'panels_viewed':3,
            'actual_RF_hardware_or_identity_truth_inferred':False}
    path=ROOT/'evidence/visual_review.json';assert not path.exists();path.write_text(json.dumps(visual,indent=2)+'\n',encoding='utf-8')
    tests=subprocess.run([sys.executable,str(ROOT/'tests/test_stream_linker.py')],capture_output=True,text=True,encoding='utf-8')
    assert tests.returncode==0 and 'Ran 14 tests' in tests.stderr and tests.stderr.rstrip().endswith('OK')
    path=ROOT/'evidence/stream_tests.txt';assert not path.exists();path.write_text(tests.stdout+tests.stderr,encoding='utf-8')
    link='<C:/Users/Donson/Documents/ChatGPT/奶牛/confirmed12_rf_stream_20261029/12事件流式读码与真实查询异常验证.md>'
    paragraphs={
      '研究进度.md':f'最新完成[12事件流式读码与真实查询异常验证]({link})：10个功能条件＋2个真实进程压力控制，144条台账与515次实际身份配置查询全部保留。每事件一码时5唯一候选／7共享转视觉，同码重传与截止内延迟一致；迟到不倒填，唯一错码仍有5错误模拟候选的局限保留。突发4接收／8拒绝，过期4项不执行查询；所有RF都是合成输入，不计真实身份准确率。120上下文／16898关系、15450图库分数及3090身份分数独立核对，14检查及两科学图目视完成。原12头与照片／模型／阈值保持，下一步优先查原视频与作者匿名ID的可靠来源对应，再做身份评价和单板验证。',
      '研究总览_从想法到论文.md':f'最新[流式RF入口与实际身份回退实验]({link})把12事件照片接入10种合成读码输入和2个真实队列压力控制，形成144条明确终态。关联器保留未计数邻轨迹，S01为5唯一RF候选／7共享；故意单码错误仍可产生错误模拟候选，因此唯一性不等于身份正确。515实际配置查询、独立读码窗口／图库分数和两图核查完成，原计数成功版本保持。它是源事件复用的软件系统实验，没有真实RF、独立身份准确率或PYNQ联合结果；下一步收敛到原视频身份来源对应、有标签裁剪域及板上验收。',
      'phase3_diagnosis_20261026/方案与执行状态.md':f'新增完成[12事件流式RF与真实后台异常／压力验证]({link})：未完成邻窗口也参与共享判定，10功能＋2压力共144台账，515实际配置查询。5唯一／7共享、迟到不倒填、单码错误局限、4接收／8拒绝和4过期零查询均保留。120上下文／16898关系与15450余弦独立核查、14检查及两图目视通过；同12事件重复不当144头独立牛，模型／照片／阈值未改。后续优先身份来源对应与有标签评价，实际RF及PYNQ-Z2关口继续待验。'}
    for name,paragraph in paragraphs.items():
        path=PROJECT/name;text=path.read_text(encoding='utf-8');assert 'confirmed12_rf_stream_20261029' not in text
        parts=text.split('\n\n',2);assert parts[0].startswith('# ') and '更新' in parts[1]
        path.write_text(parts[0]+'\n\n'+parts[1]+'\n\n'+paragraph+'\n\n'+parts[2],encoding='utf-8')
    path=PROJECT/'phase3_diagnosis_20261026/方案与执行状态.md';text=path.read_text(encoding='utf-8');lines=text.splitlines(keepends=True)
    i=next(i for i,line in enumerate(lines) if line.startswith('| V2 人工12头链路更新'))
    lines.insert(i+1,'| R2 流式RF与真实回退 | 未完成视觉窗口、实际CPU查询、受控容量／过期 | 144台账闭合；独立关系／分数与错误输入保留 | 已完成10功能＋2压力、515查询、14检查；RF仍合成，身份及板上未验 |\n')
    path.write_text(''.join(lines),encoding='utf-8')
    path=ROOT/'计划与验收.md';text=path.read_text(encoding='utf-8');assert '执行结果：' not in text
    text+='\n执行结果：CPU130362完成2分19秒／0:0，绘图130363完成2秒／0:0。10功能＋2真实压力控制的144台账闭合，515实际查询；5唯一／7共享、迟到、单码错误、4接收／8拒绝和4过期均保留。120上下文／16898关系、15450余弦／3090身份分数独立核对，14检查与两图3面板目视通过。全部照片和原12头成果保持；详见[本轮结果](<C:/Users/Donson/Documents/ChatGPT/奶牛/confirmed12_rf_stream_20261029/12事件流式读码与真实查询异常验证.md>)。\n'
    path.write_text(text,encoding='utf-8')
    print(json.dumps({'figures_actually_viewed':2,'panels':3,'stream_tests':14,'research_entry_points_updated':3}))
if __name__=='__main__':main()
