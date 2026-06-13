using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Net.Sockets;
using System.Text;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;

namespace FS服装搭配专家.Core.Services
{
    public class FridaBridge : IDisposable
    {
        private Process? _pythonProcess;
        private TcpClient? _client;
        private NetworkStream? _stream;
        private readonly string _host = "127.0.0.1";
        private readonly int _port = 18731;
        private readonly string _enginePath;
        private readonly SemaphoreSlim _sendLock = new(1, 1); // TCP 通信锁

        public bool IsConnected => _client?.Connected == true;
        public event Action<string>? OnLog;
        public event Action<Dictionary<string, object>>? OnSlotsRead;

        public FridaBridge()
        {
            var dir = AppDomain.CurrentDomain.BaseDirectory;
            _enginePath = Path.Combine(dir, "engine", "server.py");
        }

        public async Task StartEngineAsync()
        {
            // 先杀掉所有监听同一端口的旧 Python 进程
            KillStalePythonProcesses();

            var pythonExe = FindPython();
            await EnsureRequirementsAsync(pythonExe);

            var psi = new ProcessStartInfo
            {
                FileName = pythonExe,
                Arguments = $"\"{_enginePath}\"",
                UseShellExecute = false,
                CreateNoWindow = true,
                WorkingDirectory = Path.GetDirectoryName(_enginePath)!
            };

            _pythonProcess = Process.Start(psi);
            if (_pythonProcess == null)
                throw new Exception("Failed to start Python engine");

            Log("Python engine starting...");
        }

        /// <summary>从 PATH 查找 python.exe</summary>
        private static string FindPython()
        {
            string[] candidates = ["python", "python3", "python3.12", "python3.11", "python3.10"];
            foreach (var name in candidates)
            {
                try
                {
                    var psi = new ProcessStartInfo
                    {
                        FileName = name,
                        Arguments = "--version",
                        UseShellExecute = false,
                        CreateNoWindow = true,
                        RedirectStandardOutput = true,
                        RedirectStandardError = true
                    };
                    using var p = Process.Start(psi);
                    if (p == null) continue;
                    p.WaitForExit(3000);
                    if (p.ExitCode == 0) return name;
                }
                catch { }
            }
            throw new Exception("未找到 Python！请安装 Python 3.10+ 并加入 PATH。");
        }

        /// <summary>首次运行自动 pip install -r requirements.txt</summary>
        private async Task EnsureRequirementsAsync(string pythonExe)
        {
            var engineDir = Path.GetDirectoryName(_enginePath)!;
            var marker = Path.Combine(engineDir, ".deps_installed");
            var reqFile = Path.Combine(engineDir, "requirements.txt");

            if (File.Exists(marker) || !File.Exists(reqFile))
                return;

            Log("首次运行，自动安装 Python 依赖...");
            var psi = new ProcessStartInfo
            {
                FileName = pythonExe,
                Arguments = $"-m pip install -r \"{reqFile}\"",
                UseShellExecute = false,
                CreateNoWindow = true,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                WorkingDirectory = engineDir
            };
            using var p = Process.Start(psi);
            if (p == null) throw new Exception("pip 启动失败");

            var output = await p.StandardOutput.ReadToEndAsync();
            var err = await p.StandardError.ReadToEndAsync();
            await p.WaitForExitAsync();

            if (p.ExitCode != 0)
                throw new Exception($"依赖安装失败:\n{err}\n请手动执行: {pythonExe} -m pip install -r requirements.txt");

            await File.WriteAllTextAsync(marker, DateTime.Now.ToString("O"));
            Log("Python 依赖安装完成");
        }

        private void KillStalePythonProcesses()
        {
            try
            {
                foreach (var proc in Process.GetProcessesByName("python"))
                {
                    try
                    {
                        if (proc.Id == Process.GetCurrentProcess().Id) continue;
                        var cmdLine = proc.MainModule?.FileName ?? "";
                        // 杀掉所有 python 进程（我们的 engine 是唯一的 python 进程）
                        if (cmdLine.Contains("Python", StringComparison.OrdinalIgnoreCase))
                        {
                            proc.Kill();
                            Log($"Killed stale python PID {proc.Id}");
                        }
                    }
                    catch { }
                }
            }
            catch { }
        }

        public async Task ConnectAsync()
        {
            _client = new TcpClient();
            await _client.ConnectAsync(_host, _port);
            _stream = _client.GetStream();
            Log("Connected to engine");
        }

