; STM32教学管理系统 - Inno Setup 安装脚本
; 版本: 2.6.0
; 生成日期: 2025-06-12

[Setup]
; 应用程序基本信息
AppName=STM32教学管理系统
AppVersion=2.6.0
AppPublisher=STM32教学团队
AppPublisherURL=https://github.com/GhUserLiu/ProjectF407
AppSupportURL=https://github.com/GhUserLiu/ProjectF407/issues
AppUpdatesURL=https://github.com/GhUserLiu/ProjectF407/releases
AppCopyright=Copyright (C) 2025-2026 STM32教学团队

; 安装程序设置
DefaultDirName={code:GetDefaultInstallPath}
DefaultGroupName=STM32教学管理系统
AllowNoIcons=yes
OutputDir=installer_output
OutputBaseFilename=STM32教学管理系统_v2.6.0_安装程序
SetupIconFile=app\resources\icon.ico
Compression=lzma2/max
SolidCompression=yes
InternalCompressLevel=max
; 磁盘跨片设置（支持大于4GB的安装程序）
DiskSpanning=yes
DiskSliceSize=736000000
;DiskSize=736000000

; 界面设置
WizardStyle=modern
;WizardSmallImageFile=app\resources\icon.ico
;WizardImageFile=app\resources\icon.ico
ShowComponentSizes=yes
WizardImageStretch=no
AppendDefaultDirName=no

; 权限要求
PrivilegesRequired=admin

; 卸载设置
UninstallDisplayIcon={app}\STM32教学管理系统.exe
UninstallFilesDir={app}\uninstall
CreateUninstallRegKey=yes

; 启用页面
DisableDirPage=no
DisableProgramGroupPage=no
DisableReadyPage=no
DisableFinishedPage=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加图标:"; Flags: unchecked
Name: "quicklaunchicon"; Description: "创建快速启动图标"; GroupDescription: "附加图标:"; Flags: unchecked; OnlyBelowVersion: 6.1
Name: "openreadme"; Description: "安装完成后打开说明文档"; GroupDescription: "安装后操作:"; Flags: unchecked
Name: "opendata"; Description: "安装完成后打开数据目录"; GroupDescription: "安装后操作:"; Flags: unchecked

[Files]
; 主程序（目录模式）
Source: "dist\STM32教学管理系统\STM32教学管理系统.exe"; DestDir: "{app}"; Flags: ignoreversion
; 目录模式下的依赖文件（排除 build、dist、installer_output 等构建目录）
Source: "dist\STM32教学管理系统\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "\build,\dist,\installer_output,\spec"
; 测试工具（暂时禁用 - 需要单独构建）
; Source: "dist\STM32教学管理系统_测试工具.exe"; DestDir: "{app}"; Flags: ignoreversion

; 图标文件
Source: "app\resources\icon.ico"; DestDir: "{app}\resources"; Flags: ignoreversion

; 核心配置文件
Source: "..\..\docs\teaching\common\config.yaml"; DestDir: "{app}\config"; Flags: ignoreversion skipifsourcedoesntexist
Source: "..\security_config.json"; DestDir: "{app}\config"; Flags: ignoreversion skipifsourcedoesntexist

; 评分标准
Source: "..\..\docs\teaching\common\rubrics\*.json"; DestDir: "{app}\data\rubrics"; Flags: ignoreversion skipifsourcedoesntexist

; 模板文件
Source: "..\..\docs\teaching\common\templates\*.docx"; DestDir: "{app}\data\templates"; Flags: ignoreversion skipifsourcedoesntexist
Source: "..\..\docs\teaching\common\templates\*.md"; DestDir: "{app}\data\templates"; Flags: ignoreversion skipifsourcedoesntexist
Source: "..\templates\*.md"; DestDir: "{app}\data\templates"; Flags: ignoreversion skipifsourcedoesntexist

; 测试数据 - 直接复制到data目录的子目录中
Source: "test_data\students\*"; DestDir: "{app}\data\students"; Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist
Source: "test_data\submissions\*"; DestDir: "{app}\data\submissions"; Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist
Source: "test_data\templates\*"; DestDir: "{app}\data\templates"; Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist
Source: "test_data\rubrics\*"; DestDir: "{app}\data\rubrics"; Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist

