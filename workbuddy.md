# WorkBuddy 开发上下文（workbuddy.md）

> 本文件用于在「麦当劳程序员创意开发大赛」中核验本项目是否真实使用腾讯 WorkBuddy 智能体开发，作为 WorkBuddy 专项奖励的凭证。
> 以下为使用 WorkBuddy 从 0 搭建本项目的对话上下文摘要。

## 一、开发过程概要

1. **需求确认**：用户在 WorkBuddy 中提出"想参加麦当劳 MCP 开发大赛"，并明确希望做一个 **AI2UI 点单 Skill**——让 Agent 在 WorkBuddy 对话里直接展示菜单并帮用户下单。
2. **竞品调研**：WorkBuddy 抓取并分析了活动 Issue 列表（约 13 个报名），发现现有作品集中在"省钱精算"与"营养减脂"两类文字推荐型 Skill，**尚无"对话内可视化点单 + 真实下单"的 AI2UI 实现**，据此确定差异化方向。
3. **MCP 能力核验**：WorkBuddy 直接调用 `mcd-mcp` 的 `tools/list`，实测确认服务器可用、Token 有效，并核对了 35 个线上工具（含文档未收录的 `query-promotions`、`query-survey-coupon`）。
4. **仓库搭建**：WorkBuddy 生成了完整的参赛仓库文件，包括 `SKILL.md`、`MCP_INTEGRATION.md`、`README.md`、`mcp-config.example.json`、`CONTEST_DECLARATION.md`、本文件与 `preview.html`；后续补齐了零依赖可运行源码 `src/mcd_mcp_client.py`（直连麦当劳 MCP 复刻点单流程，可作调试/演示）。
5. **安全设计**：WorkBuddy 在 Skill 中内置"下单前必须用户二次确认"的强制守卫，避免误下真实订单。
6. **图片渲染决策**：用户全流程实测发现 WorkBuddy 内联面板不加载外部图片，WorkBuddy 据此将菜单呈现改为「emoji 文字卡片 + 图片 Markdown 链接（浏览器打开）」，并刷新 `preview.html` 作为浏览器端带真实图片的视觉 Demo。

## 二、关键对话节点（节选）

- 用户：想做一个简单的 AI2UI，让用户可以直接让 agent 帮忙下单，例如直接在 WorkBuddy 中查看菜品下单。
- WorkBuddy：确认方向可行且差异化强，设计"到店自取为主、外送可扩展"的流程，并加入二次确认守卫。
- WorkBuddy：生成 `SKILL.md`，定义执行流程（确认场景 → 定位门店 → 展示菜单 → 选餐 → 算价含券 → 二次确认 → 下单）。
- WorkBuddy：生成 `MCP_INTEGRATION.md`，列出真实调用的 14 个麦当劳 MCP 工具及调用链。

## 三、使用的 WorkBuddy 能力

- 智能体对话与任务规划（Agent mode）
- 联网检索（WebFetch / WebSearch）用于活动规则与竞品分析
- 本地文件读写（Write / Read）搭建参赛仓库
- 直连麦当劳 MCP（`tools/list` 实测）核验工具可用性
- 可视化预览（`preview.html`）展示 AI2UI 界面形态

## 四、说明

本文件为开发上下文的摘要导出，用于活动专项奖励核验。完整对话以 WorkBuddy 本地会话为准。
