using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace FS服装搭配专家v1._0
{
    namespace Debugger
    {
        // Token: 0x02000010 RID: 16
        public class OperationDebugger
        {
            // Token: 0x0600008A RID: 138 RVA: 0x0000E820 File Offset: 0x0000CA20
            public static void Initialize()
            {
                if (!Directory.Exists(Environment.CurrentDirectory + @"\logs"))
                {
                    Directory.CreateDirectory(Environment.CurrentDirectory + @"\logs");
                }
            }

            // Token: 0x0600008B RID: 139 RVA: 0x0000E86C File Offset: 0x0000CA6C
            public static void LogStart(string format, params object[] args)
            {
                string text = string.Format(format, args);
                OperationDebugger.Log("[START] " + text);
            }

            // Token: 0x0600008C RID: 140 RVA: 0x0000E894 File Offset: 0x0000CA94
            public static void LogComplete(string format = "", params object[] args)
            {
                string text = string.Format(format, args);
                if (string.IsNullOrEmpty(text))
                {
                    OperationDebugger.Log("[COMPLETE] Operation completed successfully");
                    return;
                }
                OperationDebugger.Log("[COMPLETE] " + text);
            }

            // Token: 0x0600008D RID: 141 RVA: 0x0000E8C8 File Offset: 0x0000CAC8
            public static void LogError(string format, params object[] args)
            {
                string text = string.Format(format, args);
                OperationDebugger.Log("[ERROR] " + text);
            }

            // Token: 0x0600008E RID: 142 RVA: 0x0000E8F0 File Offset: 0x0000CAF0
            public static void LogError(string format, Exception ex, params object[] args)
            {
                string text = string.Format(format, args);
                OperationDebugger.Log("[ERROR] " + text + " Exception: " + ex.Message);
            }

            // Token: 0x0600008F RID: 143 RVA: 0x0000E920 File Offset: 0x0000CB20
            public static void LogStep(string format, params object[] args)
            {
                string text = string.Format(format, args);
                OperationDebugger.Log("[STEP] " + text);
            }

            // Token: 0x06000090 RID: 144 RVA: 0x0000E948 File Offset: 0x0000CB48
            public static void LogVariable(string variableName, object value)
            {
                OperationDebugger.Log(string.Concat(new string[]
                {
                    "[VARIABLE] ",
                    variableName,
                    " = ",
                    ((value == null) ? "null" : value.ToString()),
                    " (",
                    ((value == null) ? "null" : value.GetType().Name),
                    ")"
                }));
            }

            // Token: 0x06000091 RID: 145 RVA: 0x0000E9AC File Offset: 0x0000CBAC
            public static void LogFileOperation(string operation, string sourcePath, string destinationPath)
            {
                OperationDebugger.Log(string.Concat(new string[]
                {
                    "[FILE OPERATION] ",
                    operation,
                    " - Source: ",
                    sourcePath,
                    " -> Destination: ",
                    destinationPath
                }));
            }

            // Token: 0x06000092 RID: 146 RVA: 0x0000EA04 File Offset: 0x0000CC04
            public static void LogUIEvent(string controlName, string eventName, string details = "")
            {
                string text = string.IsNullOrEmpty(details) ? string.Empty : " - " + details;
                OperationDebugger.Log(string.Concat(new string[]
                {
                    "[UI EVENT] ",
                    controlName,
                    ".",
                    eventName,
                    text
                }));
            }

            // Token: 0x06000093 RID: 147 RVA: 0x0000EA50 File Offset: 0x0000CC50
            public static void LogDialog(string dialogName, string message, object result)
            {
                OperationDebugger.Log(string.Concat(new string[]
                {
                    "[DIALOG] ",
                    dialogName,
                    " - Message: ",
                    message,
                    " - Result: ",
                    ((result == null) ? "null" : result.ToString())
                }));
            }

            // Token: 0x06000094 RID: 148 RVA: 0x0000EAA8 File Offset: 0x0000CCA8
            private static void Log(string message)
            {
                string text = Environment.CurrentDirectory + @"\logs\debug_" + DateTime.Now.ToString("yyyyMMdd") + ".txt";
                try
                {
                    using (StreamWriter streamWriter = new StreamWriter(text, true))
                    {
                        streamWriter.WriteLine(string.Concat(new string[]
                        {
                            DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss.fff"),
                            " ",
                            message
                        }));
                    }
                }
                catch (Exception ex)
                {
                }
            }
        }
    }
}