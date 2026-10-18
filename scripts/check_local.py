"""Run local regression tests and the synthetic demo; write a bounded report.

Usage: python -m scripts.check_local
No API keys, transcript capture or cloud service calls are needed.
"""
import hashlib
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from callgate.bench import evaluate


def main():
    root = Path(__file__).resolve().parents[1]
    report = {"generated_at":datetime.now(timezone.utc).isoformat(),
              "scope":"local developer tests and synthetic demo; not real-world fraud accuracy",
              "python":sys.version.split()[0]}
    # Bind this report to source bytes, including uncommitted files.
    paths = sorted([*root.glob('callgate/**/*.py'), *root.glob('tests/**/*.py'),
                    *root.glob('scripts/*.py'), *root.glob('callgate/demo/*'),
                    *root.glob('*.ps1'), root/'pyproject.toml'])
    report['source_sha256'] = {p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
                              for p in paths}
    report['scenarios'] = evaluate(root/'scambench/scenarios.jsonl')
    scenario_pass = all(row['state_pass'] and not row['missing_events'] and not row['extra_events']
                        for row in report['scenarios']['rows'])
    with TemporaryDirectory(prefix='callgate-check-') as directory:
        xml = Path(directory)/'tests.xml'
        tests = subprocess.run([sys.executable,'-m','pytest','-q','-p','no:cacheprovider',
                                '--basetemp',str(Path(directory)/'pytest'),
                                '--junitxml',str(xml)], cwd=root)
        counts = dict(tests=0, failures=0, errors=0, skipped=0)
        if xml.exists():
            suites = ET.parse(xml).getroot()
            for suite in ([suites] if suites.tag == 'testsuite' else suites.findall('testsuite')):
                for key in counts:
                    counts[key] += int(suite.get(key,0))
        report['tests'] = dict(exit_code=tests.returncode, **counts)
        demo = subprocess.run([sys.executable,'-m','scripts.offline_demo'], cwd=root,
                              capture_output=True,text=True)
        report['demo_exit_code'] = demo.returncode
        if demo.returncode == 0:
            report['demo'] = json.loads(demo.stdout)
        else:
            report['demo'] = {'status':'failed; run python -m scripts.offline_demo for diagnosis'}
    report['status'] = ('passed' if tests.returncode == 0 and counts['tests'] > 0
                        and counts['skipped'] == 0 and demo.returncode == 0 and scenario_pass else 'incomplete_or_failed')
    output = root/'scambench/local-check.json'
    output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    summary = root/'scambench/LOCAL_RESULTS.md'
    lines = ['# CallGate 本地逻辑验证', '',
             f"生成时间：{report['generated_at']}", '',
             f"结果：{report['status']}。测试 {counts['tests']} 项；失败 {counts['failures']}；错误 {counts['errors']}；跳过 {counts['skipped']}。", '',
             '下列为固定的合成开发案例，不能当作真实诈骗识别准确率。', '',
             (f"攻击提醒召回：{report['scenarios']['alert_recall']:.1%} "
              f"（{report['scenarios']['alert_confusion']['tp']}/"
              f"{report['scenarios']['alert_confusion']['tp'] + report['scenarios']['alert_confusion']['fn']}）；"
              f"正常或明确无需提醒案例的特异度：{report['scenarios']['specificity']:.1%} "
              f"（{report['scenarios']['alert_confusion']['tn']}/"
              f"{report['scenarios']['alert_confusion']['tn'] + report['scenarios']['alert_confusion']['fp']}）。"),
             '',
             (f"95% Wilson 区间：召回 {report['scenarios']['alert_recall_wilson95'][0]:.1%}–"
              f"{report['scenarios']['alert_recall_wilson95'][1]:.1%}；特异度 "
              f"{report['scenarios']['specificity_wilson95'][0]:.1%}–"
              f"{report['scenarios']['specificity_wilson95'][1]:.1%}。分母很小，仅用于开发回归。"),
             '',
             '| 案例 | 预期状态 | 实际状态 | 证据与状态均符合 |',
             '|---|---|---|---|']
    for row in report['scenarios']['rows']:
        ok = row['state_pass'] and not row['missing_events'] and not row['extra_events']
        lines.append(f"| {row['id']} | {row['expected_state']} | {row['state']} | {'通过' if ok else '未通过'} |")
    lines += ['', '状态解释：UNVERIFIED 表示未验证身份；CHALLENGED 表示先核验；COOLING_OFF 表示暂停并独立核验；BLOCKED 表示建议不要分享敏感信息。当前语音模块为建议模式。', '',
              f"离线凭据演示退出码：{demo.returncode}（0 为完成断言检查）。确认者为测试密钥，策略允许分支为模拟设置，未完成真人核验。", '',
              '机器可读结果与源码摘要见 [local-check.json](local-check.json)。数学定义与实现边界见 [数学框架](../docs/MATHEMATICAL_FRAMEWORK.md)。', '']
    summary.write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps({'status':report['status'],'tests':report['tests'],'report':str(output)},indent=2))
    return 0 if report['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
