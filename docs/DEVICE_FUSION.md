# UCLA 本地融合演示（2026-10-17 新增）

## 当前运行入口与边界

- 手机设备收件服务保持原进程 PID 2797、`127.0.0.1:8780`；原 ngrok 地址、设备凭证、viewer 凭证和收件箱数据库不变。
- 当前 ngrok 仍只转发 `http://127.0.0.1:8780`。实测公网 `/fusion`、`/api/fusion`、`/api/review/pending` 均 404。
- **本地融合操作台：http://127.0.0.1:8781/fusion**。实测 HTTP 200、text/html。
- **独立本地核验端：127.0.0.1:8782**。完整角色入口仅存于本机 `.test-tmp/fusion-live/reviewer-saved-family-link.txt`，由操作者私下打开，不粘贴到聊天或公开链接。
- 本次新增的是另一组本地 CallGate 会话，复用原 policy/联系人/签名/模拟操作代码；不是迁入另一组已经运行中的 participant 会话。旧 demo 不受影响。该实例启动登记 `saved-family`，为原流程相同的合成联系人登记，不等于独立真人身份验证。
- Windows localhost 与 WSL 的转发尚未经过该电脑浏览器验证；若本机 Windows 页面仍出现 404，应定位 Windows/WSL 转发或端口占用，不能将融合服务加入当前公网隧道作为替代。

没有重启 8780 或 ngrok；没有通过公网暴露融合/核验端。当前融合启动器及子进程只绑定 127.0.0.1。

## 操作者最小闭环

1. 在同机浏览器打开 `http://127.0.0.1:8781/fusion`。
2. 将本机 `.test-tmp/fusion-live/operator.token` 的原始内容填入“本地操作凭证”，点击“连接 / 刷新”。这与手机 device.token、收件箱 viewer.token、ngrok authtoken 都不同。操作页凭证只保留页面内存，不写 URL 或浏览器存储。
3. 点击“同意处理虚构测试内容”。提交虚构测试文本 `Send money.`，观察原 policy 返回 `CHALLENGED`。要用真实语音，可私下打开本机 `participant-link.txt` 中这组实例的原 participant 链接，完成录音后回操作页。
4. 在绑定区明确选择页面显示的实际当前 session ID、设备 `nano-01`、已登记联系人 `saved-family`、虚构目标和模拟金额（单位 USD cents）。点击“确认绑定会话、设备、联系人和这次模拟操作”。可在任意 policy 状态保存绑定，但不满足 policy 时不能创建请求。
5. 让队友通过原 8780/ngrok 地址发送设备事件。页面每两秒只读刷新最近 100 条：`verify_request` 显示“用户请求可信联系人核验”；`help_request` 独立显示求助意图，不创建核验。
6. 选择本次真实按钮事件，点击“按当前绑定创建核验请求”。为避免回放历史事件，服务不会自动处理旧记录，也不会因打开页面就发起核验。未绑定、设备不匹配、会话变化、缺少同意、policy 不为 CHALLENGED、授权已否决、存在待回应请求或录音尚未结束时，会显示实际原因，且不覆盖现有请求。
7. 原 workflow 创建真实的本地确认请求后，时间线增加“核验请求创建”，显示绑定范围和原六位挑战码。由你通过另一个约定渠道将码交给核验者。
8. 核验者私下使用 `reviewer-saved-family-link.txt` 中的完整链接，点击“读取当前请求”，核对身份、金额、目标；批准时输入原挑战码，或直接拒绝。签名密钥只在原独立 reviewer 子进程持有。操作页没有批准按钮。
9. 回操作台观察“联系人回应（已验签接受）”和“模拟操作结果”。只有原 broker 接受并处理签名决定后才记录这两个状态；错误签名、错误挑战、过期、取消或未收到决定都不会被画成已回应/已完成。模拟完成不等于真实转账。

