# 源片漏计优化：自审与当前状态

2026年10月28日。已完成代码、协议、原始输出、独立算术复算、媒体和浏览器核查。研究整体继续进行；本轮没有新增训练或板上执行。

## 已核查的证据

| 项目 | 实际证据与边界 |
| --- | --- |
| 用户要求 | [反馈记录](<C:/Users/Donson/Documents/ChatGPT/奶牛/counting_recovery_20261028/user_feedback.json>)确认8912–10873帧橙框内完整通行，粗略十几头，板卡稍后提供；未提供确切总数或独立事件JSON |
| 冻结输入 | 协议v2绑定原片及三seed末轮checkpoint SHA，训练更新0；本机重算源片260096040字节的SHA与协议一致 |
| 旧方案回归 | 本轮seed26的8条事件、范围内轨迹和从帧0起的历史轨迹均精确重现旧版；seed27、28沿用此前冻结输出6／8，未宣称本轮全数重跑旧组 |
| 坐标与计数 | [独立复算](<C:/Users/Donson/Documents/ChatGPT/奶牛/counting_recovery_20261028/delivery/results/independent_verification.json>)以另一份状态机重放全部10条件，并用四角方法检查36669行框坐标；60张快照完整解码。检查覆盖范围含跟踪前历史，不只看最终计数数字 |
| 原生坐标还原 | 裁剪偏移、90°逆变换及float32舍入逐行核对；恢复回调先于ByteTrack，跟踪原图形状保持1440×2560。没有移动ROI以增加计数 |
| 试验选择过程 | 最初按ROI原始框覆盖选择低阈值裁剪320，三seed为10／7／10；整幅图640的另两个seed属于后续确认。报告保留全部10组，不倒写为预设最优选择 |
| 时序规则 | 3样本@5Hz与11样本@25Hz的首末间隔均0.4秒。25Hz／3样本得到12次仅作另一时序规则诊断；主结果10次，未据此把预测改到十几头 |
| 跟踪器时钟限制 | 已取得实际安装版本的三个源码／参数文件，确认`track_buffer:30`按更新次数计时。5与25Hz的标称丢失保留预算约6／1.2秒，没有对齐；25Hz组不能用于单独否定采样率效果，同5Hz的320／640配对不受这一差别影响 |
| 交付 | 压缩包57618028字节，SHA为`ce4e4872a39c660eef2d7723f37709a6760c95f4ef0f5e89857e6e4f43b1af29`；191个清单文件、192个归档成员逐项校验。[本机结果](<C:/Users/Donson/Documents/ChatGPT/奶牛/counting_recovery_20261028/results/local_verification.json>) |
| 预测差异 | [一对一时间比较](<C:/Users/Donson/Documents/ChatGPT/奶牛/counting_recovery_20261028/results/old_new_event_comparison.json>)中，旧8／6／8事件均有同方向对应，最大时间差0.6秒；新组11／10／11。这是预测与预测比较，未当作TP／FP／FN |
| 媒体 | 四条件各MP4及WebM，共8个新媒体，均1280×720、25fps、1962帧、78.48秒，完整严格解码；三个旧seed的6媒体复用前核对SHA。[媒体证据](<C:/Users/Donson/Documents/ChatGPT/奶牛/counting_recovery_20261028/results/media_verification.json>) |
| 浏览器 | [14项核查](<C:/Users/Donson/Documents/ChatGPT/奶牛/counting_recovery_20261028/results/browser_verification.json>)通过：四条件实际播放推进、同seed两路对应、首末与指定源帧跳转、编辑暂停保留值、11条事件列表及10组结果表。独立标注草稿没有打开或修改。[截图](<C:/Users/Donson/Documents/ChatGPT/奶牛/counting_recovery_20261028/results/browser_preview.png>) |

## 失败与中断记录

1. 作业130214在跟踪器初始化失败：将说明性字符串`samebuiltinbytetrack.yaml`错误地用作真实文件名。协议v2仅修正为安装版本实际存在的`bytetrack.yaml`并保存前版SHA。失败日志与旧协议保留；后续130215完成六pilot及覆盖规则扩展，130217完成两个整幅图640确认。
2. 首次媒体压缩130222因所选旧ffmpeg缺少所需编码选项失败。改用已存在、确认支持libx264的`pid310_gpu`运行时，不修改环境；CRLF版Slurm脚本首次提交被拒绝、没有生成作业，原脚本保留。转为LF后130236完成四视频压缩及完整解码，模型预测未改变。
3. 较大的原始交付包首次传输只取得155860992字节，原337780353字节包仍在服务器。部分文件保留在本机`results/delivery.tar.gz`，未解压、未用于验证；实际交付使用另名`compact_delivery.tar.gz`，完整大小及SHA已通过。PyPI媒体运行时下载尝试没有用于最终压缩，现有环境没有因此改装。
4. 本机旧版抽帧命令使用不支持的`-vsync`选项失败；改用`-fps_mode vfr`后取得预先固定18帧并保存原失败日志。浏览器一次`body`快捷键定位超时，随后使用完整页面截图；这不是视频播放失败，14项产品行为核查仍按实际返回值记录。

最终[Slurm终态记录](<C:/Users/Donson/Documents/ChatGPT/奶牛/counting_recovery_20261028/results/final_remote_status.txt>)确认130215、130217、130220、130221、130236完成，130214与130222失败；该次查询没有运行中的本账户作业。不能把传输观察超时当成推理失败或重新训练的理由。

## 研究判断复审

| 等级 | 结论与后续动作 |
| --- | --- |
| BLOCKER（最终计数评价） | 原片独立逐事件参考仍未收到。用户粗略十几头不能作为分母；不能认领当前源片准确率提高或已数全。继续检查拥挤、并排和未完成跨区轨迹 |
| BLOCKER（硬件主张） | PYNQ-Z2 SSH、镜像与工具版本稍后提供；尚无Arm／PL实际执行或联合延迟／功率。640服务器结果不等于可部署实时结果，软件工作继续 |
| IMPORTANT | 原片已被反复用于开发；下一轮必须补新的会话及真实双向样本。三个seed是相同片段上三个训练结果，不是三个独立牧场 |
| IMPORTANT | ROI覆盖增加不保证计数改善，裁剪640的1事件／38ID完整保留；不凭粗略总数合并ID或放宽通行条件。Toros原不利结果也没有被本轮改写 |
| IMPORTANT | 下一项无须新增推理的诊断是缓存框跟踪重放与丢失保留预算对齐；先精确复现原轨迹，再单独改该时钟因素。不能把本轮25Hz结果写成纯采样率的因果消融 |
| POLISH | 新页面提供同seed同步播放、源帧跳转、全部开发条件和事件列表；视频只含用户指定范围。页面已实际打开并保留为交付页 |

已完成的工作详见[报告与下一步](<C:/Users/Donson/Documents/ChatGPT/奶牛/counting_recovery_20261028/源片漏计优化与下一步.md>)。本自审证明本轮开发对照和交付的一致性，未宣称论文主机制、跨场性能或整个研究已完成。