; 教学演示目录（用于多班级功能测试）
Source: "test_data\teaching_demo\*"; DestDir: "{app}\data\teaching_demo"; Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist

; 工具脚本
Source: "..\submission_utils.py"; DestDir: "{app}\tools"; Flags: ignoreversion skipifsourcedoesntexist
Source: "..\enhanced_quality_assessment.py"; DestDir: "{app}\tools"; Flags: ignoreversion skipifsourcedoesntexist
Source: "..\plagiarism_detection_enhanced.py"; DestDir: "{app}\tools"; Flags: ignoreversion skipifsourcedoesntexist
Source: "..\generate_grading_excel.py"; DestDir: "{app}\tools"; Flags: ignoreversion skipifsourcedoesntexist

; 安全模块
Source: "..\security\*.py"; DestDir: "{app}\tools\security"; Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist

; 说明文档
Source: "README.txt"; DestDir: "{app}"; Flags: ignoreversion

[Dirs]
; 创建必要的目录结构
Name: "{app}\config"
Name: "{app}\data"
Name: "{app}\data\rubrics"
Name: "{app}\data\templates"
Name: "{app}\data\test"
Name: "{app}\data\students"
Name: "{app}\data\submissions"
Name: "{app}\data\results"
Name: "{app}\tools"
Name: "{app}\tools\security"
Name: "{app}\logs"
Name: "{app}\temp"
Name: "{app}\resources"

[Icons]
Name: "{group}\STM32教学管理系统"; Filename: "{app}\STM32教学管理系统.exe"; WorkingDir: "{app}"; IconFilename: "{app}\resources\icon.ico"
Name: "{group}\打开数据目录"; Filename: "{app}\data"; WorkingDir: "{app}"; IconFilename: "{app}\resources\icon.ico"
Name: "{group}\说明文档"; Filename: "{app}\README.txt"; WorkingDir: "{app}"
Name: "{group}\卸载STM32教学管理系统"; Filename: "{uninstallexe}"
Name: "{userdesktop}\STM32教学管理系统"; Filename: "{app}\STM32教学管理系统.exe"; WorkingDir: "{app}"; IconFilename: "{app}\resources\icon.ico"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\STM32教学管理系统"; Filename: "{app}\STM32教学管理系统.exe"; WorkingDir: "{app}"; Tasks: quicklaunchicon

[Run]
; 安装完成后运行程序
Filename: "{app}\STM32教学管理系统.exe"; Description: "启动STM32教学管理系统"; Flags: postinstall nowait skipifsilent unchecked
Filename: "{app}\README.txt"; Description: "打开说明文档"; Flags: skipifsilent shellexec postinstall; Tasks: openreadme
Filename: "{app}\data"; Description: "打开数据目录"; Flags: skipifsilent shellexec postinstall; Tasks: opendata

[UninstallDelete]
; 卸载时删除用户数据目录中的文件（可选，根据用户选择）
; Type: files; Name: "{app}\data\students\*"
; Type: files; Name: "{app}\data\submissions\*"
; Type: files; Name: "{app}\data\results\*"
; Type: files; Name: "{app}\logs\*"
; Type: files; Name: "{app}\temp\*"

[Registry]
; 注册表项用于版本检查和路径记录
Root: HKLM; Subkey: "Software\STM32教学管理系统"; ValueType: string; ValueName: "InstallPath"; ValueData: "{app}"
Root: HKLM; Subkey: "Software\STM32教学管理系统"; ValueType: string; ValueName: "Version"; ValueData: "2.6.0"
Root: HKLM; Subkey: "Software\STM32教学管理系统"; ValueType: string; ValueName: "ConfigPath"; ValueData: "{app}\config"
Root: HKLM; Subkey: "Software\STM32教学管理系统"; ValueType: string; ValueName: "DataPath"; ValueData: "{app}\data"
Root: HKLM; Subkey: "Software\STM32教学管理系统"; ValueType: string; ValueName: "ToolsPath"; ValueData: "{app}\tools"
Root: HKLM; Subkey: "Software\STM32教学管理系统"; ValueType: string; ValueName: "RubricsPath"; ValueData: "{app}\data\rubrics"
Root: HKLM; Subkey: "Software\STM32教学管理系统"; ValueType: string; ValueName: "TemplatesPath"; ValueData: "{app}\data\templates"

