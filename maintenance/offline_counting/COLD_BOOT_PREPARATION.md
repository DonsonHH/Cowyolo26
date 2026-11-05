# O8冷启动准备：现有固件、单次操作

2026-11-02。前次板端尝试在重启后没有保存计数输出。当前只读状态为PYNQ bitfile登记None、FCLK0=100MHz、fpga_manager=operating。尚不能确认当时失联的原因。

部署与实机验证范围内，先恢复已有登记O8的易失性PL运行状态。使用原有accepted/optimization_8_resident.bit及相邻hwh；不生成新的硬件设计。正常计数入口仍只附着，不自动下载Overlay；显式prepare_o8_boot.py操作单独记录。

准备要求：

- 运行前核对冻结manifest的SHA，再核对它登记的bit/hwh SHA。
- 独占现有accelerator_job.lock，无法获得锁即失败。
- 默认无下载许可标志时，未登记匹配固件则失败；本次明确调用program-registered-overlay标志，仅允许这份匹配登记hash的现有固件。
- 确认时钟后再读取PL核ABI，核版本0x80001、capability0x8000f、缓存131072字节。按O8自定义RTL的control bit2判busy，另读0x64错误寄存器；busy或error非零均失败。准备中不运行模型，不访问DMA，不修改计数参数。
- 每个阶段写入并fsync小型记录。下载或核验失败即停止，不继续模型推理，不自动重试。
- 下载调用前记录download_attempted，结果未确认记null；异常保留failed_phase，不能把部分下载后的异常写成“未下载”。

只有准备成功且系统保持可访问，才允许另起独立目录的有界模型健康检查；其后再决定是否复测原81秒。每次新增NN调用单独计数。原中断目录、原v4 10/11和缓存11次均保留；恢复固件准备本身不能作为计数验收。
