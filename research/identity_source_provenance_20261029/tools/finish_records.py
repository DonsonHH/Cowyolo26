from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):assert not p.exists();p.write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8')
def main():
    source=load(ROOT/'results/source_review_record.json');key=load(ROOT/'results/key_evidence_figures_v2.json');sheets=[]
    for page in source['pages']:
        assert sha(Path(page['path']))==page['sha256'];ID=page['template_rows'][0]['anonymous_ID']
        sheets.append({'path':page['path'],'sha256':page['sha256'],'rows':5,'panel_slots':15,
            'actual_image_panels':10+sum(r['rewarp_path'] is not None for r in page['template_rows']),
            'actual_visual_review':'PASS','observations':
              'ID009: middle3source rewarps closely match published images; endpoints weaker. Native projected regions visibly on same right-hand track through source sequence.' if ID=='009' else
              f'ID{ID}: all5gallery images, native search suggestions, degenerate or absent warps shown; rejection labels clear. No rejected match is adopted as identity truth.'})
    for name in ['core','endpoints']:
        row=key[name];assert sha(Path(row['path']))==row['sha256']
        sheets.append({'path':row['path'],'sha256':row['sha256'],'rows':3 if name=='core' else 2,'panel_slots':row['panels'],
            'actual_image_panels':row['panels'],'actual_visual_review':'PASS','observations':
              'Three publishedID009 / native source / rewarp rows, metrics and source-track102 linkage readable. V2moves metric text below native picture and avoids overlap.' if name=='core' else
              'Weak first endpoint0.7516and strong last photometry0.9965with original geometryREJECT shown. No threshold relaxation; limitations readable.'})
    assert len(sheets)==8 and sum(r['actual_image_panels'] for r in sheets)==95
    save(ROOT/'evidence/visual_review.json',{'status':'ALL30_GALLERY_RESULTS_AND_TWO_KEY_SOURCE_EVIDENCE_FIGURES_ACTUALLY_VIEWED',
        'created_UTC':datetime.now(timezone.utc).isoformat(),'current_sheets':sheets,'current_sheets_viewed':8,
        'actual_image_panels_viewed':95,'empty_unfitted_panel_slots':8,'prior_layout_versions_retained':True,
        'independent_human_identity_acceptance':False})
    mapping=load(ROOT/'results/photometry_and_event_link_verification.json')
    save(ROOT/'results/evaluation_admission.json',{
        'status':'CURRENT_E010_ID009_AUG14_GALLERY_PAIR_EXCLUDED_FROM_INDEPENDENT_IDENTITY_EVALUATION',
        'created_UTC':datetime.now(timezone.utc).isoformat(),'reason':'Three published gallery crops align to native source frames in the same baseline track102passage used by E010query.',
        'source_link_verification_sha256':sha(ROOT/'results/photometry_and_event_link_verification.json'),
        'affected_event_id':'E010_f9790_tid102','affected_query_source_frame0':9745,'affected_count_event_frame0':9790,
        'affected_gallery_day':'2023Aug14','affected_gallery_public_anonymous_ID':'009','core_geometry_source_pairs':mapping['core_same_source_capture_candidates'],
        'reference_authority':'Computed geometric/pixel provenance candidate plus assistant source review; no independent human label acceptance.',
        'allowed_use':'Functional/development replay with full provenance disclosure.',
        'independent_event_identity_accuracy_admitted':False,'training_or_new_threshold_label_admitted':False,
        'source_cow_identity_reference_promoted':False,'ear_tag_identity_mapping_proven':False,
        'other25_gallery_images_absence_or_identity_error_inferred':False,
        'existing_Aug20_curated_query_results_recomputed_or_invalidated_in_this_audit':False,
        'original_human12_count_milestone_preserved':True,'original_model_gallery_thresholds_or_raw_files_changed':False,
        'new_identity_model_forwards':0,'new_training_updates':0,'FPGA_execution_verified':False,'whole_goal_complete':False})
    link='<C:/Users/Donson/Documents/ChatGPT/奶牛/identity_source_provenance_20261029/原视频身份来源核查与评价准入.md>'
    paragraphs={
      '研究进度.md':f'最新完成[原视频身份来源核查与评价准入]({link})：正式ZIP103156目录及.info.json101467文件记录没有发布图→源帧CSV，30图库和原视频官方校验值一致，102作者源文件核对。全部30图库的13050粗／300细几何比较，在ID009三图与9610／9685／9760帧得到NCC约0.996，均关联基线轨迹102／E010；查询9745帧与当前图库有强同次通行重叠证据，已排除独立身份评价。两端弱匹配及边界拒绝保留，020无可靠来源不推定错误。八页95图像面板核查，未调用身份编码器、未改模型／参考，原12头成果保持；后续先固定来源分组和跨通行登记／查询，再评价身份及上板。',
      '研究总览_从想法到论文.md':f'最新[身份来源审计]({link})发现当前E010／ID009图库存在强同次通行重叠：三张正式Aug14登记图能与原视频9610、9685、9760帧像素对齐，均落在该次轨迹。它们不能用于独立事件身份准确率，已另存准入排除，历史功能输出和原片人工12头计数保持。正式包及102作者源文件没有找到发布图到源帧的显式映射；几何搜索覆盖全部30图库，成功／失败和端点限制保留，未以模型分数生成真值。下一步优先来源隔离的登记／查询与有标签裁剪域，PYNQ-Z2联合关口继续待验。',
      'phase3_diagnosis_20261026/方案与执行状态.md':f'新增完成[原视频与作者ID来源审计]({link})：官方全ZIP目录、101467文件元数据、30JPEG与原视频CRC／SHA、102源码核查；全部30图库435粗帧及191细帧搜索找到ID009三强来源对齐，关联E010同次通行，当前这组图库／查询不准入独立身份测试。独立几何／像素及八页95面板核查通过，弱首端、末端几何拒绝、其他身份未匹配限制均保留。没有新神经前向／训练，原12头、图库及阈值保持；后续固定来源分组与跨通行评价。'}
    for name,paragraph in paragraphs.items():
        path=PROJECT/name;text=path.read_text(encoding='utf-8');assert 'identity_source_provenance_20261029' not in text
        parts=text.split('\n\n',2);assert parts[0].startswith('# ') and '更新' in parts[1]
        path.write_text(parts[0]+'\n\n'+parts[1]+'\n\n'+paragraph+'\n\n'+parts[2],encoding='utf-8')
    path=PROJECT/'phase3_diagnosis_20261026/方案与执行状态.md';lines=path.read_text(encoding='utf-8').splitlines(keepends=True)
    index=next(i for i,line in enumerate(lines) if line.startswith('| I1 身份基线'))
    lines.insert(index+1,'| I2 原视频身份来源 | 正式目录／元数据与几何像素追溯，绑定图库及源事件 | 保留完整范围、正负对照与无对应结果，不用ReID分数造真值 | 已发现E010／ID009同通行来源重叠并排除独立评价；其他事件身份仍待对应 |\n')
    path.write_text(''.join(lines),encoding='utf-8')
    path=ROOT/'计划与验收.md';text=path.read_text(encoding='utf-8');assert '执行结果：' not in text
    text+='\n执行结果：全103156ZIP目录、101467文件元数据及102作者源文件已核查；30图库无EXIF源帧，官方校验值通过。三个Slurm作业130396／130399／130415均COMPLETED／0:0。13050粗／300细比较得ID009三强来源对齐并联系E010，当前同通行图库／查询排除独立评价；弱首端和末端边界拒绝保留。7像素对与变换／排序独立复算，八页95图像面板目视。原12头计数和图库／模型／阈值保持，详见[结果及后续](<C:/Users/Donson/Documents/ChatGPT/奶牛/identity_source_provenance_20261029/原视频身份来源核查与评价准入.md>)。\n'
    path.write_text(text,encoding='utf-8')
    print(json.dumps({'current_source_review_sheets':8,'actual_image_panels':95,'independent_identity_pair_excluded':'E010/009Aug14',
                      'source_identity_promoted':False,'research_entries_updated':3}))
if __name__=='__main__':main()
