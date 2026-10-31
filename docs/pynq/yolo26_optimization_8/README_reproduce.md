# Optimization 8：复现说明

## 范围与文件

保持O7官方YOLO26n权重、拓扑、80类和既有量化数学；输入192/224/256。新增精确残差遍历融合和25对真实片上驻留，使用同一128MAC、100MHz阵列。主报告与审查在项目根 `reports/optimization_8/optimization_8_report.md`、`review_report.md`。

- `program_r*/`：冻结静态图、全部权重/常量；`plans/r*_all/`：默认25对、69次DMA计划。`adjacent`保留17对实验。
- `native_sources/`：完整C++/inc、ARM库、PC库及PC的libwinpthread依赖。
- `hardware/accepted/`：匹配的bit/hwh、SHA清单；XSA原样保存在`exports/`。core0x80001，128KiB缓存。
- `hardware/restore_baseline/`：旧0x60004 bit/hwh；`hardware/base/`保留原构建资料。
- `reference_o7/`：逐字节冻结的原O7正常运行13文件、原SHA清单、bus图及3份原生源，用于独立回退/A对照。其原`verify_release.py`默认可验证13文件；原`--full`指旧O7全部重建发布包，本最小参考不冒称包含这些额外旧依赖。
- `r*_fullptq/`、`r*_intdw/`、`tools/`、`compiler/`、`compiler_sources/`、`pc_intdw/`：模型和独立编译/整数Golden。
- `release_manifest.json`：运行及重建文件逐项SHA。源码、失败记录、原始报告仍完整保留。

板端沿用既有PYNQ3.1.1、ARMv7、Linux6.6.10、Python3.10、OpenCV4.5.4、XRT/GCC。PC依赖见`requirements_pc.txt`。COCO数据是明确的外部依赖。共享锁为 `/home/xilinx/jupyter_notebooks/yolo26_stage_d/reports/accelerator_job.lock`。

## 板端正常运行

前提：已在覆盖该动作的明确许可下加载匹配O8固件。正常入口只附着`download=False`，不自动编程，且验证真实bit/hwh SHA、IP/core/capability和100MHz。

```bash
cd /home/xilinx/jupyter_notebooks/yolo26_optimization_8
sudo env XILINX_XRT=/usr OMP_NUM_THREADS=2 PYTHONDONTWRITEBYTECODE=1 \
 /usr/local/share/pynq-venv/bin/python -B run_detector.py --profile flagship224

sudo env XILINX_XRT=/usr OMP_NUM_THREADS=2 PYTHONDONTWRITEBYTECODE=1 \
 /usr/local/share/pynq-venv/bin/python -B run_detector.py \
 --profile flagship224 --camera --frames 100
```

还可选择`fast192`或`quality256`，用`--image /absolute/path.jpg`指定图片。默认显示阈值0.25。每次在`runs/demo_<编号>/`保存原图、带类别/置信度的框、raw/boxes/JSON。若匹配固件刚加载、DMA尚未完成首笔传输，初始化阶段会执行有界8字自检，不重新编程。

## 正式计时和对照

```bash
sudo env XILINX_XRT=/usr OMP_NUM_THREADS=2 PYTHONDONTWRITEBYTECODE=1 \
 /usr/local/share/pynq-venv/bin/python -B run_board.py \
 --size 224 --options 4 --plan plans/r224_all/resident_plan.bin \
 --firmware-manifest hardware/accepted/firmware_manifest.json \
 --fixed 100 --warmups 3 --camera 100 --output reports/fresh_test
```

输出目录必须不存在。1000帧用`--fixed 1000 --camera 0`。完整E2E为已解码BGR→预处理/量化→完整网络/TopK→阈值/坐标解码；初始化、冷帧、采集、画框和保存另计。PL busy/compute包含于DMA等待，depthwise包含于ARM residual，不重复相加。

A=冻结O7+旧固件；B=O8软件+旧固件；C=同一O8软件+新固件逐层DDR；D=同一O8软件+新固件驻留。`run_board.py`省略plan为兼容实验，不是默认最快D。主验收A/D与C/D均三轮独立100帧、冷帧及3预热另记，所有慢帧保留。A/D脚本会切换易失性固件，执行前必须有相应许可；发布版优先使用reference_o7和随包restore_baseline，原正式A运行的是原保留O7目录，两者源码/库/图SHA相同。

长测试使用板端独立进程和文件stdout，参考`prepare_validation_job.py`与板端`jobs/validation_*/source_manifest.json`。本轮SSH断管的140图已从断点续跑，原失败文件没有覆盖。

## 数值与恢复检查

`tests/board_vectors/`包含独立整数Golden产生的实际三档卷积对、容量/halo/Co80/模式/非法元数据向量；`board_resident_vectors.py`重放实际PL。`--debug-mirror --dump-boundaries`仅用于非正式计时：中间值来自真实S2MM镜像。软件融合跳过的私有FP32中间值在调试导出时按原顺序重建，不假称性能帧仍保存它们。