; 文件关联
Root: HKCR; Subkey: ".stm32project"; ValueType: string; ValueName: ""; ValueData: "STM32ProjectFile"; Flags: uninsdeletekey
Root: HKCR; Subkey: "STM32ProjectFile\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\resources\icon.ico,0"
Root: HKCR; Subkey: "STM32ProjectFile\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\STM32教学管理系统.exe"" ""%1"""

[Code]
// Pascal脚本用于安装过程中的自定义操作

// 获取默认安装路径
function GetDefaultInstallPath(Param: String): String;
var
  ProgramFiles: String;
begin
  // 优先使用 Program Files
  if IsWin64 then
    ProgramFiles := ExpandConstant('{pf64}')
  else
    ProgramFiles := ExpandConstant('{pf}');

  Result := ProgramFiles + '\STM32教学管理系统';
end;

procedure InitializeWizard();
begin
  // 设置向导标题
  WizardForm.Caption := 'STM32教学管理系统 v2.6.0 安装向导';
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;

  // 在安装前检查系统要求
  if CurPageID = wpReady then
  begin
    // 可以添加系统检查逻辑
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ConfigFile, TestDataDir, ReadmeFile: String;
begin
  if CurStep = ssPostInstall then
  begin
    // 安装完成后的自定义操作

    // 创建数据目录说明文件
    TestDataDir := ExpandConstant('{app}\data');
    if ForceDirectories(TestDataDir) then
    begin
      // 创建 students 目录说明
      SaveStringToFile(TestDataDir + '\students\学生名单存放处.txt',
        'STM32教学管理系统 - 学生名单目录' + #13#10 +
        '=================================' + #13#10 + #13#10 +
        '请将学生名单（Excel格式）放入此目录。' + #13#10 +
        '文件命名建议：班级名.xlsx（如：汽服2302B班.xlsx）' + #13#10 + #13#10 +
        'Excel表格应包含以下列：' + #13#10 +
        '  学号  |  姓名  |  班级  |  分组' + #13#10 +
        ' 2023001 | 张三   | 汽服2302B | 1' + #13#10,
        False
      );

      // 创建 submissions 目录说明
      SaveStringToFile(TestDataDir + '\submissions\学生提交存放处.txt',
        'STM32教学管理系统 - 学生提交目录' + #13#10 +
        '=================================' + #13#10 + #13#10 +
        '请将学生提交的ZIP文件放入此目录。' + #13#10 + #13#10 +
        'ZIP文件命名格式：学号_姓名_实验名.zip' + #13#10 +
        '例如：2023001_张三_汽车档位模拟器.zip' + #13#10 + #13#10 +
        'ZIP文件应包含：' + #13#10 +
        '  - 实验报告（Word格式：.docx）' + #13#10 +
        '  - 代码文件（C源码：.c）' + #13#10,
        False
      );

      // 创建 results 目录说明
      SaveStringToFile(TestDataDir + '\results\处理结果输出目录.txt',
        'STM32教学管理系统 - 处理结果目录' + #13#10 +
        '=================================' + #13#10 + #13#10 +
        '系统处理学生提交后，结果将保存在此目录。' + #13#10 +
        '包括：' + #13#10 +
        '  - Excel成绩报告' + #13#10 +
        '  - 查重检测结果' + #13#10 +
        '  - 学生反馈文档' + #13#10,
        False
      );
    end;
  end;
end;

procedure CurUninstallStepChanged(CurStep: TUninstallStep);
var
  DataDir: String;
begin
  if CurStep = usUninstall then
  begin
    // 卸载前询问是否保留用户数据
    DataDir := ExpandConstant('{app}\data');
    if DirExists(DataDir) then
    begin
      if MsgBox('是否保留用户数据文件？（学生名单、提交记录、处理结果等）' + #13#10 +
                '' + #13#10 +
                '选择"是"将保留 data 文件夹中的所有数据。' + #13#10 +
                '选择"否"将删除所有文件（包括您的数据！）。',
                mbConfirmation, MB_YESNO) = IDYES then
      begin
        // 用户选择保留数据，跳过删除 data 目录
        // 卸载程序会自动跳过不在安装列表中的文件
      end
      else begin
        // 用户选择删除数据，删除整个 data 目录
        DelTree(DataDir, True, True, True);
      end;
    end;
  end;
end;
