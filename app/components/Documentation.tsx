'use client';

import React from 'react';

const Documentation: React.FC = () => {
  return (
    <div className="flex flex-col w-full">
      <div className="flex min-h-[600px]">
        {/* 侧边栏 */}
        <div className="w-64 border-r border-gray-200 bg-white">
          <nav className="p-4">
            <div className="mb-6">
              <h3 className="text-sm font-semibold text-gray-600 uppercase tracking-wider mb-2">规模指数</h3>
              <a href="#user-scale" className="block py-2 px-4 text-gray-700 hover:bg-gray-100 hover:text-blue-600 rounded">用户规模指数</a>
              <a href="#repo-scale" className="block py-2 px-4 text-gray-700 hover:bg-gray-100 hover:text-blue-600 rounded">仓库规模指数</a>
            </div>
            
            <div className="mb-6">
              <h3 className="text-sm font-semibold text-gray-600 uppercase tracking-wider mb-2">相似度指标</h3>
              <a href="#user-user-similarity" className="block py-2 px-4 text-gray-700 hover:bg-gray-100 hover:text-blue-600 rounded">用户间相似度</a>
              <a href="#user-repo-similarity" className="block py-2 px-4 text-gray-700 hover:bg-gray-100 hover:text-blue-600 rounded">用户-仓库相似度</a>
            </div>
            
            <div className="mb-6">
              <h3 className="text-sm font-semibold text-gray-600 uppercase tracking-wider mb-2">推荐算法</h3>
              <a href="#recommendation-pool" className="block py-2 px-4 text-gray-700 hover:bg-gray-100 hover:text-blue-600 rounded">推荐池构建</a>
              <a href="#node-classification" className="block py-2 px-4 text-gray-700 hover:bg-gray-100 hover:text-blue-600 rounded">节点分类</a>
              <a href="#similarity-calculation" className="block py-2 px-4 text-gray-700 hover:bg-gray-100 hover:text-blue-600 rounded">相似度计算</a>
              <a href="#recommendation-implementation" className="block py-2 px-4 text-gray-700 hover:bg-gray-100 hover:text-blue-600 rounded">推荐实现</a>
            </div>
          </nav>
        </div>

        {/* 主要内容 */}
        <div className="flex-1 p-8 overflow-y-auto">
          <section id="user-scale" className="mb-12">
            <h2 className="text-3xl font-bold mb-6 pb-2 border-b-2 border-blue-500">用户规模指数计算</h2>
            
            <div className="mb-8">
              <h3 className="text-2xl font-semibold mb-4">输入变量</h3>
              <ul className="list-disc pl-6 space-y-2">
                <li>OpenRank值 (OR) ∈ [0,10]</li>
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
              <div className="bg-gray-50 p-4 rounded-lg font-mono text-sm">
                <pre>{`1. OpenRank归一化：
OR_score = min(1.0, OR/10)

2. 社交影响力：
SI = min(1.0, ln(f + 1)/ln(10000))

3. 最终得分：
Score = OR_score × 0.4 + SI × 0.3 + RQ × 0.15 + AS × 0.15`}</pre>
              </div>
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
          </section>

          {/* 用户间相似度部分 */}
          <section id="user-user-similarity" className="mb-12">
            <h2 className="text-3xl font-bold mb-6 pb-2 border-b-2 border-blue-500">用户间相似度指标</h2>
            
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
          </section>

          {/* 用户-仓库相似度部分 */}
          <section id="user-repo-similarity" className="mb-12">
            <h2 className="text-3xl font-bold mb-6 pb-2 border-b-2 border-blue-500">用户-仓库相似度指标</h2>
            
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
          </section>

          {/* 仓库规模指数部分 */}
          <section id="repo-scale" className="mb-12">
            <h2 className="text-3xl font-bold mb-6 pb-2 border-b-2 border-blue-500">仓库规模指数计算</h2>
            
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
                <pre>{`1. OpenRank值计算（如果可用）：
• 从OpenDigger获取仓库的OpenRank值
• 基础分数 = 20 + OpenRank × 20
• stars影响：min(1, ln(stars + 1) / ln(10000)) × 0.2
• forks影响：min(1, ln(forks + 1) / ln(1000)) × 0.1`}</pre>
              </div>
              
              <div className="bg-gray-50 p-4 rounded-lg font-mono text-sm">
                <pre>{`2. 传统指标计算（如果无OpenRank）：
• star_score = min(1, ln(stars + 1) / ln(10000))
• fork_score = min(1, ln(forks + 1) / ln(1000))
• watcher_score = min(1, ln(watchers + 1) / ln(1000))
• 基础分数 = 20 + (star_score × 0.5 + fork_score × 0.3 + watcher_score × 0.2) × 20`}</pre>
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
          </section>

          {/* 推荐池构建部分 */}
          <section id="recommendation-pool" className="mb-12">
            <h2 className="text-3xl font-bold mb-6 pb-2 border-b-2 border-blue-500">推荐池构建算法</h2>
            
            <div className="mb-8">
              <h3 className="text-2xl font-semibold mb-4">用户推荐池</h3>
              <div className="bg-gray-50 p-4 rounded-lg font-mono text-sm mb-4">
                <pre>{`池大小计算：
• base_size = 100  # 基础池大小
• scale_factor = (scale - 20) × 5  # 规模因子
• pool_size = base_size + scale_factor
• 最终大小范围：[100, 200]

动态调整：
• 初级用户 (scale < 25)：保持基础大小 100
• 中级用户 (25 ≤ scale < 30)：增加 25-50
• 高级用户 (30 ≤ scale < 35)：增加 50-75
• 专家用户 (scale ≥ 35)：增加 75-100`}</pre>
              </div>

              <h4 className="text-xl font-semibold mb-3">候选人来源</h4>
              <ul className="list-disc pl-6 space-y-2">
                <li>一级候选（权重：0.5）
                  <ul className="list-circle pl-6 mt-2 space-y-1">
                    <li>直接关联用户（followers和following）</li>
                    <li>已star仓库的贡献者</li>
                  </ul>
                </li>
                <li>二级扩展（权重：0.3）
                  <ul className="list-circle pl-6 mt-2 space-y-1">
                    <li>基于用户主要语言</li>
                    <li>基于用户主要主题</li>
                  </ul>
                </li>
                <li>三级补充（权重：0.2）
                  <ul className="list-circle pl-6 mt-2 space-y-1">
                    <li>从GitHub Trending获取活跃用户</li>
                  </ul>
                </li>
              </ul>
            </div>

            <div className="mb-8">
              <h3 className="text-2xl font-semibold mb-4">仓库推荐池</h3>
              <div className="bg-gray-50 p-4 rounded-lg font-mono text-sm mb-4">
                <pre>{`池大小计算：
• base_size = 60  # 基础池大小
• scale_factor = (scale - 20) × 2  # 规模因子
• pool_size = base_size + scale_factor
• 最终大小范围：[60, 100]

动态调整：
• 初级用户 (scale < 25)：保持基础大小 60
• 中级用户 (25 ≤ scale < 30)：增加 10-20
• 高级用户 (30 ≤ scale < 35)：增加 20-30
• 专家用户 (scale ≥ 35)：增加 30-40`}</pre>
              </div>

              <h4 className="text-xl font-semibold mb-3">候选仓库来源</h4>
              <ul className="list-disc pl-6 space-y-2">
                <li>一级候选（权重：0.5）
                  <ul className="list-circle pl-6 mt-2 space-y-1">
                    <li>与用户已star仓库相似的仓库</li>
                    <li>用户主要语言的热门仓库</li>
                  </ul>
                </li>
                <li>二级扩展（权重：0.3）
                  <ul className="list-circle pl-6 mt-2 space-y-1">
                    <li>从主题相关的热门仓库</li>
                  </ul>
                </li>
                <li>三级补充（权重：0.2）
                  <ul className="list-circle pl-6 mt-2 space-y-1">
                    <li>从GitHub Trending获取的热门仓库</li>
                  </ul>
                </li>
              </ul>
            </div>
          </section>

          {/* 相似度计算部分 */}
          <section id="similarity-calculation" className="mb-12">
            <h2 className="text-3xl font-bold mb-6 pb-2 border-b-2 border-blue-500">相似度计算算法</h2>
            
            <div className="mb-8">
              <h3 className="text-2xl font-semibold mb-4">用户间相似度计算</h3>
              <div className="bg-gray-50 p-4 rounded-lg font-mono text-sm mb-4">
                <pre>{`1. 语言偏好相似度计算：
• 获取所有语言列表 L = {l₁, ..., lₙ}
• 计算每种语言的代码量占比
• 构建归一化向量 v = (p₁, ..., pₙ)
• 计算两向量的余弦相似度

2. 主题兴趣相似度计算：
• 收集两用户的所有仓库主题
• 构建主题集合 T₁, T₂
• 计算Jaccard系数：|T₁ ∩ T₂| / |T₁ ∪ T₂|

3. 活跃度相似度计算：
• 对followers、following、repos应用ln(x+1)转换
• 使用不同的归一化基数(10⁴,10³,10²)
• 应用权重(0.4,0.3,0.3)计算差异度
• 转换为相似度(1-差异度)`}</pre>
              </div>
            </div>

            <div className="mb-8">
              <h3 className="text-2xl font-semibold mb-4">用户-仓库相似度计算</h3>
              <div className="bg-gray-50 p-4 rounded-lg font-mono text-sm mb-4">
                <pre>{`1. 语言匹配度计算：
• 统计用户所有仓库的语言使用
• 计算每种语言的代码量占比
• 获取仓库主要语言
• 查找用户对应语言的使用比例

2. 主题匹配度计算：
• 收集用户的兴趣主题集合
• 获取仓库的主题标签集合
• 计算Jaccard相似度

3. 规模时效性计算：
• 对star数和fork数做对数转换
• 应用权重(0.7,0.3)
• 根据时效性应用乘数因子
  - 1.2(活跃)或0.8(不活跃)`}</pre>
              </div>
            </div>
          </section>

          {/* 推荐实现部分 */}
          <section id="recommendation-implementation" className="mb-12">
            <h2 className="text-3xl font-bold mb-6 pb-2 border-b-2 border-blue-500">推荐算法实现</h2>
            
            <div className="mb-8">
              <h3 className="text-2xl font-semibold mb-4">用户推荐实现</h3>
              <div className="bg-gray-50 p-4 rounded-lg font-mono text-sm mb-4">
                <pre>{`1. 推荐池构建：
• N = base_size + scale_factor
• P = P₁ ∪ P₂ ∪ P₃
  - P₁ (50%): 直接关联用户
  - P₂ (30%): 主题语言相关
  - P₃ (20%): 趋势补充

2. 相似度计算：
• 对每个候选用户计算相似度
• 按相似度降序排序
• 选取前N个用户

3. 节点分类：
• 根据scale分配到对应层级
• 分配节点类型
  - 核心节点：P₁中相似度最高的用户
  - 扩展节点：P₂中的高相似度用户
  - 探索节点：P₃中的新兴用户`}</pre>
              </div>
            </div>

            <div className="mb-8">
              <h3 className="text-2xl font-semibold mb-4">仓库推荐实现</h3>
              <div className="bg-gray-50 p-4 rounded-lg font-mono text-sm mb-4">
                <pre>{`1. 推荐池构建：
• N = base_size + scale_factor
• P = P₁ ∪ P₂ ∪ P₃
  - P₁ (50%): 相似仓库和语言热门
  - P₂ (30%): 主题相关
  - P₃ (20%): 趋势补充

2. 相似度计算：
• 对每个候选仓库计算相似度
• 按相似度降序排序
• 选取前N个仓库

3. 节点分类：
• 根据scale分配到对应层级
• 分配节点类型
  - 核心项目：高度相关的成熟项目
  - 热门项目：当前活跃的热门仓库
  - 新兴项目：近期快速增长的项目`}</pre>
              </div>
            </div>

            <div className="bg-blue-50 border-l-4 border-blue-500 p-4 rounded-r-lg mb-8">
              <h4 className="text-blue-600 font-semibold mb-2">结果优化</h4>
              <ul className="list-disc pl-4 space-y-1 text-blue-800">
                <li>多样性保证：每个层级节点数量平衡</li>
                <li>动态调整：根据用户反馈调整权重</li>
                <li>时效性优化：优先推荐活跃项目</li>
              </ul>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
};

export default Documentation; 