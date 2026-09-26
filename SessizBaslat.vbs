Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

' Proje klasörünün yolunu otomatik tespit eder
scriptPath = fso.GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = scriptPath

' Python'ı hiç konsol açmayan "pythonw.exe" ile tamamen gizli başlatır
WshShell.Run "pythonw app.py", 0, False

' Sunucunun hazır olması için 2 saniye arka planda bekler
WScript.Sleep 2000

' Tarayıcıyı pencere (uygulama) modunda açar
WshShell.Run "chrome --app=http://127.0.0.1:5000", 1, true