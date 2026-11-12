# Shopify 订阅者自动录入询盘云

简体中文 | [English](README.md)

这是一个 Agent Skill，用于设计、实施、测试和排查“Shopify 邮件订阅者或网站表单线索自动录入询盘云（LeadsCloud）CRM”的集成流程。

## 能做什么

- 选择 Shopify Flow、Webhook 或第三方表单 Webhook 接入方式
- 将 Shopify 订阅者字段转换为统一的询盘云线索字段
- 使用 Shopify 客户 ID、外部 ID 和标准化邮箱查重
- 生成稳定的幂等键，避免重复投递产生重复线索
- 对限流、网络故障和服务端错误进行有限次数重试
- 按询盘云真实文档配置 Bearer、API Key、OAuth 或 HMAC 鉴权
- 记录脱敏审计结果，隔离无法自动处理的失败事件
- 使用零第三方依赖的 Python 脚本标准化 Shopify 订阅事件

本技能不会猜测询盘云未公开的接口地址、字段 ID、租户 ID 或签名算法。正式写入前必须取得目标询盘云账号的真实接口资料。

## 安装

将仓库克隆到 Codex 技能目录：

```bash
git clone https://github.com/heyujie079-ctrl/shopify-to-leadscloud.git ~/.codex/skills/shopify-to-leadscloud
```

安装后，在下一轮对话中显式调用：

```text
使用 $shopify-to-leadscloud 帮我把 Shopify 邮件订阅者自动录入询盘云。
```

也可以直接描述任务，Codex 会在匹配时自动发现该技能。

## 使用者需要告知哪些内容

### 1. Shopify 信息

- Shopify 店铺域名，例如 `example.myshopify.com`
- 当前 Shopify 套餐
- 订阅入口类型：主题自带订阅表单、Shopify Forms、结账订阅或第三方表单
- 需要同步的范围：仅未来新增订阅者，还是包含历史订阅者
- 是否只创建新线索，还是允许更新询盘云已有线索
- 是否需要处理重新订阅和退订事件
- 希望同步的字段，例如邮箱、姓名、电话、国家、语言、来源页面和 UTM 参数

### 2. 询盘云信息

- API 基础地址
- 创建线索接口
- 查询、查重或 Upsert 接口
- 鉴权类型，以及准确的请求头或签名规则
- 企业、组织或租户 ID
- 询盘云必填字段及自定义字段 ID
- 接口速率限制、超时要求和允许的重试方式
- 测试账号、沙箱环境或测试线索的清理规则

### 3. 业务规则

- 邮箱相同但 Shopify 客户 ID 不同时如何处理
- 重复订阅时更新哪些字段
- 是否允许修改负责人、销售阶段、标签或备注
- 新线索默认负责人、来源渠道、标签和线索阶段
- 失败多久后提醒、提醒谁，以及是否需要人工补录
- 客户数据保留期限及隐私合规要求

### 4. 凭证的安全提供方式

请告知凭证存放位置和变量名，不要把真实 Token、API Key、密码或 HMAC Secret 提交到仓库。

推荐使用：

- Shopify Flow Secrets
- 部署平台的 Secret Manager
- 服务器环境变量
- 企业批准的凭证管理工具

常用配置变量示例：

```text
LEADSCLOUD_BASE_URL
LEADSCLOUD_CREATE_LEAD_PATH
LEADSCLOUD_LOOKUP_PATH
LEADSCLOUD_AUTH_MODE
LEADSCLOUD_TENANT_ID
LEADSCLOUD_TOKEN 或 LEADSCLOUD_API_KEY
```

以上只是变量名，不包含任何真实凭证。

## 推荐接入流程

```text
Shopify 新增邮件订阅者
        ↓
Shopify Flow 或 Webhook
        ↓
验签、字段校验和标准化
        ↓
按 external_id、幂等键和邮箱查重
        ↓
调用询盘云创建或更新线索
        ↓
记录结果；临时故障有限重试；永久错误进入人工处理
```

对于主题订阅表单或 Shopify Forms，优先考虑 Shopify Flow 的 `Customer subscribed to email marketing` 触发器。如果当前套餐不能使用 Flow 的 HTTP 请求，或者需要更强的可靠性控制，可以使用 `customers_email_marketing_consent/update` Webhook 和服务端中转程序。

第三方表单不会自动进入 Shopify 的专用订阅触发器，应直接使用表单服务商的 Webhook，或者先确认该表单确实更新了 Shopify 的邮件营销订阅状态。

## 常用调用示例

### 设计方案

```text
使用 $shopify-to-leadscloud。我的店铺使用 Shopify Forms，询盘云提供创建线索和查询线索接口。请设计字段映射、查重和重试方案，暂时不要写入生产环境。
```

### 检查接口资料是否完整

```text
使用 $shopify-to-leadscloud 检查这份询盘云 API 文档，列出正式接入还缺少的信息。
```

### 标准化一条 Shopify 事件

```bash
python scripts/normalize_lead.py subscriber.json \
  --store-domain example.myshopify.com \
  --event-id event-001 \
  --require-subscribed
```

脚本会输出包含 `external_id`、`dedupe_key` 和 `idempotency_key` 的统一线索数据，但不会向任何外部系统发送请求。

### 上线前测试

```text
使用 $shopify-to-leadscloud，根据测试环境完成一次 dry-run，并验证重复投递、429 限流、凭证失效和字段校验失败场景。
```

## 上线验收标准

- 同一事件重复发送不会创建第二条线索
- 重新订阅不会覆盖 CRM 中无关的负责人、销售阶段和跟进记录
- 429、5xx 和网络超时使用同一个幂等键进行有限重试
- 400、401、403 和 422 不会被无限重试
- 日志不记录真实 Token、完整邮箱、电话和原始客户数据
- 退订事件默认不会创建新线索

## 仓库结构

```text
shopify-to-leadscloud/
├── SKILL.md
├── agents/
│   └── openai.yaml
├── references/
│   ├── field-mapping.md
│   └── reliability-auth.md
└── scripts/
    └── normalize_lead.py
```

当前仓库没有包含任何询盘云真实凭证或生产接口参数。