重置会话后旧绑定失效，必须重新同意、提交当前证据、重新绑定。设备事件本身不提供身份、金额、目标、policy 证据或付款权限。

## 实现与幂等

`callgate/device_fusion.py` 仅以 SQLite `mode=ro` 读取既有收件箱，不读取手机设备凭证，也不修改收件数据。绑定/处理/查看融合接口只接受这组 broker 的 participant 操作凭证，继承原 Host、Origin、无 CORS 边界。默认启动器未启用融合时不存在这些路由。

绑定由操作端输入，session ID 必须匹配实际 workflow；联系人必须来自启动登记目录。`DemoWorkflow.request_bound_confirmation()` 在同一 workflow 锁内检查会话、同意、pending，再调用原 `request_confirmation()`，保留 CHALLENGED、否决锁、频率、联系人路由、挑战和签名路径。录音活动仍由原 broker 检查。

同一 event ID 的持久 claim 在请求创建之前提交到独立 `.test-tmp/fusion-live/fusion.sqlite3`，唯一键阻止并发/重试/重启再次创建。绑定后的每次处理仅提交 event ID；不允许设备传入批准字段。已消费事件即使重新绑定也保留原请求和原操作范围。

断电/崩溃发生在 claim 与请求记录之间时，结果可能不确定；该事件保持 claimed，不自动重试。此处优先不重复创建，未实现事务性跨 workflow/SQLite 恢复。重启会丢失内存 session、pending、密钥和当前绑定，但不能通过重启重新消费旧事件。请求过期/被原 participant 替换/取消后显示“已不再待回应”，不伪造联系人回应或结果。

时间线中的“收到”时间来自原收件记录；创建与回应时间为本地服务观察时间，不是手机硬件时钟或端到端延迟指标。所有记录仍是本地 demo，收件箱显示最近 100 条；没有短信、推送、真实联系人送达或真实付款。

## 再次启动（不要在当前运行时重复启动）

```bash
.venv/bin/python -m scripts.start_review_demo \
  --participant-port 8781 --reviewer-port 8782 \
  --device-events-db .test-tmp/device-live/events.sqlite3 \
  --fusion-runtime-dir .test-tmp/fusion-live
```

融合模式不读取 `.env` 密钥文件；会生成这一组本地新的角色凭证并保存到权限受限的 runtime，而不打印它们。启动目录权限 700，文件遵循 umask 077；请勿上传或提交 runtime。启动器可能在端口被占用时回退到空闲端口，应以本机 `launcher.log` 中不含凭证的实际操作台地址为准。

只停止新增融合服务：

```bash
.venv/bin/python .test-tmp/fusion-live/stop_fusion.py
```

该工具仅向本次融合父进程发 SIGINT，由原 launcher 停止其 reviewer/broker 子进程；不停止 8780 或 ngrok。启动/停止融合会丢失其当前会话及待回应请求，现场使用前需告知操作者。当前无需重启任何服务。

## 验证与未验证部分

融合测试使用独立临时数据库和真实 Ed25519 签名，覆盖批准/拒绝闭环、错误签名无伪造时间线、绑定/会话重置、policy/同意/录音拒绝、pending 不覆盖、并发/持久去重、重启不重发、绑定变化不改原范围、角色和 Host/Origin 隔离。Node UI 测试覆盖只观察不自动发起、显式绑定和处理分离、求助不创建、拒绝状态与安全文字显示。

实际运行验证：本地融合 HTML/JS 200、操作凭证读取 200、无凭证 401、初始未绑定；8780 原展示页仍 200；ngrok upstream/地址未变且融合与核验路由公网 404。没有在运行中的手机收件箱插入集成测试记录，没有替操作者同意、绑定或处理队友事件。

尚未验证：队友真实 BLE/iPhone 事件进入本地融合后的人机完整操作、独立真人联系人、远程联系人送达、Windows 浏览器的新增端口访问、真实付款。当前只完成受控合成联系人/模拟操作闭环，现场真机接力需要双方实际操作。

