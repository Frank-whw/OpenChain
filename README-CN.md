# OpenChain - 开源社区关系可视化系统

  

![License](https://img.shields.io/badge/License-MIT-blue)[![Node Version](https://img.shields.io/badge/node-%3E%3D18.0.0-brightgreen)](https://nodejs.org/)[![Python Version](https://img.shields.io/badge/python-%3E%3D3.8-red)](https://www.python.org/)[![EN](https://img.shields.io/badge/English-README.md-blue)](README.md)
![Language](https://img.shields.io/badge/Language-简体中文-brightgreen)

## 目录

- [项目背景](#项目背景)

- [项目简介](#项目简介)

- [功能特性](#功能特性)

- [技术架构](#技术架构)

- [安装部署](#安装部署)

- [使用指南](#使用指南)

- [推荐算法](#推荐算法)

- [开发计划](#开发计划)

- [贡献指南](#贡献指南)

- [许可证](#许可证)

  

## 项目背景

OpenChain 是一个专注于**开源社区关系可视化**的创新项目，作为"OpenRank杯"开源数字生态分析与应用创新赛的**参赛作品**。在当今开源生态蓬勃发展的背景下，开发者和项目之间的关系网络日益复杂。本项目通过**数据可视化**和**智能分析**，为开发者提供深入的开源社区洞察。

  

## 项目简介

OpenChain 基于 OpenDigger 工具集和 GitHub API，结合星火大模型，构建了一个完整的开源社区关系分析平台。系统主要聚焦于：

- 项目间的关联关系分析

- 开发者兴趣偏好画像

- 潜在协作机会发现

- 技术生态发展趋势预测

  

## 功能特性

1. 多维度关系分析

   - 用户间关系：识别具有相似技术栈的开发者

   - 项目间关系：挖掘项目依赖与技术关联

   - 用户-项目关系：精准推荐贡献机会

  

2. 智能推荐系统

   - 基于用户技术栈的项目推荐

   - 基于项目特征的贡献者推荐

   - 多维度相似度计算与匹配

  

3. 大模型分析

   - 星火大模型深度分析

   - 关系网络解读

   - 个性化协作建议生成

  

4. 交互式可视化

   - 力导向图展示关系网络

   - 节点影响力可视化

   - 关联强度动态展示

   - 高度交互操作支持

  

## 技术架构

  

### 前端技术栈

- Next.js 14 - React框架

- TypeScript - 类型安全保障

- D3.js - 数据可视化引擎

- Tailwind CSS - 样式框架

- Radix UI - 组件库

  

### 后端技术栈

- FastAPI - Python Web框架

- OpenDigger API - 开源数据分析

- GitHub API - 数据源

- 星火大模型 API - 智能分析

- Python-dotenv - 环境配置管理

  

## 安装部署

  

### 环境要求

- Node.js 18+

- Python 3.8+

- npm 或 yarn

- Git

  

### 1. GitHub Token 配置

1. 访问 GitHub 设置页面：https://github.com/settings/tokens

2. 生成新的访问令牌 (classic)

3. 配置必要权限：

   - repo

   - read:user

   - user:email

4. 保存生成的 token

  

### 2. 项目获取

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

  

### 5. 访问系统

浏览器访问 http://localhost:3000

  

## 使用指南

  

### 基本功能

- 分析类型选择（用户/仓库）

- 搜索目标输入

- 可视化结果查看

- 节点详情分析

  

### 使用示例

1. 用户->仓库分析

```

   类型：用户

   查找：仓库

   输入：Frank-whw

```
![用户-仓库分析](https://raw.githubusercontent.com/Frank-whw/img/main/blog/202412301616905.png)

点击除中心节点以外的任何节点都会生成大模型分析结果
![AI分析](https://raw.githubusercontent.com/Frank-whw/img/main/blog/202412301617349.png)

2. 用户->用户分析
```

   类型：用户

   查找：用户

   输入：Frank-whw
```
![用户-用户分析](https://raw.githubusercontent.com/Frank-whw/img/main/blog/202412301618504.png)
3. 仓库->用户
```


   类型：仓库

   查找：用户

   输入：Frank-whw/OpenChain

```
 ![仓库-用户分析](https://raw.githubusercontent.com/Frank-whw/img/main/blog/202412301621838.png)

4. 仓库->仓库
  ```

   类型：仓库

   查找：仓库

   输入：Frank-whw/OpenChain
```

![仓库-仓库分析](https://raw.githubusercontent.com/Frank-whw/img/main/blog/202412301619762.png)

### 说明文档系统
系统提供全面的说明文档，包括：
1. 算法说明
   - 用户相似度计算方法
   - 仓库相似度计算方法
   - 推荐流程详解
   - 节点类型分类规则

2. 交互功能
   - 节点悬停显示详细信息
   - 点击交互触发AI分析
   - 缩放和平移功能
   - 动态力导向布局

3. 可视化元素
   - 不同节点类型的颜色编码
   - 基于重要性的大小变化
   - 连接强度可视化
   - 交互式提示框

## 推荐算法

  

### 相似度计算

系统采用多维度的相似度计算方法：

  

#### 用户相似度

- 语言偏好匹配

- 技术栈重合度

- 项目规模相似性

- 活跃度对比

  

#### 仓库相似度

- 编程语言分析

- 主题标签匹配

- 项目规模评估

- 功能描述相似度

  

### 推荐流程

1. 数据收集

   - GitHub API 数据获取

   - OpenDigger 指标分析

   - 用户行为数据挖掘

  

2. 特征提取

   - 语言偏好分析

   - 主题标签提取

   - 活跃度计算

   - 规模评估

  

3. 相似度计算

   - 特征向量构建

   - 加权相似度计算

   - 归一化处理

  

4. 结果优化

   - 相似度排序

   - 活跃度加权

   - TOP-N 筛选

  

## 开发计划

- [x] 基础框架搭建

- [x] API 系统实现

- [x] 可视化引擎开发

- [x] 大模型集成

- [x] 推荐算法优化

- [x] 可视化效果提升

- [ ] 用户反馈系统

  

## 贡献指南

欢迎提交 Issue 和 Pull Request 参与项目改进。提交前请确保：

1. Issue 描述清晰完整

2. Pull Request 包含详细说明

3. 代码符合项目规范

4. 提供必要的测试用例

  

## 许可证

本项目采用 MIT 许可证