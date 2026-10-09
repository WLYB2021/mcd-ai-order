# 麦麦AI点单助手（McdAIPoint）

> 在 WorkBuddy 对话里直接看麦当劳菜单、选餐加购、实时算券后价、确认后一键下单的 **AI2UI 点单 Skill**。
> 麦当劳程序员创意开发大赛参赛作品（非官方产品）。

## 这是什么

传统点麦当劳要在 App 里翻好几屏。本 Skill 把点餐做成 **"对话即界面"**：

- 你只说一句话："帮我点麦当劳""加一个麦辣鸡腿堡""换个可乐"
- Agent 自动调用麦当劳 MCP，把**菜单变成卡片**、把**购物车变成实时报价**
- 你看清楚价格后说"结账"，Agent 才真正下单并给你支付链接

一句话：**不用开 App，在 WorkBuddy 里就把麦当劳点了。**

## 为什么不一样（AI2UI）

目前同类作品大多是"文字推荐型"——给你一段建议就完了。本 Skill 做的是**端到端真实下单闭环**：菜单可视化 + 购物车可视化 + 真实 `create-order`，是本届少有的"AI 直接生成点单界面"的实现。

## 功能

- 🍔 附近门店选择（到店自取 / 车道取餐 / 麦乐送外送）
- 🃏 卡片式菜单：分类、名称、价格、标签、热量一目了然
- 🛒 自然语言加购："加一个麦辣鸡腿堡""不要薯条""饮料换可乐"
- 💰 实时算价：自动叠加可用优惠券，显示商品金额 / 优惠 / 配送费 / 应付
- ✅ 二次确认守卫：下单前必须你明确说"确认/结账"，绝不误下真实订单
- 🔗 下单后返回订单详情与支付链接，可查进度 / 取消

## 安装（在 WorkBuddy 中使用）

1. 申请麦当劳 MCP Token：登录 [open.mcd.cn/mcp](https://open.mcd.cn/mcp) → 控制台 → 激活 → 复制 Token。
2. 在 WorkBuddy 左侧【专家·技能·连接器】→【连接器】→【自定义连接器】→【配置 MCP】，粘贴：

   ```json
   {
     "mcpServers": {
       "mcd-mcp": {
         "type": "streamablehttp",
         "url": "https://mcp.mcd.cn",
         "headers": { "Authorization": "Bearer ${MCD_MCP_TOKEN}" }
       }
     }
   }
   ```

   将 `${MCD_MCP_TOKEN}` 替换为你的真实 Token，保存并**启用 / 信任** `mcd-mcp`。
3. 把本仓库的 `SKILL.md` 放入 WorkBuddy 的 Skills 目录（用户级 `~/.workbuddy/skills/` 或项目级 `.workbuddy/skills/`）。
4. 在对话框说"帮我点麦当劳"即可开始。

> 完整配置示例见 [`mcp-config.example.json`](./mcp-config.example.json)；MCP 工具调用说明见 [`MCP_INTEGRATION.md`](./MCP_INTEGRATION.md)。

## 使用示例（对话）

```
你：帮我点麦当劳，到店自取
Agent：📍 附近可点餐门店：
  1. 国贸 TR 餐厅（到店自取）
  2. 环球金融中心餐厅（到店自取）
你：第 1 个
Agent：🍔 菜单（部分）：
  [麦辣鸡腿堡套餐] ¥XX · 含鸡腿堡+薯条+饮料
  [巨无霸] ¥XX · 经典
  ...
你：来一个麦辣鸡腿堡套餐，饮料换可乐
Agent：🛒 当前购物车：
  麦辣鸡腿堡套餐（可乐） ×1
  小计 ¥XX，已用券 -¥X，应付 ¥XX
你：结账
Agent：✅ 已下单，支付链接：https://...（订单号 #xxxx）
```

## 目标用户

- 通勤 / 加班想快速点餐、懒得翻 App 的人
- 团餐、拼单需要快速凑单的人
- 想用自然语言 + 可视化界面管理麦当劳点餐的 WorkBuddy 用户

## 仓库文件

| 文件 | 说明 |
| --- | --- |
| `SKILL.md` | 核心 Skill 定义（AI2UI 点单流程） |
| `MCP_INTEGRATION.md` | 实际使用的麦当劳 MCP 工具、调用流程、业务价值 |
| `mcp-config.example.json` | 脱敏配置示例（环境变量占位符） |
| `CONTEST_DECLARATION.md` | 参赛声明（内容不可改） |
| `workbuddy.md` | WorkBuddy 开发上下文（专项奖励核验） |
| `preview.html` | AI2UI 菜单 + 购物车界面静态预览（示例数据） |

## 免责声明

本项目为参赛作品，非麦当劳官方产品。餐品信息、价格及供应状态以麦当劳官方渠道实时结果为准；下单为真实交易，请确认后再支付。
