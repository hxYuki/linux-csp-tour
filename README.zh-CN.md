# linux-csp-tour

为**当前用户、单一 Plasma Wayland 桌面会话**安装和适配 TourBox Console。基础环境由 [CSPenguin-Installer](https://github.com/parka6060/CSPenguin-Installer) 提供。

## 一键安装

先用 CSPenguin 安装 CSP，并准备官方 **TourBox Console 5.12.0** Windows 安装包。保存并正常关闭 CSP 和 Console，然后在当前桌面终端执行：

```bash
git clone https://github.com/hxYuki/linux-csp-tour.git
cd linux-csp-tour
./install.sh "$HOME/Downloads/TourBoxConsoleSetup_5.12.0.exe"
```

脚本从当前用户的 CSPenguin 启动器读取实际 Wine 前缀和运行器，解包提供的 Console 安装包，应用兼容补丁，并创建应用菜单及用户服务。完成后从菜单打开 **Clip Studio Paint**，Console 会随之启动。

适用组合：**Plasma Wayland、Wine 11.4、指定构建的 Console 5.12.0、USB TourBox NEO**。写入前会校验应用构建哈希；蓝牙和其他构建暂未覆盖。

全流程沿用当前用户身份。没有其他账号回退、身份切换、虚拟终端交接或第二套桌面；也不包含本机专用数位板规则。CSPenguin 已提供的 Wine、WebView2、DXVK、视频补丁、字体和缩略图继续复用。

## 依赖与选项

需要 Python 3.11+、Python Xlib / PyGObject、7zip、systemd 用户服务、XRandR、stty、flock、fuser。Arch 系对应包包括 `python python-xlib python-gobject 7zip xorg-xrandr util-linux psmisc`。脚本只检查依赖，不安装系统软件包；请不要使用 sudo。

Console 启动时自动识别已连接的 USB NEO。当前用户应有串口读写权限；若其他驱动占用串口，请先正常退出它。

```bash
# 只读检查与计划生成，应用可以保持运行。
./install.sh --check /path/to/TourBoxConsoleSetup_5.12.0.exe

# 对已安装的同构建 Console 重复应用。
./install.sh

# 自定义当前用户环境或设备路径。
./install.sh /path/to/installer.exe --prefix /path/to/prefix \
  --cspenguin /path/to/cspenguin --serial /dev/serial/by-id/DEVICE
```

默认继承当前语言。设备区域检查需要特定语言时，可用 `--locale zh_CN.UTF-8` 等已生成的 locale 覆盖。`--proxy` 仅覆盖 WebView2 代理，不传则保留 CSPenguin 已有参数。文件使用与上游一致的标准 `~/.local` 和 `~/.config` 路径。

## 兼容内容

- NEO 串口 raw / 115200 / 8N1、COM33 与 Windows USB 枚举。
- USB-only BLE shim、中文 HKL 重试循环修补、CSP 二维码 BitBlt 截图修补。
- 修复长键＋滚轮丢失 Alt，以及长键＋R1 连按后松开仍保持吸管；保留已有预设和快捷键。
- 应用内 SQLite DLL、Electron 拾色器软件渲染。
- 官方 CSP 集成命令补缺，保留已有快捷键和配对信息。
- 当前桌面的 Wine 工作区缓存刷新与导航器父窗口关系维护。
- 同显示会话启动、输出就绪检查、无锁 FD 继承的单实例控制，以及限定 Console 的退出处理。

窗口 helper 仅监听当前 Xwayland 连接，不枚举其他用户会话。账号登录与 companion 配对仍使用官方界面。

已有安装正常关闭 CSP 和 Console 后，重新运行 `./install.sh` 即可升级到 v3 修饰键补丁；DLL 和启动参数纳入同一备份、回退流程。v3 在延迟恢复 Alt 前复查拾色器状态，避免全部松开后再次按住 Alt。源码、版本检查和回归方法见 [补丁说明](source/modifier-agent/README.md)。

## 备份、回退和验证

自动备份在 `~/.local/state/linux-csp-tour/backups/时间戳/`，安装器会打印准确的回退命令。正常关闭应用后执行：

```bash
./install.sh --rollback "$HOME/.local/state/linux-csp-tour/backups/对应时间戳"
```

安装后又编辑过的文件会保留并提示冲突。回退恢复管理文件及服务启用状态，不倒带运行期 COM33 枚举、串口状态或应用后续写入的数据。

`bash verify.sh` 运行基础检查。真实安装包测试覆盖临时 HOME 内的完整安装、无改动重应用和回退；服务与 Wine 应用启动被模拟。独立 Xvfb 测试运行实际窗口 helper。新环境中的实体旋钮、绘图压感和配对仍需要实际验收。

仓库只包含通用脚本、补丁源码和允许分发的兼容二进制，不含官方安装包、厂商 JAR/class、个人配置、登录信息、设备序列号或本机审计记录。详细说明见 [英文 README](README.md)。
