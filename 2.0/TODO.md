# FreeStyle v2.0 TODO

## 高优先级

### 1. 练习场暴力扫描提速
- **现状**: JS `bruteDwordScan` 耗时 ~22s（5个映射 × 全部内存区域 × 串行扫描）
- **方案 A（单遍扫描）**: 一次遍历所有区域，同时搜索所有 pattern，预估 22s → 5-6s
- **方案 B（缩小范围）**: 跳过 <64KB 小区域 + 缓存区域列表，预估 22s → 8-10s ✅ **已实施**
- **方案 C（A+B）**: 组合优化，预估 22s → 3-4s
- **约束**: 必须在 strcpy hook 内同步执行，游戏线程会阻塞等待结果
- **方案 B 实施细节**:
  - `_cachedRanges` 缓存区域列表，首次调用后不再重新枚举
  - 跳过 <64KB 小区域（ItemCode DWORD 不太可能出现在极小分配中）
  - 诊断日志：`brute_scan_cache` 报告 total/kept/skipped 区域数
  - 回退方式：删除 `_cachedRanges` 缓存和 `MIN_SCAN_SIZE` 过滤即可

### 2. 退出练习场回角色选择界面光头
- **根因**: `bruteDwordScan` 无差别替换所有 DWORD（含装备槽数据），退出时不恢复
- **尝试过的方案**:
  - `native_restore_shop` 恢复非属性表条目 → 恢复了房间装备数据导致光头
  - Python `native_dword_scan`（有 flag 检查）→ 练习场 flag 读不到，替换 0 个
  - Python `native_brute_scan`（无 flag 检查）→ 异步执行，游戏线程不等，替换无效
- **待研究**: 如何在退出练习场时精确恢复装备槽数据而不影响属性表

## 中优先级

### 3. 587/588 未知前缀道具
- 刷新穿搭时出现 `587`, `588` 两个 ItemCode，不在 itemshop.json 中
- 可能是游戏新增道具或内部特效 ID
- 需要确认来源并更新 itemshop 数据

### 4. 391 前缀道具
- `3910041` 被跳过，前缀 391 不在任何 slot 的 prefix 映射中
- 需要确认这是什么类型的道具

## 低优先级

### 5. 动态/静态发型区分
- ItemCode 编号无规律可区分动态/静态发型
- 动态/静态由服务器下发的 `CharacterMotion.bml` 决定
- 唯一可靠方法: 运行时扫描 vtable（DDynamicActor = 0x0284A9EC）

## 已完成

- [x] 刷新穿搭重复饰品修复（seenCodes 去重 + 批次边界检测）
- [x] 刷新穿搭读到上一个人物数据修复（Python 侧清除旧数据）
- [x] 装备位匹配算法重写（两阶段匹配：固定 slot + 灵活 slot 依次展示）
- [x] 514 翅膀/515 尾巴显示修复
- [x] 兜底 slot（prefix="*"）接收未映射道具
- [x] 名称回退（Python 返回未知时 C# 用本地 _itemDict 补充）
- [x] Hook 实时监控（hook_log_buffer + 2 秒轮询）
- [x] TCP 通信锁（SemaphoreSlim）
- [x] 日志复制按钮
- [x] sprintf 未命中日志过滤（只写 engine.log 不推 UI）
- [x] 调试日志覆盖（连接/刷新/替换/匹配各环节）
