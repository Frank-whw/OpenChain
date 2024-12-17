# OpenChain - 开源社区关系可视化系统 🔗

 ![License](https://img.shields.io/badge/License-MIT-blue)[![Node Version](https://img.shields.io/badge/node-%3E%3D18.0.0-brightgreen)](https://nodejs.org/)[![Python Version](https://img.shields.io/badge/python-%3E%3D3.8-red)](https://www.python.org/)![Language](https://img.shields.io/badge/Language-简体中文-brightgreen)

## 目录 📑
- [项目背景](#项目背景) 🎯
- [项目简介](#项目简介) 📖
- [功能亮点](#功能亮点) ✨
- [技术架构](#技术架构) 🏗️
- [安装部署](#安装部署) 🚀
- [使用指南](#使用指南) 📚
- [推荐算法](#推荐算法) 🧮
- [TODO](#todo) 📝
- [贡献指南](#贡献指南) 🤝
- [许可证](#许可证) 📄

## 项目背景 🎯
OpenChain 是一个专注于开源社区关系可视化的创新项目，是"OpenRank杯"开源数字生态分析与应用创新赛的参赛作品。在当今开源生态蓬勃发展的背景下，开发者和项目之间的关系网络变得越来越复杂。我们的项目旨在通过数据可视化和智能分析，帮助开发者更好地理解和参与开源社区。

## 项目简介 📖
OpenChain 利用 OpenDigger 工具集和 GitHub API，结合星火大模型，为用户提供直观的开源社区关系分析。项目通过可视化展示和智能分析，帮助用户发现：
- 🔍 项目间的关联关系
- 👥 开发者的兴趣偏好
- 🤝 潜在的协作机会
- 📈 技术生态的发展趋势

## 功能亮点 ✨
1. 多维度关系分析 🔄
   - 👥 用户-用户关系：发现相似兴趣的开发者
   - 🔗 项目-项目关系：展示相关联的开源项目
   - 🎯 用户-项目关系：推荐适合的贡献机会

2. 智能推荐系统 🧠
   - 📚 基于用户技术栈的项目推荐
   - 👨‍💻 基于项目特征的贡献者推荐
   - 📊 考虑多个维度的相似度计算

3. 大模型分析 🤖
   - 🔍 利用星火大模型进行深度分析
   - 📝 提供详细的关系解读
   - 💡 生成个性化的协作建议

4. 交互式可视化 📊
   - 🎨 力导向图展示关系网络
   - 📈 节点大小反映影响力
   - 🔗 连线粗细表示关联强度
   - 🖱️ 支持缩放和拖拽操作

[示例图片位置 1：主界面展示]

## 技术架构 🏗️

### 前端技术栈 💻
- ⚛️ Next.js 14 - React框架
- 📘 TypeScript - 类型安全的JavaScript
- 📊 D3.js - 数据可视化库
- 🎨 Tailwind CSS - 样式框架
- 🎯 Radix UI - UI组件库

### 后端技术栈 🔧
- ⚡ FastAPI - Python Web框架
- 📊 OpenDigger API - 开源数据分析
- 🐙 GitHub API - 数据源
- 🤖 星火大模型 API - 智能分析
- 🔑 Python-dotenv - 环境变量管理


## 安装部署 🚀

### 环境要求 📋
- Node.js 18+ ⚡
- Python 3.8+ 🐍
- npm 或 yarn 📦
- Git 🔧

### 1. 获取 GitHub Token
1. 访问 GitHub 设置页面：https://github.com/settings/tokens
2. 点击 "Generate new token (classic)"
3. 勾选以下权限：
   - repo
   - read:user
   - user:email
4. 生成并保存 token

### 2. 克隆项目
```bash
git clone https://github.com/Frank-whw/OpenChain.git
cd OpenChain
```

### 3. 前端部署
```bash
# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

### 4. 后端部署
```bash
# 进入后端目录
cd backend

# 安装 Python 依赖
pip install -r requirements.txt

# 配置环境变量
# 创建 .env 文件并添加：
GITHUB_TOKEN=你的GitHub_Token

# 启动后端服务
uvicorn main:app --reload
```

### 5. 访问应用
打开浏览器访问 http://localhost:3000

[示例图片位置 3：部署成功截图]

## 使用指南 📚

### 1. 基本功能
- 选择分析类型（用户/仓库）
- 输入搜索内容
- 查看可视化结果
- 点击节点查看详细分析

### 2. 使用示例
1. 用户->仓库
   ```
   类型：用户
   查找：仓库
   输入：torvalds
   ```
   [示例图片位置 4：用户分析结果]

2. 仓库->用户
   ```
   类型：仓库
   查找：用户
   输入：microsoft/vscode
   ```
   [示例图片位置 5：仓库分析结果]
3. 用户->用户
   ```
   类型：用户
   查找：用户
   输入：torvalds
   ```
   [示例图片位置 6：用户分析结果]
4. 仓库->仓库
   ```
   类型：仓库
   查找：仓库
   输入：microsoft/vscode
   ```
   [示例图片位置 7：仓库分析结果]

## 推荐算法 🧮

### 1. 相似度计算
项目采用多维度的相似度计算方法：

#### 用户-用户相似度
- 语言偏好匹配
- 技术栈重合度
- 项目规模相似性
- 活跃度对比

#### 仓库-仓库相似度
- 编程语言
- 主题标签
- 项目规模
- 功能描述相似度

#### 用户-仓库相似度
- 技术栈匹配度
- 贡献历史分析
- 项目规模适配度
- 活跃度评估

### 2. 推荐流程
1. 数据收集
   - GitHub API 获取基础数据
   - OpenDigger 获取活跃度数据
   - 用户行为数据分析

2. 特征提取
   - 语言偏好分析
   - 主题标签提取
   - 活跃度计算
   - 规模评估

3. 相似度计算
   - 多维度特征向量构建
   - 加权相似度计算
   - 归一化处理

4. 结果排序
   - 相似度排序
   - 活跃度加权
   - TOP-N 选取
### 3. 推荐算法特点
推荐算法的特点是：
1. 多维度相似度计算，考虑了技术栈、兴趣主题和活跃度等多个方面
2. 使用缓存机制（`@lru_cache`）优化性能
3. 实现了并行处理以提高效率
4. 具有完善的错误处理和降级机制
5. 支持灵活的权重调整
6. 集成了 OpenDigger API 提供的开源指标数据

[示例图片位置 6：推荐算法流程图]

## TODO 📝
- [x] 基础界面框架搭建 🎨
- [x] 后端API实现 ⚡
- [x] 前端可视化实现 📊
- [x] 大模型分析实现 🤖
- [x] 优化推荐算法 🧮
- [x] 改进可视化效果 🎯
- [ ] 添加用户反馈机制 📢

## 贡献指南 🤝
欢迎提交 Issue 和 Pull Request 来帮助改进项目。在提交之前，请确保：
1. 🎯 Issue 描述清晰具体
2. 📝 Pull Request 包含完整的功能描述
3. ✨ 代码符合项目规范
4. 🧪 提供必要的测试用例
