# 冻结 O7 运行参考

这里包含原O7正常运行所需13个文件及原SHA清单、bus图和3份原生源，逐字节等同保留的O7。不是新的优化实现。
恢复旧core0x60004需要覆盖该行动的明确许可。加载匹配旧bit/hwh并完成DMA首笔初始化后，可在此目录运行原run_detector.py或run_board.py；原程序保持download=False和共享StageD独占锁。
其原verify_release.py默认验证13运行文件；--full指原O7全量重建发布包，本最小参考不声称带齐原O7全部训练/PC评估复现依赖。O8顶层verify_release.py --full会验证本参考的全部已包含文件。
本参考不用于O8默认运行，不把O8的数学或性能冒作原O7。原来的全部O7工作目录和ZIP仍被保留。
