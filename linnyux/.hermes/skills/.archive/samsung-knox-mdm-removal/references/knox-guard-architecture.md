# Knox Guard 服务器端架构参考

> 来源：Samsung Knox 官方文档 (2026-07-12 抓取)

## 核心架构：服务端-客户端模型

```
Knox Guard 服务器 (us-kg-portal / eu-kg-portal)
    │
    ├── 策略推送 + 锁定指令
    │
Samsung Knox 服务器 (设备注册数据库)
    │
    ├── 设备注册 + 硬件绑定
    │
设备端 Knox Agent (com.samsung.android.knox)
    │
    └── Knox TEE (安全执行环境) + 硬件级保修位 (e-fuse)
```

## 设备状态生命周期

```
上传(Upload) → 待定(Pending) → 接受(Accept)/拒绝(Reject)
    → 管理中(Manage) → 锁定(Lock)/解锁(Unlock)
```

### 关键状态
- **上传**: 设备通过经销商或 CSV 上传到控制台
- **待定**: 等待管理员审批
- **接受**: 设备加入管理，分配许可证
- **锁定**: 包括自动锁定（离线超时）、手动锁定
- **离线锁定**: 设备断网超时（3-200天）后自动锁定
- **完全移除**: 从管理中删除设备

## 离线锁定机制（关键攻击面）

- 设备可配置为离线超时后自动锁定（3-200天）
- 离线锁定后，用户必须联系运营商恢复功能
- 支持 PIN 离线解锁：管理员生成 PIN → 用户在锁屏输入
- **Hardened Security 模式设备**：PIN 解锁后有24小时窗口连接服务器获取策略，否则重新锁定
- 重启会关闭24小时窗口

## REST API 接口

Knox Guard 提供 REST API (v1.1.3)：
- 设备管理端点
- 策略推送端点
- 锁定/解锁操作
- 注册管理

## Knox Mobile Enrollment 注册流程

1. IT 管理员和经销商交换 Knox 客户 ID 和经销商 ID
2. 经销商上传设备 ID 到 Knox 经销商门户
3. IT 管理员批准设备上传
4. 分配注册配置文件
5. 设备用户完成注册

## Hardened Security 模式 (Galaxy S26+)

仅限 Device Financing 域，强制启用：
- **Default lock**: 错误发生时自动锁定
- **Hacking lock**: 检测恶意行为并锁定
- **Multi-layer lock**: 引导加载程序层 + 应用层多层防护
- **Date/time block**: 阻止手动修改系统时间

## 商业工具参考

| 许可证 | 年费 | 积分/年 | 流程折扣 | 手机连接数 |
|--------|------|---------|----------|------------|
| Basic | $99.9 | 999 | 0% | 100 |
| Professional | $149.9 | 1,499 | 10% | 1,500 |
| Premium | ~$299 | ~3,000 | 20%+ | 无限 |

## 关键命令

```bash
# 查找 Knox/MDM 包
adb shell pm list packages | grep -iE 'mdm|knox|enterprise|safetynet|samsung.android.knox'

# 卸载关键 Knox 包（可能需要 root）
adb shell pm uninstall -k com.sec.enterprise.knox
adb shell pm uninstall -k com.samsung.android.knox
adb shell pm uninstall -k com.samsung.android.knox.bbp
adb shell pm uninstall -k com.sec.android.app.safetynet

# 强制禁用 Knox 代理
adb shell pm disable-user --user 0 com.samsung.android.knox

# 标记设备已配置（跳过设置向导）
adb shell settings put global device_provisioned 1

# 组合固件 root 后清除 Knox 数据
adb shell rm -rf /data/system/gatekeeper.*
adb shell rm -rf /data/system_de/0/spgatekeeper.db
```

## 官方文档 URL

- Knox Guard 概览: https://docs.samsungknox.com/admin/knox-guard/
- 状态流程: https://docs.samsungknox.com/admin/knox-guard/get-started/knox-guard-status-flow/
- 锁定/解锁: https://docs.samsungknox.com/admin/knox-guard/how-to-guides/manage-devices/lock-and-unlock-devices/
- 离线锁定: https://docs.samsungknox.com/admin/knox-guard/how-to-guides/manage-policies/normal-tenant/offline-device-lock/
- REST API: https://docs.samsungknox.com/dev/knox-guard/api/
- Knox Mobile Enrollment: https://docs.samsungknox.com/admin/knox-mobile-enrollment/
- Hardened Security: https://docs.samsungknox.com/admin/knox-guard/get-started/hardened-security-mode/
