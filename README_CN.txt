参考健康人优先版本 (EXPERIMENTAL)

1) 此算法复用当前 fast_batch.py 中 build_index/select_full_fibers/run 等函数，仍与传统 TrackVis 存在体素化差异，必须验证。
2) 先等旧任务 1712443/1712445/1712442 退出，不要并行对同一患者运行旧流程。
3) 只运行一次 prepare，生成冻结的剩余患者分组；不要在已有参考块之后重新运行并改变分组。
4) 每999名患者一大组，每名参考只加载一次TRK；10个Slurm数组元素并行处理10名健康参考；每个参考按50患者保存部分结果。
5) 地图任务使用 >=2G RAM/50人数据及临时FSL中间图像；12小时期限需根据实测调整。
6) 每波健康参考(0..9, 10..19, ... 600)全部map成功后，reduce串行将该波结果累加到50人状态计数；后续才提交下一波。
7) 为防丢失计算结果，reduce不会自动删除map临时文件；确认最终数值/配额/检查点可恢复后，清理已合并参考的map目录。
8) 如果某一map失败，修复后需要单独重提对应task或整波：现有 .ok map子块会自动跳过；已提交同一波的提交记录需要人工确认原Job已退出后才调整。
9) 先创建独立的小规模验证组(例如 pilot50)，测试一个参考并验证，再使用 g000 正式任务。
10) 请先执行：python prepare.py；复制map.py/reduce.py到服务器scripts下，并确保已有fast_batch.py不被覆盖。
11) Slurm提交：bash scripts/submit_wave.sh g000 0；查看map/reduce结果；全部成功后 bash scripts/submit_wave.sh g000 1。
12) 61波全部完成后，在 ref_major_v1/final/患者ID/ 下生成三张最终图和MERGE_SUCCESS.txt。
13) 注意不是所有10个map任务结束就能无条件合并：Slurm afterok 确保全波成功才合并，失败需补算。
14) 不建议同时处理多个999人大组，先测共享存储、磁盘配额与吞吐率。
