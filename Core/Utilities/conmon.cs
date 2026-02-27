using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Linq;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading.Tasks;

namespace FS服装搭配专家v1._0
{
    // Token: 0x02000011 RID: 17
    public class conmon
    {
        // Token: 0x06000095 RID: 149 RVA: 0x0000EAC0 File Offset: 0x0000CCC0
        public static string GetMD5HashFromFile(string fileName)
        {
            try
            {
                FileStream fileStream = new FileStream(fileName, FileMode.Open);
                System.Security.Cryptography.MD5 mD = System.Security.Cryptography.MD5.Create();
                byte[] array = mD.ComputeHash(fileStream);
                fileStream.Close();
                StringBuilder stringBuilder = new StringBuilder();
                for (int i = 0; i < array.Length; i++)
                {
                    stringBuilder.Append(array[i].ToString("x2"));
                }
                return stringBuilder.ToString();
            }
            catch (Exception ex)
            {
                return "";
            }
        }

        // Token: 0x06000096 RID: 150 RVA: 0x0000EB74 File Offset: 0x0000CD74
        public static bool CheckInstallDirectory(string path)
        {
            bool result = false;
            if (Directory.Exists(path))
            {
                string text = path + "\\item_text.pak";
                if (File.Exists(text))
                {
                    result = true;
                }
            }
            return result;
        }

        // Token: 0x06000097 RID: 151 RVA: 0x0000EBB4 File Offset: 0x0000CDB4
        public static string DonePakUrl(string installPath)
        {
            string result = "";
            if (Directory.Exists(installPath))
            {
                result = installPath;
            }
            return result;
        }

        // Token: 0x06000098 RID: 152 RVA: 0x0000EBD8 File Offset: 0x0000CDD8
        public static System.Drawing.Image GetImage(string path)
        {
            System.Drawing.Image result = null;
            if (File.Exists(path))
            {
                try
                {
                    result = System.Drawing.Image.FromFile(path);
                }
                catch (Exception ex)
                {
                }
            }
            return result;
        }

        // Token: 0x06000099 RID: 153 RVA: 0x0000EC20 File Offset: 0x0000CE20
        public static bool CopyDirectory(string sourceDirName, string destDirName)
        {
            bool result = false;
            try
            {
                if (!Directory.Exists(destDirName))
                {
                    Directory.CreateDirectory(destDirName);
                    File.SetAttributes(destDirName, File.GetAttributes(sourceDirName));
                }
                if (destDirName[destDirName.Length - 1] != Path.DirectorySeparatorChar)
                {
                    destDirName += Path.DirectorySeparatorChar;
                }
                string[] files = Directory.GetFiles(sourceDirName);
                foreach (string text in files)
                {
                    if (File.Exists(destDirName + Path.GetFileName(text)))
                    {
                        File.Delete(destDirName + Path.GetFileName(text));
                    }
                    File.Copy(text, destDirName + Path.GetFileName(text), true);
                    File.SetAttributes(destDirName + Path.GetFileName(text), FileAttributes.Normal);
                }
                string[] directories = Directory.GetDirectories(sourceDirName);
                foreach (string text2 in directories)
                {
                    conmon.CopyDirectory(text2, destDirName + Path.GetFileName(text2));
                }
                result = true;
            }
            catch (Exception ex)
            {
            }
            return result;
        }

        // Token: 0x0600009A RID: 154 RVA: 0x0000ED0C File Offset: 0x0000CF0C
        public static void RunCmd(string str)
        {
            try
            {
                Process process = new Process();
                process.StartInfo.FileName = "cmd.exe";
                process.StartInfo.UseShellExecute = false;
                process.StartInfo.RedirectStandardInput = true;
                process.StartInfo.RedirectStandardOutput = true;
                process.StartInfo.RedirectStandardError = true;
                process.StartInfo.CreateNoWindow = true;
                process.StartInfo.Verb = "RunAs";
                process.Start();
                process.StandardInput.WriteLine(str + "&exit");
                process.StandardInput.AutoFlush = true;
                process.StandardInput.WriteLine("exit");
                string text = process.StandardOutput.ReadToEnd();
                process.WaitForExit();
                process.Kill();
                process.Dispose();
            }
            catch (Exception ex)
            {
            }
        }

