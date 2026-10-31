from pathlib import Path,PurePosixPath
from collections import defaultdict
from urllib.parse import unquote
from datetime import datetime,timezone
import gzip,hashlib,json,posixpath,re,shutil
C=Path(__file__).resolve().parent;R=C/'repo';S=Path('C:/Users/Donson/Documents/ChatGPT/奶牛')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
indices=['selected_local_index_v2.json','selected_pynq_index_complete.json','selected_server_index.json']
rows=[];sources=[]
for name in indices:
 p=C/name
 if p.exists():rows.extend(json.loads(p.read_text(encoding='utf-8')));sources.append(name)
by={(r['scope'],r['path']):r for r in rows}
assert len(by)==len(rows)
for row in rows:
 p=R/row['repository_path'];assert p.exists()and p.stat().st_size==row['bytes']and sha(p)==row['sha256'],row['repository_path']
docs=R/'docs';docs.mkdir(exist_ok=True)
prefixes=[('C:/Users/Donson/Documents/ChatGPT/奶牛/','workspace'),
          ('/share/home/renly/projects/idcoo_research_20261026/','server'),
          ('/home/xilinx/jupyter_notebooks/','pynq')]
pattern=re.compile(r'(!?)\[([^\]]*)\]\((?:<([^>]+)>|([^\)]+))\)')
derivatives=[]
for row in rows:
 if not row['path'].lower().endswith('.md'):continue
 source=R/row['repository_path'];friendly=docs/row['repository_path'];friendly.parent.mkdir(parents=True,exist_ok=True)
 text=source.read_text(encoding='utf-8-sig',errors='replace')
 def replace(match):
  bang,label=match[1],match[2];target=unquote((match[3]or match[4]).strip()).replace('\\','/')
  if target.startswith(('http://','https://','mailto:','#')):return match[0]
  path,sep,anchor=target.partition('#');key=None
  for prefix,scope in prefixes:
   if path.lower().startswith(prefix.lower()):key=(scope,path[len(prefix):]);break
  if key is None and not re.match(r'^[A-Za-z]:/',path)and not path.startswith('/'):
   key=(row['scope'],posixpath.normpath(posixpath.join(posixpath.dirname(row['path']),path)))
  selected=by.get(key)
  if selected:
   dest=R/selected['repository_path']
   if selected['path'].lower().endswith('.md'):dest=docs/selected['repository_path']
   relative=posixpath.relpath(dest.relative_to(R).as_posix(),friendly.parent.relative_to(R).as_posix())
   return f'{bang}[{label}](<{relative+("#"+anchor if sep else "")}>)'
  relative=posixpath.relpath('ARCHIVE_CONTENTS.md',friendly.parent.relative_to(R).as_posix())
  return f'[{label}](<{relative}#omitted>)'
 converted=pattern.sub(replace,text)
 friendly.write_text(converted,encoding='utf-8',newline='\n')
 derivatives.append({'source':row['repository_path'],'source_sha256':row['sha256'],'readable_copy':friendly.relative_to(R).as_posix(),'readable_copy_sha256':sha(friendly)})
with gzip.open(R/'archive_inventory/selected_files.jsonl.gz','wt',encoding='utf-8',compresslevel=6)as f:
 for row in rows:f.write(json.dumps(row,ensure_ascii=False,separators=(',',':'))+'\n')
with gzip.open(R/'archive_inventory/readable_copies.jsonl.gz','wt',encoding='utf-8',compresslevel=6)as f:
 for row in derivatives:f.write(json.dumps(row,ensure_ascii=False,separators=(',',':'))+'\n')
groups=defaultdict(lambda:{'count':0,'bytes':0,'reports':[]})
for row in rows:
 if row['scope']!='workspace':continue
 parts=PurePosixPath(row['path']).parts
 if len(parts)<2:continue
 group=groups[parts[0]];group['count']+=1;group['bytes']+=row['bytes']
 if len(parts)==2 and parts[-1].lower().endswith('.md'):group['reports'].append(row)