        public async Task EnsureEngineAsync()
        {
            if (_pythonProcess == null || _pythonProcess.HasExited)
                await StartEngineAsync();

            // 轮询端口就绪（最多10秒）
            for (int i = 0; i < 100; i++)
            {
                // 检查 Python 进程是否还活着
                if (_pythonProcess != null && _pythonProcess.HasExited)
                    throw new Exception($"Python 引擎异常退出 (exit code: {_pythonProcess.ExitCode})，请检查 frida/psutil 是否已安装");

                try
                {
                    using var test = new TcpClient();
                    await test.ConnectAsync(_host, _port);
                    Log("Engine port ready");
                    break;
                }
                catch { await Task.Delay(100); }
            }

            if (!IsConnected)
                await ConnectAsync();
        }

        public async Task<JsonElement> SendCommandAsync(Dictionary<string, object> cmd)
        {
            await _sendLock.WaitAsync();
            try
            {
                // 尝试发送，失败则重连一次
                for (int attempt = 0; attempt < 2; attempt++)
                {
                    try
                    {
                        if (_stream == null) throw new Exception("Not connected");

                        var json = JsonSerializer.Serialize(cmd);
                        var bytes = Encoding.UTF8.GetBytes(json + "\n");
                        await _stream.WriteAsync(bytes);

                        // 读响应（直到换行）
                        var buf = new byte[4096];
                        var ms = new MemoryStream();
                        while (true)
                        {
                            int n = await _stream.ReadAsync(buf, 0, buf.Length);
                            if (n == 0) throw new Exception("Connection lost");
                            ms.Write(buf, 0, n);
                            var str = Encoding.UTF8.GetString(ms.ToArray());
                            if (str.Contains('\n'))
                                break;
                        }

                        var responseStr = Encoding.UTF8.GetString(ms.ToArray()).Trim();
                        return JsonSerializer.Deserialize<JsonElement>(responseStr);
                    }
                    catch (Exception ex)
                    {
                        if (attempt == 0)
                        {
                            Log($"连接断开，尝试重连: {ex.Message}");
                            try { await ConnectAsync(); } catch { }
                        }
                        else
                        {
                            throw new Exception($"通信失败: {ex.Message}");
                        }
                    }
                }
                throw new Exception("通信失败");
            }
            finally
            {
                _sendLock.Release();
            }
        }

        public async Task<int> ConnectGameAsync()
        {
            var result = await SendCommandAsync(new Dictionary<string, object> { { "cmd", "CONNECT" } });
            if (result.GetProperty("status").GetString() == "ok")
            {
                var pid = result.GetProperty("pid").GetInt32();
                Log($"Attached to FreeStyle.exe PID {pid}");
                return pid;
            }
            throw new Exception(result.GetProperty("error").GetString());
        }

        public async Task<int> LaunchGameAsync(string gameDir)
        {
            var result = await SendCommandAsync(new Dictionary<string, object>
            {
                { "cmd", "LAUNCH_GAME" },
                { "game_dir", gameDir }
            });
            if (result.GetProperty("status").GetString() == "ok")
            {
                var pid = result.GetProperty("pid").GetInt32();
                var msg = result.TryGetProperty("msg", out var m) ? m.GetString() : "";
                Log($"Launched FreeStyle.exe PID {pid}: {msg}");
                return pid;
            }
            throw new Exception(result.GetProperty("error").GetString());
        }

        public async Task<(Dictionary<string, SlotData> slots, string hint)> ReadCurrentSlotsAsync()
        {
            var result = await SendCommandAsync(new Dictionary<string, object> { { "cmd", "READ_CURRENT" } });
            var slots = new Dictionary<string, SlotData>();
            var hint = "";

            if (result.TryGetProperty("hint", out var hintEl))
                hint = hintEl.GetString() ?? "";

            if (result.TryGetProperty("slots", out var slotsEl))
            {
                foreach (var prop in slotsEl.EnumerateObject())
                {
                    var slot = new SlotData
                    {
                        Code = prop.Value.GetProperty("code").GetInt32(),
                        Name = prop.Value.GetProperty("name").GetString() ?? "",
                        Pak = prop.Value.GetProperty("pak").GetString() ?? ""
                    };
                    slots[prop.Name] = slot;
                }
            }
            return (slots, hint);
        }