        // Token: 0x0600009C RID: 156 RVA: 0x0000EDE0 File Offset: 0x0000CFE0
        public static string ConvertBig5(string str, bool toBig5)
        {
            string result = str;
            try
            {
                // 注册代码页提供程序
                Encoding.RegisterProvider(CodePagesEncodingProvider.Instance);
                if (toBig5)
                {
                    // 将Unicode转换为Big5
                    byte[] bytes = Encoding.Unicode.GetBytes(str);
                    result = Encoding.GetEncoding(950).GetString(bytes);
                }
                else
                {
                    // 将Big5转换为Unicode
                    byte[] bytes = Encoding.GetEncoding(950).GetBytes(str);
                    result = Encoding.Unicode.GetString(bytes);
                }
            }
            catch (Exception ex)
            {
            }
            return result;
        }

        // Token: 0x0600009D RID: 157 RVA: 0x0000EE48 File Offset: 0x0000D048
        public static string ConvertKorea(string str, bool toKorea)
        {
            string result = str;
            try
            {
                byte[] bytes = Encoding.Default.GetBytes(str);
                if (toKorea)
                {
                    result = Encoding.GetEncoding(949).GetString(bytes);
                }
                else
                {
                    result = Encoding.Default.GetString(bytes);
                }
            }
            catch (Exception ex)
            {
            }
            return result;
        }

        // Token: 0x0600009E RID: 158 RVA: 0x0000EEB0 File Offset: 0x0000D0B0
        public static bool IsNumberic(string oText)
        {
            try
            {
                int.Parse(oText);
                return true;
            }
            catch (Exception ex)
            {
                return false;
            }
        }

        // Token: 0x060000F9 RID: 249
        [DllImport("kernel32", CharSet = CharSet.Auto, SetLastError = true)]
        private static extern int LCMapString(int Locale, int dwMapFlags, string lpSrcStr, int cchSrc, [Out] string lpDestStr, int cchDest);

        // Token: 0x060000FA RID: 250 RVA: 0x00017F14 File Offset: 0x00016114
        public static string ToSimplified(string source)
        {
            string text = new string(' ', source.Length);
            int num = LCMapString(2048, 33554432, source, source.Length, text, source.Length);
            return text;
        }

        // Token: 0x06000100 RID: 256 RVA: 0x000182A8 File Offset: 0x000164A8
        public static bool IsFileInUse(string fileName)
        {
            bool result = true;
            FileStream fileStream = null;
            try
            {
                fileStream = new FileStream(fileName, FileMode.Open, FileAccess.Read, FileShare.None);
                result = false;
            }
            catch
            {
            }
            finally
            {
                if (fileStream != null)
                {
                    fileStream.Close();
                }
            }
            return result;
        }

        // Token: 0x06000106 RID: 262 RVA: 0x000184B8 File Offset: 0x000166B8
        public static int PrintFileVersionInfo(string path)
        {
            FileInfo fileInfo = null;
            try
            {
                fileInfo = new FileInfo(path);
            }
            catch (Exception ex)
            {
                return 0;
            }
            int result;
            if (fileInfo != null && fileInfo.Exists)
            {
                result = Convert.ToInt32((double)fileInfo.Length / 1024.0);
            }
            else
            {
                result = 0;
            }
            return result;
        }

        // Token: 0x06000105 RID: 261 RVA: 0x00018484 File Offset: 0x00016684
        public static void Delay(int milliSecond)
        {
            int tickCount = Environment.TickCount;
            while (Math.Abs(Environment.TickCount - tickCount) < milliSecond)
            {
                // 移除 Application.DoEvents()，使用 Thread.Sleep 代替
                System.Threading.Thread.Sleep(1);
            }
        }

        // Token: 0x060000F7 RID: 247 RVA: 0x00017DC8 File Offset: 0x00015FC8
        public static void CopyDir(string srcPath, string aimPath)
        {
            try
            {
                if (aimPath[aimPath.Length - 1] != Path.DirectorySeparatorChar)
                {
                    aimPath += Path.DirectorySeparatorChar;
                }
                if (!Directory.Exists(aimPath))
                {
                    Directory.CreateDirectory(aimPath);
                }
                string[] files = Directory.GetFiles(srcPath);
                foreach (string text in files)
                {
                    if (!File.Exists(aimPath + Path.GetFileName(text)))
                    {
                        File.Copy(text, aimPath + Path.GetFileName(text), true);
                    }
                }
            }
            catch (Exception ex)
            {
                throw;
            }
        }

        // Token: 0x0400011A RID: 282
        private const int LOCALE_SYSTEM_DEFAULT = 2048;

        // Token: 0x0400011B RID: 283
        private const int LCMAP_SIMPLIFIED_CHINESE = 33554432;

        // Token: 0x0400011C RID: 284
        private const int LCMAP_TRADITIONAL_CHINESE = 67108864;
    }
}