最终验证结果：新增融合 Python 集成 15 passed；完整 Python 271 passed、3 skipped、2 条测试客户端弃用警告；两组 Node 前端逻辑共 6 passed；`git diff --check` 通过。新增融合服务已启动且保持未绑定，等待操作者进行上述真实操作。

### 新人工测试事件与挑战码位置

2026-10-17 操作者请求发送的新事件带 `local-manual-test-20261017T234509Z-` 前缀，明确为本机人工测试；8780 返回 201。发送后当前绑定仍有效、CHALLENGED、pending=false，没有自动创建请求或重置会话。刷新操作页，重新输入 operator.token 连接，在该事件卡片点击“按当前绑定创建核验请求”。创建成功后，该卡片详情下方、时间线上方会显示加粗的“**一次性挑战码（仅本地显示，通过另一条可信渠道交给核验者）**”。挑战码由原 workflow 在创建时产生，有效期两分钟；过期/取消不会重新消费同一事件。标签改动无需重启，刷新页面加载最新 JS 即可。不要将旧 no_longer_pending 事件当作新请求或复用旧码。

### 核验端“无请求”排查与入口修正

现场排查时，旧本地人工请求已 no_longer_pending，但检查当时距 expires_at 仍约 39 秒；实际 context 为 CHALLENGED、pending=false、authorization_denied=false、outcome=null。因此该次空请求不能归因于过期，也无已接受的联系人结果。原规则在接受新转录时会使 pending 失效；缺少生命周期审计，无法断定本次是哪次用户操作导致，不能伪造根因。

保存的 `reviewer-saved-family-link.txt` 指向 8782 的当前融合 reviewer，角色凭证接口 200/null，无凭证 401；接口错误没有被映射成 null。新增 UI 提示使 401/网络错误与空请求明确分开，并显示当前端地址、请求 ID、session ID 和联系人路由。

准确入口：操作台 `http://127.0.0.1:8781/fusion`；核验端 `http://127.0.0.1:8782/`。刷新核验端后，可把本机 `.test-tmp/fusion-live/reviewer-saved-family-link.txt` 的完整内容粘入“本机完整核验角色链接”密码框，点“使用当前实例入口”，替换旧标签页凭证，再点“读取当前请求”。该字段仅接受与当前页同一 origin 的链接；不会把链接发到其他地址或聊天。

创建请求后，在两分钟内读取、核对并回应；这期间不要在原 participant 或 fusion 再次提交文本、启动转录、撤回同意或重置会话。新转录的失效规则保持不变。核验页显示的 request ID 必须与操作台该卡片相同，核对后再通过另一条渠道输入挑战码。过期或取消不能恢复同一事件；如需新测试，明确使用新的 local-manual-reviewer-check 事件。

静态 HTML/JS 更新无需重启；本次没有重启当前融合、8780 或 ngrok，也没有更换凭证/地址/数据库。新增前端错误区分、实例凭证替换及 request_id 显示测试；新增未到期时新证据取消 pending 的集成测试。

实际人机本地测试现已完成：见 [2026-10-17 本地人工核验记录](LOCAL_MANUAL_VERIFICATION_2026-10-17.md)。该成功属于事件 `-983168` 的后续请求，不是此前匹配检查的旧 request；不计作手机/BLE/硬件验证。保留服务和 ngrok 运行。

## 当前产品界面：ReachGuard 英文改造

本地入口和协议不变，页面按钮/状态现已改为英文并重排布局；以上旧版中文按钮说明属于实现历史。请按 [ReachGuard 当前操作指南](REACHGUARD_UI.md) 操作，可用本地 `scripts.open_fusion_page` 打开正确角色而不复制私有链接。此次为展示层改造，不增加安全、身份、送达或硬件保证；未重启原服务或改变现有绑定、凭证和数据库。
