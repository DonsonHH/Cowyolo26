from pathlib import Path
from datetime import datetime,timezone
import json

ROOT=Path(__file__).resolve().parents[1]
def load(path):return json.loads(path.read_text())

v=load(ROOT/'results/independent_verification.json');t=load(ROOT/'evidence/result_transfer.json')
assert v['status']=='FULL97_ARM_INPUTS_RAW_FEATURES9_ANCHORS120_DECISIONS_AND_TERMINAL_STATE_INDEPENDENTLY_RECOMPUTED'
report=f'''# 新身份候选的PYNQ-Z2 ARM实机验证与研究决定

2026年10月30日。**新域适配编码器已在真实PYNQ-Z2上执行97次正式图像推理及2次预热，120条身份检索决定与参考一致。** 网络张量到576维特征平均{v['mean_network_ms']:.2f}ms、P95为{v['P95_network_ms']:.2f}ms。这完成了新权重的ARM实现准入；该次没有并发检测，不据此认领完整系统5FPS或可靠身份找回。

## 输入与真实执行

沿用[执行前协议](protocol/run_v1.json)与[计划](计划与验收.md)，固定C_domain_seed26的NCNN bin SHA为`2a587d0fe293d244eb5632feb0e3665cf6091243198612b59363a6a7bb173252`。90张MultiCam已有照片为30图库＋30已登记查询＋30未知查询，另加Cows固定索引0／60／120／180／300／420／539共7张锚点。全部来自此前开发材料；未来20候选ID与保留日期的像素继续隔离。

在独立任务目录复用已经核验的Cortex-A9 VFPv3库，线程数1、FP32，未安装或导入Torch。模型读取、JPEG解码和身体预处理均实际在板上执行；97个实际输入的SHA先于首次网络调用核对。原始97份raw与归一化向量、逐图时间及9份完整张量锚点全部取回，独立核验重新读取本机原JPEG复算输入。

| 证据 | 结果 |
|---|---:|
| 正式ARM图像前向／另列预热 | 97／2 |
| 原JPEG与实际tensor hash逐图核对 | 97／97一致 |
| ARM相对Torch归一化特征最大绝对差 | {v['maximum_normalized_ARM_vs_Torch_error']:.9g} |
| ARM相对NCNN CPU归一化特征最大绝对差 | {v['maximum_normalized_ARM_vs_NCNN_error']:.9g} |
| 两个固定阈值下检索／接受决定 | 120／120一致 |
| 纯网络均值／P95 | {v['mean_network_ms']:.2f}／{v['P95_network_ms']:.2f}ms |
| JPEG解码＋预处理均值／P95 | {v['mean_JPEG_decode_preprocess_ms']:.2f}／{v['P95_JPEG_decode_preprocess_ms']:.2f}ms |

沿用归一化特征最大绝对差1e-4和`1−dot`1e-5门限，未调整权重、阈值或容差。这里的`1−dot`按既有浮点归一化向量计算，极小负值属于舍入；独立复算原值，不将其解释为负距离。[完整独立复算](results/independent_verification.json)还核验720个身份分数、120条决定、终态、全部清单与时间统计；复核本身没有增加模型前向。

## 保留能力与范围

| MultiCam工作点 | Top-1／30已登记 | 正确C | 错误W | 拒绝U | 未知FA／30 |
|---|---:|---:|---:|---:|---:|
'''
for name,label in [('original_MultiCam','旧MultiCam阈值0.844539'),('new_Cows_calibrated','Cows校准阈值0.870746')]:
 row=v['retention_outcomes'][name];report+=f"| {label} | {row['known_Top1']} | {row['C']} | {row['W']} | {row['U']} | {row['unknown_FA']} |\n"
report+=f'''
表中90张图全部是既有原来源保留检查，不能称新独立测试；未知误接受0／30也不证明总体风险为0。7张Cows锚点仅检查输入与网络实现，没有完整Cows图库／查询，不能据此计算Cows板端身份准确率。新域训练的完整开发结果仍以[配对训练报告](../identity_domain_adapt_20261030/身份域适配配对训练与开发结果.md)为准。

网络计时从已就绪的224 tensor开始，不含JPEG解码、相机、检测、跟踪、抓拍或整套任务证据写出。97个输入均先预处理，再顺序送网络，没有O8检测并发。与旧阶段约147ms的网络均值不是严格配对速度实验，不能据此宣称新训练使网络更快。

## 原始记录、失败和设备终态

输入包4,497,946字节、SHA `82bdaab1eb18c44019726727333c20f918ada723af3ba998c02d1672b30d36a1`，13成员完整核对。首次就绪行解析失败时没有上传图像或执行模型。随后控制端句柄消失，已确认的1,245,184字节前缀保留；只终止本任务接收器，观察到TTY恢复，并独立核验前缀SHA后从该位置续传。未重新建立或重跑模型实验，原接收日志与不成功的控制记录全部保留，最终整包SHA及TTY恢复通过。

正式实验PID30756已结束。首次采集进程PID30916在`sha(PL.bitfile_name)`处发生str／Path类型错误，尚未写结果归档；修复仅落入独立`collect_results_v2.py`并附[采集执行绑定](protocol/collection_execution_v2.json)。原采集脚本、错误日志、97图实验代码、输入及结果均保留。采集修复新增模型前向0。

最终原始包为{t['bytes']:,}字节、{t['members']}成员／{t['manifest_files']}清单文件，SHA为`{t['sha256']}`，已经完整下载并逐项核对。实验和采集进程均终态；[设备终态](delivery/final_board_state.json)显示默认旧encoder、O8 bitstream SHA未变，任务锁可用，板内SSH与Jupyter端口均可连接，eth0载波仍为0。当前通过COM6操作；不能据此说外部网络已恢复。

## 研究决定

新模型保留为已通过实机准入的研究候选，默认模型暂不替换。理由是新Cows开发Top-1提高，但固定拒识门限下覆盖率仍低，未证明原视频每次通行的永久身份。下一步在明确的同板负载和抓拍协议下比较新旧候选，分别报告前台计数／迟到、后台完成时间及候选／未解决状态；完整身份正确恢复仍需独立ID参考。未来20候选和保留日期在正式协议与候选冻结前保持关闭。

本轮自查已覆盖模型／输入绑定、实际99次网络调用、原始特征、两个阈值、计时范围、全部失败、归档完整性及设备终态。本阶段完成不等于整个研究、现场验证或论文贡献已经完成。
'''
target=ROOT/'新身份候选ARM实机与研究决定.md';assert not target.exists();target.write_text(report,encoding='utf-8');print(target)
