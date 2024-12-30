# OpenChain - Open Source Community Relationship Visualization System

![License](https://img.shields.io/badge/License-MIT-blue)
[![Node Version](https://img.shields.io/badge/node-%3E%3D18.0.0-brightgreen)](https://nodejs.org/)
[![Python Version](https://img.shields.io/badge/python-%3E%3D3.8-red)](https://www.python.org/)
[![CN](https://img.shields.io/badge/简体中文-README--CN.md-blue)](README-CN.md)
![Language](https://img.shields.io/badge/Language-English-brightgreen)

## Table of Contents
- [Background](#background)
- [Introduction](#introduction)
- [Features](#features)
- [Technical Architecture](#technical-architecture)
- [Installation](#installation)
- [Usage Guide](#usage-guide)
- [Recommendation Algorithm](#recommendation-algorithm)
- [Development Plan](#development-plan)
- [Contributing](#contributing)
- [License](#license)

## Background
OpenChain is an innovative project focused on open source community relationship visualization, developed as an entry for the "OpenRank Cup" Open Source Digital Ecosystem Analysis and Innovation Competition. In today's thriving open source ecosystem, the relationship network between developers and projects is becoming increasingly complex. This project provides deep insights into open source communities through data visualization and intelligent analysis.

## Introduction
OpenChain builds a comprehensive open source community relationship analysis platform based on the OpenDigger toolkit and GitHub API, combined with the Spark Large Language Model. The system mainly focuses on:
- Analysis of inter-project relationships
- Developer interest preference profiling
- Discovery of potential collaboration opportunities
- Technology ecosystem development trend prediction

## Features
1. Multi-dimensional Relationship Analysis
   - User Relationships: Identify developers with similar tech stacks
   - Project Relationships: Explore project dependencies and technical connections
   - User-Project Relationships: Precise contribution opportunity recommendations

2. Intelligent Recommendation System
   - Project recommendations based on user tech stack
   - Contributor recommendations based on project characteristics
   - Multi-dimensional similarity calculation and matching

3. Large Model Analysis
   - Deep analysis using Spark Large Language Model
   - Relationship network interpretation
   - Personalized collaboration suggestion generation

4. Interactive Visualization
   - Force-directed graph for relationship network display
   - Node influence visualization
   - Dynamic association strength display
   - High-level interaction support

## Technical Architecture

### Frontend Stack
- Next.js 14 - React framework
- TypeScript - Type safety
- D3.js - Data visualization engine
- Tailwind CSS - Styling framework
- Radix UI - Component library

### Backend Stack
- FastAPI - Python Web framework
- OpenDigger API - Open source data analysis
- GitHub API - Data source
- Spark Large Language Model API - Intelligent analysis
- Python-dotenv - Environment configuration management

## Installation

### Requirements
- Node.js 18+
- Python 3.8+
- npm or yarn
- Git

### 1. GitHub Token Configuration
1. Visit GitHub settings page: https://github.com/settings/tokens
2. Generate new access token (classic)
3. Configure necessary permissions:
   - repo
   - read:user
   - user:email
4. Save the generated token

### 2. Project Setup
```bash
git clone https://github.com/Frank-whw/OpenChain.git
cd OpenChain
```

### 3. Frontend Deployment
```bash
# Install dependencies
npm install

# Start development server
npm run dev
```

### 4. Backend Deployment
```bash
# Enter backend directory
cd backend

# Install Python dependencies
pip install -r requirements.txt

# Configure environment variables
# Create .env file and add:
GITHUB_TOKEN=your_GitHub_Token

# Start backend service
uvicorn main:app --reload
```

### 5. Access System
Visit http://localhost:3000 in your browser

## Usage Guide

### Basic Functions
- Analysis type selection (user/repository)
- Search target input
- Visualization result viewing
- Node detail analysis

### Usage Examples
1. User->Repository Analysis
   ```
   Type: User
   Search: Repository
   Input: torvalds
   ```
![User-Repo Analysis](https://raw.githubusercontent.com/Frank-whw/img/main/blog/202412301616905.png)

Click on any node except the center node to generate large model analysis results
![AI Analysis](https://raw.githubusercontent.com/Frank-whw/img/main/blog/202412301617349.png)

2. User->User Analysis
   ```
   Type: User
   Search: User
   Input: Frank-whw
   ```
![User-User Analysis](https://raw.githubusercontent.com/Frank-whw/img/main/blog/202412301618504.png)

3. Repository->User Analysis
   ```
   Type: Repository
   Search: User
   Input: Frank-whw/OpenChain
   ```
![Repo-User Analysis](https://raw.githubusercontent.com/Frank-whw/img/main/blog/202412301621838.png)

4. Repository->Repository Analysis
   ```
   Type: Repository
   Search: Repository
   Input: Frank-whw/OpenChain
   ```
![Repo-Repo Analysis](https://raw.githubusercontent.com/Frank-whw/img/main/blog/202412301619762.png)

### Documentation System
The system provides comprehensive documentation including:
1. Algorithm Explanation
   - User similarity calculation methods
   - Repository similarity calculation methods
   - Recommendation process details
   - Node type classification rules

2. Interactive Features
   - Node hover effects with detailed information
   - Click interaction for AI analysis
   - Zoom and pan capabilities
   - Dynamic force-directed layout

3. Visual Elements
   - Color coding for different node types
   - Size variation based on importance
   - Connection strength visualization
   - Interactive tooltips

## Recommendation Algorithm

### Similarity Calculation
The system uses multi-dimensional similarity calculation methods:

#### User Similarity
- Language preference matching
- Tech stack overlap
- Project scale similarity
- Activity level comparison

#### Repository Similarity
- Programming language analysis
- Topic tag matching
- Project scale evaluation
- Functional description similarity

### Recommendation Process
1. Data Collection
   - GitHub API data retrieval
   - OpenDigger metrics analysis
   - User behavior data mining

2. Feature Extraction
   - Language preference analysis
   - Topic tag extraction
   - Activity level calculation
   - Scale evaluation

3. Similarity Calculation
   - Feature vector construction
   - Weighted similarity calculation
   - Normalization processing

4. Result Optimization
   - Similarity ranking
   - Activity level weighting
   - TOP-N filtering

## Development Plan
- [x] Basic framework setup
- [x] API system implementation
- [x] Visualization engine development
- [x] Large model integration
- [x] Recommendation algorithm optimization
- [x] Visualization enhancement
- [ ] User feedback system

## Contributing
Welcome to submit Issues and Pull Requests to participate in project improvement. Before submitting, please ensure:
1. Issue description is clear and complete
2. Pull Request includes detailed explanation
3. Code complies with project standards
4. Necessary test cases are provided

## License
This project is licensed under the MIT License