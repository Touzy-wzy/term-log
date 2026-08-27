# termlog

自动记录本地开发时的终端会话内容和长期服务日志。

## 安装

    cd E:/termlog
    python -m venv .venv
    source .venv/Scripts/activate   # Linux/Mac 上用 .venv/bin/activate
    pip install -e ".[windows]"     # Linux/Mac 上不需要 [windows]

## 一、终端自动录制

**开启**（装上之后，以后新开的终端窗口都会自动被记录）：

    termlog hook install

这会给 `~/.bashrc` 和 PowerShell 的 `$PROFILE` 文件加上一段有标记包裹的代码。装好之后，你正常打开新终端使用即可（不会改变操作习惯），这个终端里出现的所有内容都会同时保存到
`~/.termlog/logs/<项目路径>/sessions/` 目录下。

**查看当前状态**（确认现在是装着还是没装）：

    termlog hook status

**关闭**（卸载钩子，以后新开的终端就不再被记录）：

    termlog hook uninstall

这个功能开启之后是持续生效的，不需要每次开机重新装，只有主动执行 `uninstall` 才会关闭。

执行 `uninstall` 时会先自动做一次导出：把从上次 `install` 到现在这段时间内产生的所有会话日志和托管服务日志，去除颜色/控制转义序列后，另存一份纯文本副本，分别放在每个项目目录下的 `sessions_view/`、`services_view/<服务名>/`（与 `sessions/`、`services/<服务名>/` 同级），文件名不变。原始带转义序列的日志文件不受影响。下次重新 `install` 会开始一个新的时间窗口。

## 二、托管开发服务日志采集

用来启动你自己指定的长期运行服务（比如某个项目的 `python app.py`），并持续采集它的输出。

**第一步，先配置**（编辑 `~/.termlog/termlog.yaml`，没有就新建）：

    services:
      - name: my-api
        command: python app.py
        cwd: E:/my-project

**开启**（启动这个服务，并开始记录它的输出）：

    termlog service start my-api

一次性启动配置文件里列出的所有服务：

    termlog service start --all

**查看运行状态**：

    termlog service status

**实时查看某个服务当前的日志**：

    termlog service logs my-api -f

**关闭**（停止这个服务）：

    termlog service stop my-api

## 配置

`~/.termlog/termlog.yaml`：

    retention_days: 14      # 超过这个天数的会话/服务日志会被自动删除
    max_log_size_mb: 50     # 单个日志文件超过这个大小会自动切分成新文件

## 以纯文本方式查看日志

日志文件里原样保留了终端的颜色、光标控制等转义序列，所以直接用文本编辑器打开会看到很多类似
`[?25l[93m...` 这样的内容混在真实文字里。用下面的命令可以查看或导出一份去除这些控制码的干净文本版本：

    termlog log view <日志文件路径>
    termlog log view <日志文件路径> --out <导出文件路径>

这个命令不会改变日志文件本身的存储内容，只是在查看/导出时才做转换。

## 已知局限

- 非交互场景（脚本、工具调用 `bash -c "..."` 或 `powershell -Command "..."`、录制器自己重新启动的 shell）会被钩子主动跳过，不会被录制——只有真正的交互式终端会话才会被记录。因为非交互场景没有键盘输入，如果强行接管会一直卡住等待永远不会来的输入。
- 由于钩子的工作方式是"整体接管"当前 shell 进程,一些会在终端刚打开时自动注入命令的工具（比如 VSCode 的"New Terminal"会自动帮你激活项目的虚拟环境）可能会把这条命令发给"接管之前"的旧 shell 进程,而这个进程此时已经把控制权交给录制器了，命令实际上会丢失。这种情况下终端本身的内容依然会被完整记录，只是那一条自动注入的命令没有生效,需要你手动执行一次（比如 `.\.venv\Scripts\Activate.ps1`）。
- 如果在录制过程中用方向键调历史命令、按 Tab 补全，或者粘贴一大段内容，由于终端本身是靠"移动光标覆盖屏幕上某处内容"来实现动态刷新效果的，而日志是按时间顺序线性记录的，去除颜色控制码后查看纯文本时，这部分操作过程可能会出现新旧内容拼接在一起、不太好读的情况。日志文件本身没有丢失任何信息（可以完整还原当时屏幕效果），只是目前 `log view` 这个纯文本查看命令没法完美处理这类场景。命令执行完之后的正式输出（报错信息、命令结果等）不受影响，仍然清晰可读。
