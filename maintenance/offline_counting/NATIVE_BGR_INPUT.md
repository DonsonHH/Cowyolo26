# 原生BGR输入候选

现有native_graph.run_image→o7_run_bgr已提供BGR入口。原生C++用256项查表完成uint8→RGB归一化及首量化；表中归一化为float(j)/255.f，沿用登记输入scale/zero point。没有更改编译库、模型图、计划或固件。

新 `detector_input=native_bgr` 接受BGR uint8 letterbox画布；Python端省去每帧NCHW/FP32转换，再由既有原生入口完成。默认rgb_float32保持原路径。legacy画布与旧输入一致；显式resize_first_v1画布保留既定坐标，但有已登记的少量像素差异。两种组合全局和局部输入选择相同，错误dtype/shape/stride在进入原生函数前拒绝。

先在同一旧开发输入上比较两个入口的完整raw输出和各段耗时；只有实机比较通过，才进行新的实时计数评估。单帧/固定向量一致不能代替完整计数验收。此前resize-first候选在320上更慢的实测记录保留，不升级为成功优化。
