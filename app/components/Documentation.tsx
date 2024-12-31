'use client';

import React, { useState, useEffect } from 'react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { tomorrow } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { Search, ChevronDown, ChevronUp } from 'lucide-react';
import SidebarSection from '@/app/components/components/SidebarSection';
import ContentSection from '@/app/components/components/ContentSection';
import Tooltip from '@/app/components/components/Tooltip';

const Documentation: React.FC = () => {
  const [searchTerm, setSearchTerm] = useState('');
  const [expandedSections, setExpandedSections] = useState<{ [key: string]: boolean }>({});
  const [activeSection, setActiveSection] = useState('');

  useEffect(() => {
    const handleScroll = () => {
      const sections = document.querySelectorAll('section[id]');
      let currentActiveSection = '';
      sections.forEach((section) => {
        const sectionTop = (section as HTMLElement).offsetTop;
        const sectionHeight = (section as HTMLElement).clientHeight;
        if (window.pageYOffset >= sectionTop - 60 && window.pageYOffset < sectionTop + sectionHeight - 60) {
          currentActiveSection = section.id;
        }
      });
      setActiveSection(currentActiveSection);
    };

    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const toggleSection = (sectionId: string) => {
    setExpandedSections(prev => ({ ...prev, [sectionId]: !prev[sectionId] }));
  };

  const scrollToSection = (sectionId: string) => {
    const section = document.getElementById(sectionId);
    if (section) {
      section.scrollIntoView({ behavior: 'smooth' });
    }
  };

  const filterContent = (content: string) => {
    return content.toLowerCase().includes(searchTerm.toLowerCase());
  };

  return (
    <div className="flex flex-col w-full">
      <div className="flex min-h-[600px]">
        {/* 侧边栏 */}
        <div className="w-64 border-r border-gray-200 bg-white sticky top-0 h-screen overflow-y-auto">
          <nav className="p-4">
            <div className="mb-4">
              <div className="relative">
                <input
                  type="text"
                  placeholder="搜索..."
                  className="w-full px-4 py-2 border rounded-md"
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                />
                <Search className="absolute right-3 top-2.5 text-gray-400" size={20} />
              </div>
            </div>
            <SidebarSection
              title="规模指数"
              items={[
                { id: 'user-scale', label: '用户规模指数' },
                { id: 'repo-scale', label: '仓库规模指数' },
              ]}
              activeSection={activeSection}
              scrollToSection={scrollToSection}
              filterContent={filterContent}
            />
            <SidebarSection
              title="相似度指标"
              items={[
                { id: 'user-user-similarity', label: '用户间相似度' },
                { id: 'user-repo-similarity', label: '用户-仓库相似度' },
                { id: 'repo-repo-similarity', label: '仓库间相似度' },
              ]}
              activeSection={activeSection}
              scrollToSection={scrollToSection}
              filterContent={filterContent}
            />
            <SidebarSection
              title="推荐算法"
              items={[
                { id: 'user-recommendation', label: '用户推荐算法' },
                { id: 'repo-recommendation', label: '仓库推荐算法' },
              ]}
              activeSection={activeSection}
              scrollToSection={scrollToSection}
              filterContent={filterContent}
            />
          </nav>
        </div>

        {/* 主要内容 */}
        <div className="flex-1 p-8 overflow-y-auto">
          <ContentSection
            id="user-scale"
            title="用户规模指数计算"
            expanded={expandedSections['user-scale']}
            toggleSection={() => toggleSection('user-scale')}
            filterContent={filterContent}
          >
            {/* 用户规模指数计算内容 */}
            <div className="mb-8">
              <h3 className="text-2xl font-semibold mb-4">输入变量</h3>
              <ul className="list-disc pl-6 space-y-2">
                <li>
                  <Tooltip content="OpenRank是衡量开发者影响力的指标">
                    <span className="underline cursor-help">OpenRank值 (OR)</span>
                  </Tooltip> ∈ [0,10]
                </li>
                <li>
                  用户信息 (U)
                  <ul className="list-circle pl-6 mt-2 space-y-1">
                    <li>followers数量 (f)</li>
                    <li>public_repos数量 (R)</li>
                  </ul>
                </li>
              </ul>
            </div>

            <div className="mb-8">
              <h3 className="text-2xl font-semibold mb-4">计算路径</h3>
              <SyntaxHighlighter language="python" style={tomorrow}>
                {`1. OpenRank归一化：
OR_score = min(1.0, OR/10)

2. 社交影响力：
SI = min(1.0, ln(f + 1)/ln(10000))

3. 最终得分：
Score = OR_score × 0.4 + SI × 0.3 + RQ × 0.15 + AS × 0.15`}
              </SyntaxHighlighter>
            </div>

            <div className="mb-8">
              <h3 className="text-2xl font-semibold mb-4">分级说明</h3>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">分数范围</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">级别</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">特征</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    <tr>
                      <td className="px-6 py-4 whitespace-nowrap">[20,25)</td>
                      <td className="px-6 py-4 whitespace-nowrap">初级开发者</td>
                      <td className="px-6 py-4">{"OpenRank < 0.25 或 followers < 100"}</td>
                    </tr>
                    <tr>
                      <td className="px-6 py-4 whitespace-nowrap">[25,30)</td>
                      <td className="px-6 py-4 whitespace-nowrap">中级开发者</td>
                      <td className="px-6 py-4">{"0.25 ≤ OpenRank < 0.5 或 100 ≤ followers < 1000"}</td>
                    </tr>
                    <tr>
                      <td className="px-6 py-4 whitespace-nowrap">[30,35)</td>
                      <td className="px-6 py-4 whitespace-nowrap">高级开发者</td>
                      <td className="px-6 py-4">{"0.5 ≤ OpenRank < 0.75 或 1000 ≤ followers < 5000"}</td>
                    </tr>
                    <tr>
                      <td className="px-6 py-4 whitespace-nowrap">[35,40]</td>
                      <td className="px-6 py-4 whitespace-nowrap">专家级开发者</td>
                      <td className="px-6 py-4">{"OpenRank ≥ 0.75 或 followers ≥ 5000"}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </ContentSection>
          <ContentSection
            id="repo-scale"
            title="仓库规模指数计算"
            expanded={expandedSections['repo-scale']}
            toggleSection={() => toggleSection('repo-scale')}
            filterContent={filterContent}
          >
            <div className="mb-8">
              <h3 className="text-2xl font-semibold mb-4">基础指标</h3>
              <ul className="list-disc pl-6 space-y-2">
                <li>stars: 星标数量</li>
                <li>forks: 复刻数量</li>
                <li>watchers: 关注者数量</li>
              </ul>
            </div>

            <div className="mb-8">
              <h3 className="text-2xl font-semibold mb-4">计算步骤</h3>
              <div className="bg-gray-50 p-4 rounded-lg font-mono text-sm mb-4">
                <SyntaxHighlighter language="python" style={tomorrow}>
                  {`1. OpenRank值计算（如果可用）：
          • 从OpenDigger获取仓库的OpenRank值
          • 基础分数 = 20 + OpenRank × 20
          • stars影响：min(1, ln(stars + 1) / ln(10000)) × 0.2
          • forks影响：min(1, ln(forks + 1) / ln(1000)) × 0.1`}
                </SyntaxHighlighter>
              </div>

              <div className="bg-gray-50 p-4 rounded-lg font-mono text-sm">
                <SyntaxHighlighter language="python" style={tomorrow}>
                  {`2. 传统指标计算（如果无OpenRank）：
          • star_score = min(1, ln(stars + 1) / ln(10000))
          • fork_score = min(1, ln(forks + 1) / ln(1000))
          • watcher_score = min(1, ln(watchers + 1) / ln(1000))
          • 基础分数 = 20 + (star_score × 0.5 + fork_score × 0.3 + watcher_score × 0.2) × 20`}
                </SyntaxHighlighter>
              </div>
            </div>

            <div className="mb-8">
              <h3 className="text-2xl font-semibold mb-4">活跃度调整</h3>
              <ul className="list-disc pl-6 space-y-2">
                <li>检查最近更新时间</li>
                <li>如果在2023-2024年活跃：系数 = 1.0</li>
                <li>否则：系数 = 0.5</li>
              </ul>
            </div>

            <div className="mb-8">
              <h3 className="text-2xl font-semibold mb-4">指标含义</h3>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">分数范围</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">项目规模</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    <tr>
                      <td className="px-6 py-4 whitespace-nowrap">20-25</td>
                      <td className="px-6 py-4 whitespace-nowrap">小型项目</td>
                    </tr>
                    <tr>
                      <td className="px-6 py-4 whitespace-nowrap">26-30</td>
                      <td className="px-6 py-4 whitespace-nowrap">中型项目</td>
                    </tr>
                    <tr>
                      <td className="px-6 py-4 whitespace-nowrap">31-35</td>
                      <td className="px-6 py-4 whitespace-nowrap">大型项目</td>
                    </tr>
                    <tr>
                      <td className="px-6 py-4 whitespace-nowrap">36-40</td>
                      <td className="px-6 py-4 whitespace-nowrap">超大型项目</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </ContentSection>
          <ContentSection
            id="user-user-similarity"
            title="用户间相似度指标"
            expanded={expandedSections['user-user-similarity']}
            toggleSection={() => toggleSection('user-user-similarity')}
            filterContent={filterContent}
          >
            <div className="mb-8">
              <h3 className="text-2xl font-semibold mb-4">指标构成</h3>
              <ul className="list-disc pl-6 space-y-2">
                <li>语言偏好相似度 (30%)
                  <ul className="list-circle pl-6 mt-2 space-y-1">
                    <li>衡量两用户在编程语言使用上的相似程度</li>
                    <li>考虑各语言的代码量占比</li>
                  </ul>
                </li>
                <li>主题兴趣相似度 (30%)
                  <ul className="list-circle pl-6 mt-2 space-y-1">
                    <li>衡量两用户在项目主题上的重叠度</li>
                    <li>基于仓库标签的集合运算</li>
                  </ul>
                </li>
                <li>活跃度相似度 (40%)
                  <ul className="list-circle pl-6 mt-2 space-y-1">
                    <li>衡量两用户在GitHub活跃程度的接近度</li>
                    <li>考虑followers、following、repos三个维度</li>
                  </ul>
                </li>
              </ul>
            </div>

            <div className="bg-blue-50 border-l-4 border-blue-500 p-4 rounded-r-lg mb-8">
              <h4 className="text-blue-600 font-semibold mb-2">注意事项</h4>
              <ul className="list-disc pl-4 space-y-1 text-blue-800">
                <li>所有对数运算均使用自然对数(ln)</li>
                <li>活跃度基于最近一年的更新情况</li>
                <li>相似度计算结果在[0,1]区间内</li>
              </ul>
            </div>
          </ContentSection>

          <ContentSection
            id="user-repo-similarity"
            title="用户-仓库相似度指标"
            expanded={expandedSections['user-repo-similarity']}
            toggleSection={() => toggleSection('user-repo-similarity')}
            filterContent={filterContent}
          >
            <div className="mb-8">
              <h3 className="text-2xl font-semibold mb-4">指标构成</h3>
              <ul className="list-disc pl-6 space-y-2">
                <li>语言匹配度 (40%)
                  <ul className="list-circle pl-6 mt-2 space-y-1">
                    <li>衡量用户对仓库主语言的熟悉程度</li>
                    <li>基于用户的语言使用统计</li>
                    <li>值域：[0,1]，1表示完全匹配</li>
                  </ul>
                </li>
                <li>主题匹配度 (40%)
                  <ul className="list-circle pl-6 mt-2 space-y-1">
                    <li>衡量用户兴趣与仓库主题的重合度</li>
                    <li>基于主题标签的集合运算</li>
                    <li>值域：[0,1]，1表示完全重合</li>
                  </ul>
                </li>
                <li>规模时效性 (20%)
                  <ul className="list-circle pl-6 mt-2 space-y-1">
                    <li>衡量仓库的受欢迎程度和活跃度</li>
                    <li>考虑star数、fork数和更新时间</li>
                    <li>值域：[0,1]，1表示最受欢迎且活跃</li>
                  </ul>
                </li>
              </ul>
            </div>

            <div className="bg-blue-50 border-l-4 border-blue-500 p-4 rounded-r-lg mb-8">
              <h4 className="text-blue-600 font-semibold mb-2">指标特性</h4>
              <ul className="list-disc pl-4 space-y-1 text-blue-800">
                <li>非对称性：用户对仓库的相似度不等于反向相似度</li>
                <li>归一化：最终得分在[0,1]区间</li>
                <li>时效性：考虑仓库的活跃状态</li>
              </ul>
            </div>

            <div className="mb-8">
              <h3 className="text-2xl font-semibold mb-4">应用场景</h3>
              <ul className="list-disc pl-6 space-y-2">
                <li>项目推荐：推荐适合的项目</li>
                <li>贡献建议：推荐可贡献的仓库</li>
                <li>学习路径：推荐学习资源</li>
              </ul>
            </div>
          </ContentSection>

          <ContentSection
            id="repo-repo-similarity"
            title="仓库间相似度指标"
            expanded={expandedSections['repo-repo-similarity']}
            toggleSection={() => toggleSection('repo-repo-similarity')}
            filterContent={filterContent}
          >
            <div className="mb-8">
              <h3 className="text-2xl font-semibold mb-4">指标构成</h3>
              <ul className="list-disc pl-6 space-y-2">
                <li>
                  <Tooltip content="比较两个仓库的主要开发语言，判断技术栈的相似程度">
                    语言相似度 (30%)
                  </Tooltip>
                  <ul className="list-circle pl-6 mt-2 space-y-1">
                    <li>衡量仓库主要开发语言的匹配程度</li>
                    <li>基于语言使用统计的相似度计算</li>
                    <li>值域：[0,1]，1表示完全匹配</li>
                  </ul>
                </li>
                <li>
                  <Tooltip content="分析仓库的主题标签重叠情况，反映功能和领域的相似性">
                    主题相似度 (40%)
                  </Tooltip>
                  <ul className="list-circle pl-6 mt-2 space-y-1">
                    <li>衡量仓库主题标签的重叠度</li>
                    <li>基于主题标签的集合运算</li>
                    <li>值域：[0,1]，1表示完全重合</li>
                  </ul>
                </li>
                <li>
                  <Tooltip content="比较仓库的规模大小，包括代码量、star数、fork数等指标">
                    规模相似度 (30%)
                  </Tooltip>
                  <ul className="list-circle pl-6 mt-2 space-y-1">
                    <li>衡量仓库规模大小的接近程度</li>
                    <li>考虑代码量、star数、fork数等维度</li>
                    <li>值域：[0,1]，1表示规模最接近</li>
                  </ul>
                </li>
              </ul>
            </div>

            <div className="bg-blue-50 border-l-4 border-blue-500 p-4 rounded-r-lg mb-8">
              <h4 className="text-blue-600 font-semibold mb-2">指标特性</h4>
              <ul className="list-disc pl-4 space-y-1 text-blue-800">
                <li>
                  <Tooltip content="A仓库对B仓库的相似度等于B仓库对A仓库的相似度">
                    对称性：相似度计算具有对称性
                  </Tooltip>
                </li>
                <li>
                  <Tooltip content="所有相似度计算结果都会被归一化到0到1之间">
                    归一化：最终得分在[0,1]区间
                  </Tooltip>
                </li>
              </ul>
            </div>

            <div className="mb-8">
              <h3 className="text-2xl font-semibold mb-4">应用场景</h3>
              <ul className="list-disc pl-6 space-y-2">
                <li>
                  <Tooltip content="帮助用户发现与当前关注仓库相似的其他项目">
                    相似项目发现
                  </Tooltip>
                </li>
                <li>
                  <Tooltip content="辅助开发者在相似技术栈间进行迁移和学习">
                    技术栈迁移
                  </Tooltip>
                </li>
                <li>
                  <Tooltip content="发现和分析同领域的竞争项目">
                    竞品分析
                  </Tooltip>
                </li>
              </ul>
            </div>
          </ContentSection>

          <ContentSection
            id="user-recommendation"
            title="用户推荐算法实现"
            expanded={expandedSections['user-recommendation']}
            toggleSection={() => toggleSection('user-recommendation')}
            filterContent={filterContent}
          >
            <div className="mb-8">
              <h3 className="text-2xl font-semibold mb-4">推荐池构建</h3>
              <div className="bg-gray-50 p-4 rounded-lg font-mono text-sm mb-4">
                <SyntaxHighlighter language="python" style={tomorrow}>
                  {`规模计算：
• N = base_size + scale_factor
  - base_size = 60
  - scale_factor = (scale - 20) × 2
  - N ∈ [60, 100]

候选集构建：
• P = P₁ ∪ P₂ ∪ P₃
  - P₁ (50%)：相似用户
    · S = get_similar_users(user.followers)
    · L = get_top_users(user.languages)
    · P₁ = S ∪ L
  - P₂ (30%)：兴趣相关
    · T = get_user_topics(user)
    · P₂ = search_users(topics=T)
  - P₃ (20%)：趋势补充
    · P₃ = get_trending_users()`}
                </SyntaxHighlighter>
              </div>
            </div>

            <div className="mb-8">
              <h3 className="text-2xl font-semibold mb-4">相似度计算</h3>
              <div className="bg-gray-50 p-4 rounded-lg font-mono text-sm mb-4">
                <SyntaxHighlighter language="python" style={tomorrow}>
                  {`对于每个候选用户 u ∈ P：
• sim(user, u) = compute_similarity(user, u)
• 按相似度降序排序
• 选取前 N 个用户作为推荐集 R`}
                </SyntaxHighlighter>
              </div>
            </div>

            <div className="mb-8">
              <h3 className="text-2xl font-semibold mb-4">节点分类</h3>
              <ul className="list-disc pl-6 space-y-2">
                <li>规模分类
                  <ul className="list-circle pl-6 mt-2 space-y-1">
                    <li>scale = compute_user_scale(r)</li>
                    <li>根据 scale 分配到对应层级</li>
                  </ul>
                </li>
                <li>类型分配
                  <ul className="list-circle pl-6 mt-2 space-y-1">
                    <li>核心节点：P₁ 中相似度最高的用户</li>
                    <li>扩展节点：P₂ 中的高相似度用户</li>
                    <li>探索节点：P₃ 中的新兴用户</li>
                  </ul>
                </li>
              </ul>
            </div>

            <div className="mb-8">
              <h3 className="text-2xl font-semibold mb-4">结果优化</h3>
              <ul className="list-disc pl-6 space-y-2">
                <li>多样性保证
                  <ul className="list-circle pl-6 mt-2 space-y-1">
                    <li>每个层级节点数量平衡</li>
                    <li>不同来源节点混合</li>
                    <li>随机打乱同类节点顺序</li>
                  </ul>
                </li>
                <li>动态调整
                  <ul className="list-circle pl-6 mt-2 space-y-1">
                    <li>根据用户反馈调整权重</li>
                    <li>更新候选池组成比例</li>
                    <li>优化节点分布策略</li>
                  </ul>
                </li>
              </ul>
            </div>
          </ContentSection>

          <ContentSection
            id="repo-recommendation"
            title="仓库推荐算法实现"
            expanded={expandedSections['repo-recommendation']}
            toggleSection={() => toggleSection('repo-recommendation')}
            filterContent={filterContent}
          >
            <div className="mb-8">
              <h3 className="text-2xl font-semibold mb-4">推荐池构建</h3>
              <div className="bg-gray-50 p-4 rounded-lg font-mono text-sm mb-4">
                <SyntaxHighlighter language="python" style={tomorrow}>
                  {`规模计算：
• N = base_size + scale_factor
  - base_size = 60
  - scale_factor = (scale - 20) × 2
  - N ∈ [60, 100]

候选集构建：
• P = P₁ ∪ P₂ ∪ P₃
  - P₁ (50%)：相似仓库
    · S = get_similar_repos(user.starred_repos)
    · L = get_top_repos(user.languages)
    · P₁ = S ∪ L
  - P₂ (30%)：主题相关
    · T = get_user_topics(user)
    · P₂ = search_repos(topics=T)
  - P₃ (20%)：趋势补充
    · P₃ = get_trending_repos()`}
                </SyntaxHighlighter>
              </div>
            </div>

            <div className="mb-8">
              <h3 className="text-2xl font-semibold mb-4">相似度计算</h3>
              <div className="bg-gray-50 p-4 rounded-lg font-mono text-sm mb-4">
                <SyntaxHighlighter language="python" style={tomorrow}>
                  {`对于每个候选仓库 r ∈ P：
• sim(user, r) = compute_repo_similarity(user, r)
• 按相似度降序排序
• 选取前 N 个仓库作为推荐集 R`}
                </SyntaxHighlighter>
              </div>
            </div>

            <div className="mb-8">
              <h3 className="text-2xl font-semibold mb-4">节点分类</h3>
              <ul className="list-disc pl-6 space-y-2">
                <li>规模分类
                  <ul className="list-circle pl-6 mt-2 space-y-1">
                    <li>scale = compute_repo_scale(r)</li>
                    <li>根据 scale 分配到对应层级</li>
                  </ul>
                </li>
                <li>类型分配
                  <ul className="list-circle pl-6 mt-2 space-y-1">
                    <li>核心项目：与用户高度相关的成熟项目</li>
                    <li>热门项目：当前活跃的热门仓库</li>
                    <li>新兴项目：近期快速增长的项目</li>
                  </ul>
                </li>
              </ul>
            </div>

            <div className="mb-8">
              <h3 className="text-2xl font-semibold mb-4">结果优化</h3>
              <ul className="list-disc pl-6 space-y-2">
                <li>多样性保证
                  <ul className="list-circle pl-6 mt-2 space-y-1">
                    <li>语言分布均衡</li>
                    <li>主题覆盖广泛</li>
                    <li>规模分布合理</li>
                  </ul>
                </li>
                <li>时效性优化
                  <ul className="list-circle pl-6 mt-2 space-y-1">
                    <li>优先推荐活跃项目</li>
                    <li>考虑更新频率</li>
                    <li>关注社区活跃度</li>
                  </ul>
                </li>
              </ul>
            </div>
          </ContentSection>
        </div>
      </div>
    </div>
  );
};

export default Documentation;