        public async Task RecollectAsync()
        {
            var result = await SendCommandAsync(new Dictionary<string, object> { { "cmd", "RECOLLECT" } });
            if (result.GetProperty("status").GetString() != "ok")
                throw new Exception(result.GetProperty("error").GetString());
            Log("Collect state reset");
        }

        public async Task ReplaceAsync(Dictionary<string, int> map, Dictionary<string, int>? effectMap = null, bool enableEffect = true)
        {
            var cmd = new Dictionary<string, object>
            {
                { "cmd", "REPLACE" },
                { "map", map },
                { "enable_effect", enableEffect }
            };
            if (effectMap != null && effectMap.Count > 0)
                cmd["effect_map"] = effectMap;

            var result = await SendCommandAsync(cmd);
            if (result.GetProperty("status").GetString() != "ok")
                throw new Exception(result.GetProperty("error").GetString());
            Log($"Replace set: {map.Count} slots, {effectMap?.Count ?? 0} effects");
        }

        public async Task RestoreAsync()
        {
            var result = await SendCommandAsync(new Dictionary<string, object> { { "cmd", "RESTORE" } });
            Log("Restored");
        }

        public async Task<string?> ReadCharNameAsync()
        {
            var result = await SendCommandAsync(new Dictionary<string, object> { { "cmd", "READ_CHARNAME" } });
            if (result.GetProperty("status").GetString() == "ok")
            {
                var name = result.GetProperty("name").GetString() ?? "";
                Log($"CharName: {name}");
                return string.IsNullOrEmpty(name) ? null : name;
            }
            return null;
        }

        public class CharInfo
        {
            public string PlayerName { get; set; } = "";
            public string CharName { get; set; } = "";
            public string ComboKey { get; set; } = "";
        }

        public async Task<CharInfo?> ReadCharInfoAsync()
        {
            var result = await SendCommandAsync(new Dictionary<string, object> { { "cmd", "READ_CHARINFO" } });
            if (result.GetProperty("status").GetString() == "ok")
            {
                var info = new CharInfo
                {
                    PlayerName = result.TryGetProperty("player_name", out var pn) ? pn.GetString() ?? "" : "",
                    CharName = result.TryGetProperty("char_name", out var cn) ? cn.GetString() ?? "" : "",
                    ComboKey = result.TryGetProperty("combo_key", out var ck) ? ck.GetString() ?? "" : "",
                };
                Log($"CharInfo: player={info.PlayerName}, char={info.CharName}, combo={info.ComboKey}");
                return string.IsNullOrEmpty(info.ComboKey) ? null : info;
            }
            return null;
        }

        public async Task<List<SearchResult>> SearchAsync(string keyword)
        {
            var result = await SendCommandAsync(new Dictionary<string, object>
            {
                { "cmd", "SEARCH" },
                { "keyword", keyword }
            });

            var list = new List<SearchResult>();
            if (result.TryGetProperty("results", out var arr))
            {
                foreach (var item in arr.EnumerateArray())
                {
                    list.Add(new SearchResult
                    {
                        Code = item.GetProperty("code").GetString() ?? "",
                        Name = item.GetProperty("name").GetString() ?? "",
                        Pak = item.GetProperty("pak").GetString() ?? ""
                    });
                }
            }
            return list;
        }

        public async Task<List<string>> PollHookLogAsync(int since = 0)
        {
            try
            {
                var result = await SendCommandAsync(new Dictionary<string, object>
                {
                    { "cmd", "HOOK_LOG" },
                    { "since", since }
                });
                var lines = new List<string>();
                if (result.TryGetProperty("lines", out var arr))
                {
                    foreach (var item in arr.EnumerateArray())
                        lines.Add(item.GetString() ?? "");
                }
                return lines;
            }
            catch
            {
                return new List<string>();
            }
        }

        private void Log(string msg) => OnLog?.Invoke(msg);

        public void Dispose()
        {
            _stream?.Close();
            _client?.Close();
            // 杀掉所有 Python 进程（包括自己启动的和残留的）
            KillStalePythonProcesses();
            if (_pythonProcess != null && !_pythonProcess.HasExited)
            {
                try { _pythonProcess.Kill(); } catch { }
            }
        }
    }

    public class SlotData
    {
        public int Code { get; set; }
        public string Name { get; set; } = "";
        public string Pak { get; set; } = "";
    }

    public class SearchResult
    {
        public string Code { get; set; } = "";
        public string Name { get; set; } = "";
        public string Pak { get; set; } = "";
        public string Display => $"{Name} ({Code}) pak{Pak}";
    }
}
