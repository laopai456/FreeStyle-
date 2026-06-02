# 常见问题FAQ

## 编译相关

### Q: 编译时提示找不到图标文件
**A**: 复制 `FS服装搭配专家v5.3.6.ico` 到项目根目录，或注释掉项目文件中的图标引用。

### Q: 编译时出现 "应输入 ;" 等语法错误
**A**: 检查修改代码时是否遗漏了分号或大括号。

### Q: 编译成功但运行时弹出 "resources文件被杀毒软件删掉"
**A**: 将 `pack\resources.exe` 复制到编译输出目录（`bin\Debug\` 或 `bin\Release\`）。

## 运行相关

### Q: 调试日志文件在哪里？
**A**: `[程序运行目录]/logs/operation_debug.log`

### Q: 日志文件乱码怎么办？
**A**: 使用 UTF-8 编码的文本编辑器打开，或使用 VS Code。

### Q: 如何禁用调试监听器？
**A**: 注释掉 `FrmMain.cs` 构造函数中的 `Elena.Debugger.OperationDebugger.Initialize();`

### Q: 启动程序后主界面显示空白，只弹"Error"错误？
**A**:
1. 检查是否有卡住的 `resources.exe` 进程（`tasklist | findstr resources`）
2. 如有，使用 `taskkill /F /IM resources.exe` 杀掉所有卡住的进程
3. 删除 `cookies\item_text.pak`（如果被占用无法删除，说明resources进程未正常退出）
4. 重新启动程序

**原因分析**：
- `pack\resources` 工具执行解包/打包操作后未正常退出
- 卡住的进程占用了 item_text.pak 文件，导致无法重新解包
- `GetNewItem()` 方法无法读取 `item_text_pak\itemshop.txt`，抛出异常

**预防措施**：
- 批量变更后如遇到问题，先检查并清理卡住的 resources 进程
- 避免频繁重复执行批量变更操作

## 功能相关

### Q: 变更后进入游戏没效果？
**A**:
1. 确认游戏已完全关闭
2. 检查 `pack\resources.exe` 是否存在
3. 查看调试日志确认变更是否成功

### Q: 如何还原所有道具？
**A**: 点击主界面的"还原全部"按钮，会运行 `T2REPAIR.exe` 修复游戏文件。

### Q: 它服道具怎么使用？
**A**: 勾选"它服"复选框，然后选择它服目录的道具。

## 代码相关

### Q: 如何修改游戏目录？
**A**: 程序从配置文件读取，或通过界面设置游戏安装路径。

### Q: 如何批量变更道具？
**A**: 当前版本只支持单对单变更，批量变更需要自行开发。

### Q: pak文件如何解包和打包？
**A**:
- 解包: `pack\resources "pak文件路径" -all`
- 打包: `pack\resources -file2pak "目录路径" "pak文件路径"`

## 其他

### Q: 文件中的 `<>4__this` 是什么？
**A**: 反编译工具生成的内部变量名，需要手动修改为合法的变量名（如 `__this`）。

### Q: `Environment.CurrentDirectory` 和 `Application.StartupPath` 有什么区别？
**A**:
- `Environment.CurrentDirectory`: 当前工作目录（运行命令的目录）
- `Application.StartupPath`: EXE文件所在目录（推荐使用）

### Q: 如何调试 BackgroundWorker 异步操作？
**A**: 使用调试监听器的日志功能，或在异步方法中添加断点调试。
