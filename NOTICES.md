# 来源与许可

本仓库用于研究成果交接。原仓库的MIT LICENSE保留不变。

包含或引用的Ultralytics、NCNN、LAP等第三方代码与资料，各自原有的许可证、版权和来源声明继续适用；本仓库LICENSE不将第三方材料重新许可。公开数据来源、作者标注边界及模型来源见各阶段报告和协议。

2026-11-09复审补充：两个O8 native include `pynq/yolo26_optimization_8/native_sources/resident_methods.inc` 与 `software_fusion.inc` 从项目编译工作区恢复，并与release manifest中的散列匹配。当前仓库未为这两个文件单独记录作者和许可证。上传、合并或再分发前，实际权利人需核实其创作/派生来源并补充版权与许可说明；匹配release manifest只证明字节一致，不证明著作权归属或再分发许可。

2026-11-10归属补充：实际跟踪器来自 Ultralytics 8.4.63 的 NumPy 移植和后续关联修改，不能仅标作“ByteTrack论文实现／MIT”。`pynq/cow_research_numpy_tracker_20261029/cow_tracker`、`maintenance/counting_r1/tracker.py` 保留 AGPL-3.0 标记；原始完整许可文本位于 `LICENSES/Ultralytics-8.4.63-AGPL-3.0.txt`，来源为该固定版本的官方仓库。论文引用 ByteTrack 方法与软件派生归属分别说明。

完整模型权重、原始张量及原始大视频未随新补充提供；历史树确有部分数据集作者标注、照片衍生面板和依赖副本，详见 `ARCHIVE_CONTENTS.md`。源码中的原模型／数据路径与校验值不表示对应大载荷可以从GitHub取得。新投稿附包排除上述两个来源未核实的 O8 include、native 二进制、权重和媒体，只提供组件需求及可核对的资产身份；附包不自称自包含的硬件复现发行版。