`representative_D.py`检查同一100张不同真实图、三档、每图411逻辑输出和最终raw/boxes。`verify_actual_integer.py`再以独立整数Golden核对实际PL/ARM卷积边界。恢复脚本只做有界AXI-Lite soft_reset和AXI DMA reset，须独占，停止DMA后才释放BO；不重新编程。

## PC正式COCO5000

新建独立venv并安装`requirements_pc.txt`，不改板端系统Python。外部依赖为官方val2017全部5000图和annotations。`dataset_split.json`保留512张train校准池；实际O7/O8数学配方固定取前128张，与val严格不交叉。O8没有重新校准。

```powershell
python -B -X utf8 verify_release.py --full
python -B -X utf8 evaluate_release.py --size 224 --limit 5000 `
 --library native_queue_pc.dll --options 4 --plan plans/r224_all/resident_plan.bin `
 --images D:/datasets/coco/val2017 `
 --annotations D:/datasets/coco/annotations/instances_val2017.json `
 --output evaluation/fresh224
```

192/256修改size和plan。期望AP50–95分别为18.253461788328632%、21.28188815782671%、24.09114997833079%。O8三份5000均实际重跑，均与O7相同。PC将驻留计划展开为原逻辑卷积，使用独立整数Golden及共用原生CPU数学；准确率转移另由板端等价性支持。PC5000不是板端5000，PC耗时不冒充板端E2E。

## 重建原生库、图与计划

```powershell
python -B recompile_native.py --output builds/fresh_pc `
 --compiler D:/AMDDesignTools/2026.1/Vivado/tps/mingw/10.0.0/win64.o/nt/bin/g++.exe
python -B -X utf8 recompile_release.py --size 224 --output builds/fresh224
```

ARM：`python -B recompile_native.py --output revisions/fresh_native`，只写新目录，不替换当前库。参数为O3/C++17/shared/PIC/cortex-a9/neon/hard-float/OpenMP/ffp-contract=off/ldl；没有fast-math。Windows静态gcc/stdC++/gomp，gomp须位于目标文件后，仍需随包libwinpthread。两次依赖链接失败与修正后的9图/411边界复核证据保留。

O8实际重跑了三档冻结ONNX→整数DW→graph.bin→resident plan，全部逐字节一致。`regenerate_release.py`保留O7官方PT→固定128train MinMax PTQ的较长配方，需要外部train2017；本轮未重新校准/训练，不把继承配方写成O8新实验。

## 硬件与回退

固定Vivado2026.1和xc7z020clg400-1。原board preset保留，只沿用四个负DDR UI DQS delay归零覆盖，不屏蔽告警。完整RTL209156字、扩展42340字、requant3072字节自检通过；实际板端另有384组/3072字节INT32极值及饱和的驻留验证。

`initialize.py`、`create_resident_rtl.py`及建设期`prepare_*_runtime`等是归档的一次性生成器；接受版已加封存保护，拒绝覆盖最终代码。不要用它们重新初始化发布树；下述正常仿真/原生/图/硬件构建入口仍可在新输出目录运行。原未加保护版本作为历史证据保留在reports。

从项目根执行`powershell -NoProfile -ExecutionPolicy Bypass -File scripts/optimization_8/run_sim.ps1`；默认full含128KiB边界，模板已闭合在O8 tests。然后用新simulation路径运行`run_hardware.ps1 -Simulation <路径>`。工具和许可证位置在wrapper中显式记录；换主机需相应安装和有效许可证，许可证不入包。

普通route曾有-.424ns，接受版复用同一综合DCP，在独立项目运行`run_physical_retry.ps1 -Parent <新构建编号>`，Performance_Explore/AggressiveExplore/route Explore。未放宽100MHz、添加任意时序例外或忽略DRC。新环境不承诺布局/bit逐位相同，必须重新通过完整门禁。构建脚本不自动下载。接受版源快照、匹配bit/hwh/xsa和原始报告齐全；workspace保留所有完整Vivado项目。

PYNQ3.1.1的is_xsa会因bit旁存在同stem XSA误选解析器，所以XSA保存在`accepted/exports/`。无需改PYNQ安装。获准回退时使用`hardware/restore_baseline/optimization_5_exact.bit`，随后可用原O7入口。未来任务编程仍需新的明确许可。

## 测量边界

HP0读计数是每个64位R握手8字节，写计数按WSTRB；它不包含ARM全部DDR访问，也不是DRAM芯片物理事务。相机帧龄/驱动丢帧未测，稳定性不代表场景准确率；不宣称30FPS、每帧硬实时、实测功耗或Fmax。验收后停止，不自动开始O9。
