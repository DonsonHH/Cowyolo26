from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
for name in ['check_catalog_intake.py','verify_media_archive.py','prepare_media.py','finish_media.py']:
    source=(PROJECT/'secondstage_iou_20261028/tools'/name).read_text(encoding='utf-8')
    if name=='check_catalog_intake.py':
        source=source.replace('frozen_prediction_catalog_v3','frozen_prediction_catalog_v4')
        source=source.replace("c['conditions'][:23]","c['conditions'][:26]").replace("len(c['conditions'])==26","len(c['conditions'])==29")
        source=source.replace("len(c['paired_comparisons'])==6","len(c['paired_comparisons'])==9").replace("c['paired_comparisons'][3:]","c['paired_comparisons'][6:]")
        source=source.replace("result['conditions']==26","result['conditions']==29").replace("len(scores['conditions'])==26","len(scores['conditions'])==29")
        source=source.replace("len(scores['paired_changes'])==6","len(scores['paired_changes'])==9").replace("len(list(csv.DictReader(f)))==52","len(list(csv.DictReader(f)))==58")
        source=source.replace('known_QA_26_conditions_blocked','known_QA_29_conditions_blocked').replace('CURRENT26_','CURRENT29_')
        source=source.replace("'conditions':26,'preserved_records':23,'pairs':6","'conditions':29,'preserved_records':26,'pairs':9")
        source=source.replace("'software_fixture_scored_conditions':26,'software_fixture_direction_rows':52","'software_fixture_scored_conditions':29,'software_fixture_direction_rows':58")
    elif name=='verify_media_archive.py':
        source=source.replace("==25 and len(members)","==28 and len(members)").replace("==26\n","==29\n")
        source=source.replace('ALL25_MEDIA_ARCHIVE_FILES','ALL28_MEDIA_ARCHIVE_FILES').replace("'files':25","'files':28")
    elif name=='prepare_media.py':
        source=source.replace("['files']==25","['files']==28")
        source=source.replace("r['variant']=='secondstage_iou'","r['variant']=='allow_lost_iou'").replace("r['variant']=='installed_baseline'","r['variant']=='active_only_iou'")
        source=source.replace("f'secondstage_iou_seed{seed}_f8912-10873'","f'lost_recovery_seed{seed}_f8912-10873'")
        source=source.replace('第二阶段纯IoU · seed','Lost低分恢复 · seed')
        source=source.replace("PROJECT/'confirmation_handoff_20261028/results/media_verification.json'","PROJECT/'secondstage_iou_20261028/results/media_verification.json'")
        source=source.replace("f'confirmation_handoff_seed{seed}_f8912-10873'","f'secondstage_iou_seed{seed}_f8912-10873'")
        source=source.replace("c['applied_low_stage_matches_in_scope']","c['lost_recoveries_in_scope']")
        source=source.replace("['event_times_and_directions_exact_without_ID']","['times_and_directions_exact']")
        source=source.replace("'secondstage_iou_seed26'","'allow_lost_iou_seed26'")
        source=source.replace('secondstage_iou_preview','lost_recovery_preview')
        source=source.replace("PROJECT/f'confirmation_handoff_20261028/delivery/results/replay_v2/seed{seed}'","PROJECT/f'secondstage_iou_20261028/media_delivery/results/secondstage_iou_seed{seed}'")
        source=source.replace("f9420.jpg","f9365.jpg").replace('source9420','source9365').replace('Secondstage IoU','Lost low recovery')
    elif name=='finish_media.py':
        source=source.replace("len(b['tests'])==12","len(b['tests'])==12")
    path=ROOT/'tools'/name;assert not path.exists();path.write_text(source,encoding='utf-8')
source=(PROJECT/'secondstage_iou_20261028/templates/preview.html').read_text(encoding='utf-8')
source=source.replace('第二阶段纯IoU配对对照','Lost低分恢复配对对照').replace('奶牛通道：低分匹配恢复，事件数量未变','奶牛通道：Lost恢复后，完整事件仍未增加')
source=source.replace('confirmation_handoff_preview.html','secondstage_iou_preview.html').replace('secondstage_iou_preview_data.json','lost_recovery_preview_data.json')
start=source.index('<div class="notice">');end=source.index('</div>',start)+6
source=source[:start]+'<div class="notice">右侧仅让保留池中的Lost轨迹也参加低分第二阶段匹配；纯IoU代价、0.5门槛、第一阶段与确认交接计数不变。三组预测仍12／11／11，事件时间和方向一致。新增恢复不等于正确找回奶牛，独立参考仍待提供。</div>'+source[end:]
source=source.replace('原第二阶段：分数融合代价','原资格：只允许Tracked轨迹')
source=source.replace('；第二阶段纯IoU，计数规则相同','；Lost可参与低分恢复，计数规则相同')
source=source.replace('本段低分匹配次数','本段Lost恢复次数')
source=source.replace('低分匹配次数统计本时间段全画面，不等于ROI奶牛数量。全部三个seed及无新增事件结果均保留；当前不将该控制认领为计数准确率改进。',
 'Lost恢复次数统计本时间段全画面，共33次，其中原始低分框中心在ROI内的4次已逐例检查；次数不等于不同奶牛数量。全部seed和无新增事件结果保留。')
folder=ROOT/'templates';folder.mkdir(exist_ok=True);target=folder/'preview.html';assert not target.exists();target.write_text(source,encoding='utf-8')
print('catalog verification and media/page tools prepared from reviewed previous phase')
