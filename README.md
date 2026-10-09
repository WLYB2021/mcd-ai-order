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

- 📝 **一次性信息收集**：开场一次问清用餐方式 / 称呼 / 手机号 / 位置，后续不再反复打断
- 🍔 附近门店选择（到店自取 / 得来速 / 麦乐送外送），并**同步展示各店活动与预约能力**（`reservation`）
- 🃏 卡片式菜单：用 emoji + 文字呈现（**名称 / 标签 / 描述**一目了然），真实图片以可点击链接给出，点开浏览器看原图
- 🎟️ **进点餐主动拉券+活动**：本店券 `query-store-coupons` + 卡包券 `query-my-coupons` + 可领券 `available-coupons` + 当月活动 `campaign-calendar`
- 🛒 自然语言加购："加一个麦辣鸡腿堡""不要薯条""饮料换可乐"
- 💰 实时算价：自动叠加可用优惠券，显示商品金额 / 优惠 / 配送费 / 应付
- ✅ 二次确认守卫：下单前一张总订单卡，必须你明确说"确认/结账"，绝不误下真实订单
- 💳 **对话内直接支付**：`create-order` 返回支付链接/二维码，在 WorkBuddy 里点链接或扫码即可，**无需跳转麦当劳 App**（堂食外带还返回取餐柜二维码）

## 关于图片（重要）

WorkBuddy 内联面板出于安全限制**不加载外部图片**，因此本 Skill 在面板内统一使用 emoji + 文字卡片，餐品真实图片通过 **Markdown 链接** 提供（点开浏览器看原图）。需要看带真实图片的视觉版，请用浏览器打开 [`preview.html`](./preview.html)。

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

## 可运行源码（离线调试 / 演示）

除 Skill 提示外，仓库提供标准库零依赖的参考实现 [`src/mcd_mcp_client.py`](./src/mcd_mcp_client.py)，直连麦当劳 MCP 复刻整个点单流程（搜店 / 菜单 / 算价 / 下单），可作为 Skill 的调试与演示工具：

```bash
export MCD_MCP_TOKEN="你的Token"
python src/mcd_mcp_client.py demo            # 只读演示：搜店→菜单→算价
python src/mcd_mcp_client.py stores --city 北京 --keyword 国贸
python src/mcd_mcp_client.py menu  --store 1950564 --order-type 1 --be-type 1
python src/mcd_mcp_client.py price --store 1950564 --order-type 1 --be-type 1 \
       --item 1100:1 --item 9900005411:1
# 真实下单需显式 --confirm（真实交易，谨慎）
python src/mcd_mcp_client.py order --store 1950564 --order-type 1 --be-type 1 \
       --item 1100:1 --take-way <code> --confirm
```

## 使用示例（对话）

```
你：帮我点麦当劳
Agent：👋 先一次性确认下信息（一次问完，后面不打断你）：
  · 用餐方式？[到店自取 / 麦乐送外送 / 得来速 / 企业团餐]
  · 怎么称呼？· 手机号？· 位置或地址？
你：（选择到店自取 + 填好其余信息）

Agent：📍 附近门店 + 今日活动：
  1. 建外SOHO餐厅（距269m，营业中，支持预约：夜市17:14–21:45）★
  2. 国贸 TR 餐厅（距1.2km）
  🎉 今日活动：9.9元早餐两件套、麦旋风任选券…
你：第 1 个

Agent：🎟️ 本店可用券 / 活动 已为你拉好；🍔 菜单（emoji 卡片 + 图片链接）：
  [巨无霸] ¥XX  🖼 图片  [麦辣鸡腿堡套餐] ¥XX …
你：来一个麦辣鸡腿堡套餐，饮料换可乐
Agent：🛒 购物车：麦辣鸡腿堡套餐（可乐）×1，已用券 -¥X，应付 ¥XX

你：结账
Agent：🧾 总订单卡（门店/商品/优惠/应付/取餐方式）— 确认下单？
你：确认
Agent：✅ 已下单！💳 支付链接 + 二维码（在此直接付，无需开App）：https://...
  订单号 #xxxx · 用 query-order 查进度 / cancel-order 取消
```

## 目标用户

- 通勤 / 加班想快速点餐、懒得翻 App 的人
- 团餐、拼单需要快速凑单的人
- 想用自然语言 + 可视化界面管理麦当劳点餐的 WorkBuddy 用户

## 仓库文件

| 文件 | 说明 |
| --- | --- |
| `SKILL.md` | 核心 Skill 定义（AI2UI 点单流程，含面板图片限制的渲染约定） |
| `MCP_INTEGRATION.md` | 实际使用的麦当劳 MCP 工具、调用流程、业务价值 |
| `src/mcd_mcp_client.py` | 可运行参考实现（零依赖直连 MCP，复刻点单流程） |
| `mcp-config.example.json` | 脱敏配置示例（环境变量占位符） |
| `CONTEST_DECLARATION.md` | 参赛声明（内容不可改） |
| `workbuddy.md` | WorkBuddy 开发上下文（专项奖励核验） |
| `preview.html` | AI2UI 菜单 + 购物车界面静态预览（浏览器打开，含真实图片） |

## 免责声明

本项目为参赛作品，非麦当劳官方产品。餐品信息、价格及供应状态以麦当劳官方渠道实时结果为准；下单为真实交易，请确认后再支付。图片在 WorkBuddy 面板内受限制，以链接形式在浏览器查看。
