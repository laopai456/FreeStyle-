using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
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
        public static void RunCmd(string cmd)
        {
            try
            {
                ProcessStartInfo processStartInfo = new ProcessStartInfo();
                processStartInfo.FileName = "cmd.exe";
                processStartInfo.Arguments = "/c " + cmd;
                processStartInfo.UseShellExecute = false;
                processStartInfo.RedirectStandardInput = true;
                processStartInfo.RedirectStandardOutput = true;
                processStartInfo.RedirectStandardError = true;
                processStartInfo.CreateNoWindow = true;
                Process process = Process.Start(processStartInfo);
                process.WaitForExit();
                process.Close();
            }
            catch (Exception ex)
            {
            }
        }

        // Token: 0x0600009B RID: 155 RVA: 0x0000ED9C File Offset: 0x0000CF9C
        public static int PrintFileVersionInfo(string fileName)
        {
            int result = 0;
            try
            {
                FileVersionInfo versionInfo = FileVersionInfo.GetVersionInfo(fileName);
                result = File.ReadAllBytes(fileName).Length;
            }
            catch (Exception ex)
            {
            }
            return result;
        }

        // Token: 0x0600009C RID: 156 RVA: 0x0000EDE0 File Offset: 0x0000CFE0
        public static string ConvertBig5(string str, bool toBig5)
        {
            string result = str;
            try
            {
                byte[] bytes = Encoding.Default.GetBytes(str);
                if (toBig5)
                {
                    result = Encoding.GetEncoding(950).GetString(bytes);
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
    }
}