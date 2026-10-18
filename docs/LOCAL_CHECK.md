# 本地逻辑检查

在已安装基础、Pipecat/Silero 集成与 verification 依赖的环境中，从仓库根目录运行：

```powershell
python -m scripts.check_local
```

结果保存在 `scambench/local-check.json`。检查包括开发测试和离线合成流程；存在跳过测试时报告 incomplete_or_failed，避免缺少可选依赖却误报完整通过。它不需要麦克风、AssemblyAI 密钥或 AWS。

报告包含运行时间、Python 版本、测试数量、失败/跳过数量、模拟流程结果以及 Python 源码和项目配置的 SHA-256。摘要用于对应源码版本，不是报告签名，不证明文件来源或系统安全，也未覆盖全部运行依赖和二进制模型。

测试密钥临时生成，不写入报告；重放数据库是临时测试文件，结束后删除。政策允许分支是测试中明确设置的模拟条件，未解除原会话的 COOLING_OFF 状态。

本阶段检查证明指定案例符合预期，不能替代真实身份注册、真实人工确认、语音联网稳定性或独立数据集评测。运行时依赖版本见 requirements 文件。
