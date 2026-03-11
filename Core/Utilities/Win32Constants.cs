using System;

namespace FS服装搭配专家v1._0
{
    namespace Win32
    {
        // Win32 API 常量定义
        public static class Constants
        {
            // 区域设置常量
            public const int LOCALE_SYSTEM_DEFAULT = 2048;
            public const int LOCALE_USER_DEFAULT = 1024;
            
            // 字符映射标志
            public const int LCMAP_SIMPLIFIED_CHINESE = 33554432;  // 简体中文
            public const int LCMAP_TRADITIONAL_CHINESE = 67108864; // 繁体中文
            
            // 窗口消息
            public const int WM_NULL = 0x0000;
            public const int WM_CREATE = 0x0001;
            public const int WM_DESTROY = 0x0002;
            public const int WM_MOVE = 0x0003;
            public const int WM_SIZE = 0x0005;
            public const int WM_ACTIVATE = 0x0006;
            public const int WM_SETFOCUS = 0x0007;
            public const int WM_KILLFOCUS = 0x0008;
            public const int WM_ENABLE = 0x000A;
            public const int WM_SETREDRAW = 0x000B;
            
            // 键盘消息
            public const int WM_KEYDOWN = 0x0100;
            public const int WM_KEYUP = 0x0101;
            public const int WM_CHAR = 0x0102;
            
            // 鼠标消息
            public const int WM_MOUSEMOVE = 0x0200;
            public const int WM_LBUTTONDOWN = 0x0201;
            public const int WM_LBUTTONUP = 0x0202;
            public const int WM_RBUTTONDOWN = 0x0204;
            public const int WM_RBUTTONUP = 0x0205;
            
            // 文件操作
            public const int FILE_ATTRIBUTE_NORMAL = 0x80;
            public const int FILE_ATTRIBUTE_READONLY = 0x01;
            public const int FILE_ATTRIBUTE_HIDDEN = 0x02;
            public const int FILE_ATTRIBUTE_SYSTEM = 0x04;
            
            // 错误代码
            public const int ERROR_SUCCESS = 0;
            public const int ERROR_FILE_NOT_FOUND = 2;
            public const int ERROR_PATH_NOT_FOUND = 3;
            public const int ERROR_ACCESS_DENIED = 5;
            
            // 内存状态
            public const int MEM_COMMIT = 0x1000;
            public const int MEM_RESERVE = 0x2000;
            public const int MEM_RELEASE = 0x8000;
            
            // 页面保护
            public const int PAGE_READONLY = 0x02;
            public const int PAGE_READWRITE = 0x04;
            public const int PAGE_EXECUTE = 0x10;
            public const int PAGE_EXECUTE_READ = 0x20;
            public const int PAGE_EXECUTE_READWRITE = 0x40;
        }
    }
}