Option Explicit
Dim shell, files, folder, executable, command
Set shell = CreateObject("WScript.Shell")
Set files = CreateObject("Scripting.FileSystemObject")
folder = files.GetParentFolderName(WScript.ScriptFullName)
executable = folder & "\dist\Obsydian Finder\Obsydian Finder.exe"
If files.FileExists(executable) Then
    shell.Run """" & executable & """", 1, False
Else
    executable = folder & "\.venv\Scripts\pythonw.exe"
    If files.FileExists(executable) Then
        command = """" & executable & """ """ & folder & "\launch.py"""
        shell.Run command, 0, False
    Else
        MsgBox "Use the packaged Obsydian Finder application, or install the desktop dependencies in the project .venv first.", vbExclamation, "Obsydian Finder"
    End If
End If
