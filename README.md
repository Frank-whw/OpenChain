# OpenChain - 开源社区关系可视化系统

## 项目简介

OpenChain 是一个专注于开源社区关系可视化的创新项目，旨在探索和展示开源生态中的多维度关系网络。本项目是"OpenRank杯"开源数字生态分析与应用创新赛的参赛作品，利用 OpenDigger 工具集和开源数据，结合星火大模型，为用户提供直观的开源社区关系分析。

### 核心功能
- 项目关系分析：探索不同开源项目之间的依赖关系和协作模式
- 贡献者网络：可视化展示开源社区中的贡献者关系网络
- 智能分析：利用星火大模型对关系网络进行深度分析和解读
- 多平台支持：支持 GitHub 和 Gitee 两大开源平台的数据分析

## 技术架构

### 前端技术栈
- Next.js 14 - React框架
- TypeScript - 类型安全的JavaScript
- D3.js - 数据可视化库
- Tailwind CSS - 样式框架
- Radix UI - UI组件库

### 后端技术栈（开发中）
- Python
- OpenDigger API
- GitHub/Gitee API
- 星火大模型 API
- FastAPI（计划中）

## 快速开始

### 环境要求
- Node.js 18+
- Python 3.8+
- npm 或 yarn

### 前端部署
1. 克隆项目
\`\`\`bash
git clone [项目地址]
cd openchain
\`\`\`

2. 安装依赖
\`\`\`bash
npm install
# 或
yarn install
\`\`\`

3. 启动开发服务器
\`\`\`bash
npm run dev
# 或
yarn dev
\`\`\`

4. 访问 http://localhost:3000 查看应用

### 后端部署（开发中）
1. 安装Python依赖
\`\`\`bash
cd backend
pip install -r requirements.txt
\`\`\`

2. 配置环境变量
创建 .env 文件并添加以下配置：
\`\`\`
GITHUB_TOKEN=你的GitHub Token
SPARK_API_KEY=你的星火大模型API密钥
\`\`\`

3. 启动后端服务（即将推出）
\`\`\`bash
python main.py
\`\`\`

## 使用指南

1. 平台选择
   - 在界面顶部选择要分析的平台（GitHub/Gitee）
   - 选择分析类型（Repository/User）

2. 搜索
   - 在搜索框中输入要分析的仓库名称（例如：odoo/odoo）或用户名
   - 点击"Find Repo"或"Find User"按钮开始分析

3. 查看结果
   - 等待数据加载完成
   - 在可视化图表中查看关系网络
   - 点击节点可查看详细信息和关系分析

## 项目特色

1. 直观的可视化界面
   - 使用D3.js实现流畅的力导向图
   - 节点大小反映项目影响力
   - 连线表示项目间的关联关系

2. 智能分析（开发中）
   - 基于星火大模型的关系解读
   - 项目协作建议
   - 贡献者匹配推荐

3. 多维度数据支持
   - OpenRank指数分析
   - 项目依赖关系
   - 贡献者网络

## 开发路线图

- [x] 基础界面框架搭建
- [x] 前端可视化实现
- [ ] 后端API开发
- [ ] 星火大模型集成
- [ ] 数据分析优化
- [ ] 用户交互体验提升

## 贡献指南

欢迎提交 Issue 和 Pull Request 来帮助改进项目。在提交之前，请确保：

1. Issue 描述清晰具体
2. Pull Request 包含完整的功能描述
3. 代码符合项目规范
4. 提供必要的测试用例

## 许可证

本项目采用 MIT 许可证
