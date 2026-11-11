using System;
using System.Runtime.InteropServices;

public class EmrRawPrinter {
    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Ansi)]
    public class DOCINFOA {
        [MarshalAs(UnmanagedType.LPStr)] public string pDocName;
        [MarshalAs(UnmanagedType.LPStr)] public string pOutputFile;
        [MarshalAs(UnmanagedType.LPStr)] public string pDataType;
    }

    [DllImport("winspool.Drv", EntryPoint = "OpenPrinterA", SetLastError = true,
        CharSet = CharSet.Ansi, ExactSpelling = true, CallingConvention = CallingConvention.StdCall)]
    public static extern bool OpenPrinter([MarshalAs(UnmanagedType.LPStr)] string szPrinter, out IntPtr hPrinter, IntPtr pd);

    [DllImport("winspool.Drv", EntryPoint = "ClosePrinter", SetLastError = true,
        ExactSpelling = true, CallingConvention = CallingConvention.StdCall)]
    public static extern bool ClosePrinter(IntPtr hPrinter);

    [DllImport("winspool.Drv", EntryPoint = "StartDocPrinterA", SetLastError = true,
        CharSet = CharSet.Ansi, ExactSpelling = true, CallingConvention = CallingConvention.StdCall)]
    public static extern bool StartDocPrinter(IntPtr hPrinter, int level, [In, MarshalAs(UnmanagedType.LPStruct)] DOCINFOA di);

    [DllImport("winspool.Drv", EntryPoint = "EndDocPrinter", SetLastError = true,
        ExactSpelling = true, CallingConvention = CallingConvention.StdCall)]
    public static extern bool EndDocPrinter(IntPtr hPrinter);

    [DllImport("winspool.Drv", EntryPoint = "StartPagePrinter", SetLastError = true,
        ExactSpelling = true, CallingConvention = CallingConvention.StdCall)]
    public static extern bool StartPagePrinter(IntPtr hPrinter);

    [DllImport("winspool.Drv", EntryPoint = "EndPagePrinter", SetLastError = true,
        ExactSpelling = true, CallingConvention = CallingConvention.StdCall)]
    public static extern bool EndPagePrinter(IntPtr hPrinter);

    [DllImport("winspool.Drv", EntryPoint = "WritePrinter", SetLastError = true,
        ExactSpelling = true, CallingConvention = CallingConvention.StdCall)]
    public static extern bool WritePrinter(IntPtr hPrinter, IntPtr pBytes, int dwCount, out int dwWritten);

    public static void SendBytes(string printerName, byte[] bytes) {
        IntPtr hPrinter = IntPtr.Zero;
        IntPtr pBytes = IntPtr.Zero;
        try {
            if (!OpenPrinter(printerName.Normalize(), out hPrinter, IntPtr.Zero)) {
                throw new Exception("OpenPrinter failed: " + Marshal.GetLastWin32Error());
            }
            DOCINFOA di = new DOCINFOA();
            di.pDocName = "EMR label";
            di.pDataType = "RAW";
            if (!StartDocPrinter(hPrinter, 1, di)) {
                throw new Exception("StartDocPrinter failed: " + Marshal.GetLastWin32Error());
            }
            try {
                if (!StartPagePrinter(hPrinter)) {
                    throw new Exception("StartPagePrinter failed: " + Marshal.GetLastWin32Error());
                }
                try {
                    pBytes = Marshal.AllocHGlobal(bytes.Length);
                    Marshal.Copy(bytes, 0, pBytes, bytes.Length);
                    int written;
                    if (!WritePrinter(hPrinter, pBytes, bytes.Length, out written)) {
                        throw new Exception("WritePrinter failed: " + Marshal.GetLastWin32Error());
                    }
                } finally {
                    EndPagePrinter(hPrinter);
                }
            } finally {
                EndDocPrinter(hPrinter);
            }
        } finally {
            if (pBytes != IntPtr.Zero) { Marshal.FreeHGlobal(pBytes); }
            if (hPrinter != IntPtr.Zero) { ClosePrinter(hPrinter); }
        }
    }
}