lines=['# 全部阶段导航','','所有阶段保留原名称，包含失败、不采用和部分结果。最新交接见 [HANDOFF](HANDOFF.md)。','','| 阶段 | 原件文件数 | 报告入口 |','|---|---:|---|']
for name,group in sorted(groups.items()):
 links=[f"[{PurePosixPath(row['path']).name}](<docs/{row['repository_path']}>)"for row in group['reports']]
 lines.append(f"| [{name}](<research/{name}/>) | {group['count']} | {' · '.join(links)if links else'源码、协议及指标见目录'} |")
(R/'STAGE_INDEX.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
scopes=defaultdict(lambda:{'files':0,'bytes':0})
for row in rows:scopes[row['scope']]['files']+=1;scopes[row['scope']]['bytes']+=row['bytes']
complete=all((C/name).exists()for name in indices)
status={'created_UTC':datetime.now(timezone.utc).isoformat(),'archive_scope':'readable_research_results_without_model_or_dataset_payloads',
        'source_scopes':dict(scopes),'selected_original_files':len(rows),'readable_markdown_copies':len(derivatives),
        'all_requested_scopes_collected':complete,'new_experiments_launched_for_archive':0,'automatic_research_stopped':True,
        'research_scientific_goal_claimed_complete':False,'archive_upload_verified':False}
with(R/'archive_inventory/ARCHIVE_STATUS.json').open('w',encoding='utf-8')as f:json.dump(status,f,ensure_ascii=False,indent=2);f.write('\n')
content=['# 归档范围与校验','','本次按用户最终要求，只上传便于分析的研究成果，不上传模型、数据集及大体积原始载荷。','','| 来源 | 文件数 | 原件字节数 |','|---|---:|---:|']
for scope,values in scopes.items():content.append(f"| {scope} | {values['files']} | {values['bytes']} |")
content+=['',f'共{len(rows)}份原件，另提供{len(derivatives)}份GitHub阅读副本。原件保持原字节；阅读副本只转换文件链接。',
          '', '文件清单与每个原件SHA-256见 [selected_files.jsonl.gz](archive_inventory/selected_files.jsonl.gz)。源工作区的全路径筛选记录见 [workspace_all_paths.jsonl.gz](archive_inventory/workspace_all_paths.jsonl.gz)。远端采集清单同目录保存。',
          '', '## omitted','',
          '模型权重、数据集、逐帧图片、视频、原始张量、编译二进制、依赖缓存和大体积传输包按用户要求排除。原路径、来源、配置及已有校验信息保留；原始文件没有删除。阅读副本中指向未上传载荷或本机外部路径的链接汇总到本节。',
          '', '分析图表、拼图、指标、事件／时序记录、源代码、实验参数、成功与失败记录均保留；未把实验失败改成完成，也未将候选身份改成确认身份。',
          '', '自动科研已停止。归档上传完成后结束目标，后续由用户分析、指导。']
(R/'ARCHIVE_CONTENTS.md').write_text('\n'.join(content)+'\n',encoding='utf-8')
u=R/'user_inputs';u.mkdir(exist_ok=True)
attachment=Path('C:/Users/Donson/.codex/attachments/f33838e4-77d9-4bff-b76d-2b154b25e824/已粘贴的文本.txt')
if attachment.exists()and not(u/'initial_project_context.txt').exists():shutil.copyfile(attachment,u/'initial_project_context.txt')
(u/'archive_scope.md').write_text('# 用户最终归档范围\n\n用户要求把本对话所有成果上传到DonsonHH/Cowyolo26，由用户自行分析后续工作；上传任务完成即结束原目标。\n\n随后补充：大的模型文件和数据集不必上传，目的是分析后续方向与优化，而非查看数据集和模型文件。\n\n此要求覆盖历史自动续跑计划；本次只做归档与校验。\n',encoding='utf-8')
print(json.dumps(status,ensure_ascii=False))
