from typing import Dict, Optional
import logging

# 配置日志
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# 定义算法解释内容
explanations = {
    # 规模指数解释
    'scale': {
        'user': """用户规模指数计算方法：

1. 输入变量：
   • OR ∈ [0,10]：OpenRank值（从OpenDigger获取）
   • U：用户信息
     - f：followers数量
     - R：public_repos数量
   • R = {r₁, r₂, ..., rₙ}：用户的仓库集合
     其中每个仓库 rᵢ 包含：
     - sᵢ：stargazers_count
     - fᵢ：forks_count
     - tᵢ：updated_at

2. 基于OpenRank的计算路径：

   a) OpenRank归一化：
      OR_score = min(1.0, OR/10)

   b) 社交影响力：
      SI = min(1.0, ln(f + 1)/ln(10000))

   c) 仓库质量计算：
      若 |R| > 0:
         s̄ = (∑sᵢ)/|R|  # 平均star数
         f̄ = (∑fᵢ)/|R|  # 平均fork数
         RQ = min(1.0, (ln(s̄ + 1)/ln(1000) + ln(f̄ + 1)/ln(500))/2)
      否则:
         RQ = 0

   d) 活跃度计算：
      R_recent = {r ∈ R : r.updated_at在近一年内}
      AR = |R_recent|/|R| if |R| > 0 else 0
      AS = min(1.0, ln(|R| + 1)/ln(100)) × AR

   e) 最终得分：
      Score = OR_score × 0.4 + SI × 0.3 + RQ × 0.15 + AS × 0.15

3. 传统计算路径（无OpenRank时）：

   a) 社交影响力 (40%)：
      SI = min(1.0, ln(f + 1)/ln(10000))

   b) 仓库质量 (40%)：
      若 |R| > 0:
         s̄ = (∑sᵢ)/|R|
         f̄ = (∑fᵢ)/|R|
         RQ = min(1.0, (ln(s̄ + 1)/ln(1000) + ln(f̄ + 1)/ln(500))/2)
      否则:
         RQ = 0

   c) 活跃度 (20%)：
      AR = |R_recent|/|R| if |R| > 0 else 0
      AS = min(1.0, ln(|R| + 1)/ln(100)) × AR

   d) 最终得分：
      Score = SI × 0.4 + RQ × 0.4 + AS × 0.2

4. 规模指数映射：
   Scale = 20 + Score × 20
   返回值范围：[20, 40]

5. 分级说明：
   • [20,25): 初级开发者
     - OpenRank < 0.25 或 followers < 100
     - 平均star/fork较少
     - 年度活跃仓库比例 < 30%

   • [25,30): 中级开发者
     - 0.25 ≤ OpenRank < 0.5 或 100 ≤ followers < 1000
     - 平均star/fork中等
     - 年度活跃仓库比例 30%-60%

   • [30,35): 高级开发者
     - 0.5 ≤ OpenRank < 0.75 或 1000 ≤ followers < 5000
     - 平均star/fork较高
     - 年度活跃仓库比例 60%-80%

   • [35,40]: 专家级开发者
     - OpenRank ≥ 0.75 或 followers ≥ 5000
     - 平均star/fork很高
     - 年度活跃仓库比例 > 80%

注：
1. 所有对数运算均使用自然对数(ln)
2. 活跃度基于最近一年的仓库更新情况
3. 若获取信息失败，返回基础分数20""",
        
        'repo': """仓库规模指数计算方法：

1. 基础指标：
   - stars: 星标数量
   - forks: 复刻数量
   - watchers: 关注者数量

2. 计算步骤：

   a) OpenRank值计算（如果可用）：
      • 从OpenDigger获取仓库的OpenRank值
      • 基础分数 = 20 + OpenRank × 20
      
      • stars影响：min(1, ln(stars + 1) / ln(10000)) × 0.2
      • forks影响：min(1, ln(forks + 1) / ln(1000)) × 0.1

   b) 传统指标计算（如果无OpenRank）：
      • star_score = min(1, ln(stars + 1) / ln(10000))
      • fork_score = min(1, ln(forks + 1) / ln(1000))
      • watcher_score = min(1, ln(watchers + 1) / ln(1000))
      
      • 基础分数 = 20 + (star_score × 0.5 + fork_score × 0.3 + watcher_score × 0.2) × 20

3. 活跃度调整：
   • 检查最近更新时间
   • 如果在2023-2024年活跃：系数 = 1.0
   • 否则：系数 = 0.5

4. 最终计算：
   scale = min(max(基础分数 × 活跃度系数, 20), 40)

5. 指标含义：
   - 20-25: 小型项目
   - 26-30: 中型项目
   - 31-35: 大型项目
   - 36-40: 超大型项目"""
    },
    
    # 相似度指标定义
    'similarity': {
        'user-user': """用户间相似度指标定义：

1. 指标构成：
   • 语言偏好相似度 (30%)
     - 衡量两用户在编程语言使用上的相似程度
     - 考虑各语言的代码量占比
     - 值域：[0,1]，1表示完全相同

   • 主题兴趣相似度 (30%)
     - 衡量两用户在项目主题上的重叠度
     - 基于仓库标签的集合运算
     - 值域：[0,1]，1表示完全重叠

   • 活跃度相似度 (40%)
     - 衡量两用户在GitHub活跃程度的接近度
     - 考虑followers、following、repos三个维度
     - 值域：[0,1]，1表示活跃度完全接近

2. 指标特性：
   • 对称性：A对B的相似度等于B对A的相似度
   • 归一化：最终得分在[0,1]区间
   • 可解释：各分量有明确的现实含义

3. 应用场景：
   • 用户推荐：寻找相似用户
   • 社群发现：识别相似兴趣群体
   • 协作建议：推荐潜在的合作者""",

        'user-repo': """用户-仓库相似度指标定义：

1. 指标构成：
   • 语言匹配度 (40%)
     - 衡量用户对仓库主语言的熟悉程度
     - 基于用户的语言使用统计
     - 值域：[0,1]，1表示完全匹配

   • 主题匹配度 (40%)
     - 衡量用户兴趣与仓库主题的重合度
     - 基于主题标签的集合运算
     - 值域：[0,1]，1表示完全重合

   • 规模时效性 (20%)
     - 衡量仓库的受欢迎程度和活跃度
     - 考虑star数、fork数和更新时间
     - 值域：[0,1]，1表示最受欢迎且活跃

2. 指标特性：
   • 非对称性：用户对仓库的相似度不等于反向相似度
   • 归一化：最终得分在[0,1]区间
   • 时效性：考虑仓库的活跃状态

3. 应用场景：
   • 项目推荐：推荐适合的项目
   • 贡献建议：推荐可贡献的仓库
   • 学习路径：推荐学习资源"""
    },
    
    # 推荐池算法
    'pool': {
        'user-user': """用户推荐池构建算法：

1. 输入变量：
   • U：目标用户信息
     - f：followers数量
     - F：following集合
     - R：仓库集合
   • scale ∈ [20,40]：用户规模指数

2. 池大小计算：
   a) 基础配置：
      • base_size = 100  # 基础池大小
      • scale_factor = (scale - 20) × 5  # 规模因子
      • pool_size = base_size + scale_factor
      • 最终大小范围：[100, 200]

   b) 动态调整：
      • 初级用户 (scale < 25)：保持基础大小 100
      • 中级用户 (25 ≤ scale < 30)：增加 25-50
      • 高级用户 (30 ≤ scale < 35)：增加 50-75
      • 专家用户 (scale ≥ 35)：增加 75-100

3. 候选人来源：
   a) 一级候选（权重：0.5）：
      • F_direct = U.followers ∪ U.following
      • C_repos = {贡献者 from r for r in U.starred_repos}
      • 初始池 P₁ = F_direct ∪ C_repos

   b) 二级扩展（权重：0.3）：
      • 获取用户主要语言 L = {l₁, l₂, ..., lₖ}
      • 获取主要主题 T = {t₁, t₂, ..., tₘ}
      • P₂ = {活跃用户 from GitHub API where 语言 ∈ L or 主题 ∈ T}

   c) 三级补充（权重：0.2）：
      • P₃ = {从 GitHub Trending 获取的活跃用户}

4. 池大小控制策略：
   • 优先从 P₁ 选取 50% 的名额
   • 从 P₂ 选取 30% 的名额
   • 从 P₃ 补充剩余名额
   • 若某级源不足，名额按比例分配给其他来源""",
        
        'user-repo': """仓库推荐池构建算法：

1. 输入变量：
   • U：用户信息
     - L：语言使用统计
     - T：感兴趣的主题集合
     - S：已star的仓库集合
   • scale ∈ [20,40]：用户规模指数

2. 池大小计算：
   a) 基础配置：
      • base_size = 60  # 基础池大小
      • scale_factor = (scale - 20) × 2  # 规模因子
      • pool_size = base_size + scale_factor
      • 最终大小范围：[60, 100]

   b) 动态调整：
      • 初级用户 (scale < 25)：保持基础大小 60
      • 中级用户 (25 ≤ scale < 30)：增加 10-20
      • 高级用户 (30 ≤ scale < 35)：增加 20-30
      • 专家用户 (scale ≥ 35)：增加 30-40

3. 候选仓库来源：
   a) 一级候选（权重：0.5）：
      • R_similar = {与用户已star仓库相似的仓库}
      • R_lang = {用户主要语言的热门仓库}
      • 初始池 P₁ = R_similar ∪ R_lang

   b) 二级扩展（权重：0.3）：
      • 获取用户主题 T = {t₁, t₂, ..., tₘ}
      • P₂ = {从主题相关的热门仓库}

   c) 三级补充（权重：0.2）：
      • P₃ = {从 GitHub Trending 获取的热门仓库}

4. 池大小控制策略：
   • 优先从 P₁ 选取 50% 的名额
   • 从 P₂ 选取 30% 的名额
   • 从 P₃ 补充剩余名额
   • 对于高规模用户，增加新兴仓库的比例

注：
1. 规模因子基于用户的活跃度和影响力
2. 池大小随用户规模增长而增加
3. 高规模用户获得更大更多样的推荐池"""
    },
    
    # 节点分类算法
    'node': {
        'user-user': """用户节点分类算法：

1. 输入变量：
   • users：推荐用户列表
   • similarities：用户相似度列表
   • user_scale：目标用户的规模指数

2. 节点类型定义：
   a) Mentor节点 (6-10个)：
      • 条件：scale ≥ 33
      • 特点：经验丰富的高级开发者
      • 目的：提供指导和学习机会

   b) Peer节点 (9-15个)：
      • 条件：25 ≤ scale < 33
      • 特点：技术水平相近的开发者
      • 目的：促进技术交流与协作

   c) Floating节点 (10-20个)：
      • 条件：scale < 25
      • 特点：新兴或潜在的合作者
      • 目的：扩展社交网络

3. 节点分配算法：
   a) 初始分类：
      • mentor_nodes = [u for u in users if get_user_scale(u) ≥ 33]
      • peer_nodes = [u for u in users if 25 ≤ get_user_scale(u) < 33]
      • floating_nodes = [u for u in users if get_user_scale(u) < 25]

   b) 数量控制：
      • mentor_count = min(max(6, len(mentor_nodes)), 10)
      • peer_count = min(max(9, len(peer_nodes)), 15)
      • floating_count = min(max(10, len(floating_nodes)), 20)

   c) 节点筛选：
      • 按相似度降序排序
      • 选取指定数量的节点
      • 保持类型比例平衡

4. 节点属性设置：
   • id: 用户的GitHub登录名
   • type: mentor/peer/floating
   • weight: 基于相似度计算
   • size: 基于用户规模计算""",

        'user-repo': """仓库节点分类算法：

1. 输入变量：
   • repos：推荐仓库列表
   • similarities：仓库相似度列表
   • user_scale：用户的规模指数

2. 节点类型定义：
   a) Mentor节点 (3-5个)：
      • 条件：scale ≥ 33
      • 特点：成熟的大型开源项目
      • 目的：深入学习的目标

   b) Peer节点 (4-7个)：
      • 条件：25 ≤ scale < 33
      • 特点：适合贡献的中型项目
      • 目的：参与开源实践

   c) Floating节点 (6-12个)：
      • 条件：scale < 25
      • 特点：新兴或小型项目
      • 目的：发掘潜在机会

3. 节点分配算法：
   a) 初始分类：
      • mentor_nodes = [r for r in repos if get_repo_scale(r) ≥ 33]
      • peer_nodes = [r for r in repos if 25 ≤ get_repo_scale(r) < 33]
      • floating_nodes = [r for r in repos if get_repo_scale(r) < 25]

   b) 数量控制：
      • mentor_count = min(max(3, len(mentor_nodes)), 5)
      • peer_count = min(max(4, len(peer_nodes)), 7)
      • floating_count = min(max(6, len(floating_nodes)), 12)

   c) 节点筛选：
      • 按相似度降序排序
      • 选取指定数量的节点
      • 确保语言和主题多样性

4. 节点属性设置：
   • id: 仓库的full_name
   • type: mentor/peer/floating
   • weight: 基于相似度计算
   • size: 基于仓库规模计算"""
    },
    
    # 相似度计算算法
    'similarity_algo': {
        'user-user': """用户间相似度计算算法：

1. 语言偏好相似度计算：
   a) 语言向量构建：
      • 获取所有语言列表 L = {l₁, ..., lₙ}
      • 计算每种语言的代码量占比
      • 构建归一化向量 v = (p₁, ..., pₙ)
   
   b) 余弦相似度计算：
      • 提取两用户的语言向量 v₁, v₂
      • 计算点积和模长
      • 应用余弦公式得到相似度

2. 主题兴趣相似度计算：
   a) 主题集合处理：
      • 收集两用户的所有仓库主题
      • 构建主题集合 T₁, T₂
      • 去重和标准化处理
   
   b) Jaccard系数计算：
      • 计算集合交集大小 |T₁ ∩ T₂|
      • 计算集合并集大小 |T₁ ∪ T₂|
      • 计算比值得到相似度

3. 活跃度相似度计算：
   a) 指标对数转换：
      • 应用ln(x+1)转换降低量级差异
      • 对followers、following、repos分别处理
      • 使用不同的归一化基数(10⁴,10³,10²)
   
   b) 差异度计算：
      • 计算转换后的指标差异
      • 应用权重(0.4,0.3,0.3)
      • 转换为相似度(1-差异度)""",

        'user-repo': """用户-仓库相似度计算算法：

1. 语言匹配度计算：
   a) 用户语言统计：
      • 统计用户所有仓库的语言使用
      • 计算每种语言的代码量占比
      • 构建语言使用概率分布

   b) 仓库语言匹配：
      • 获取仓库主要语言
      • 查找用户对应语言的使用比例
      • 直接使用该比例作为匹配度

2. 主题匹配度计算：
   a) 主题集合构建：
      • 收集用户的兴趣主题集合
      • 获取仓库的主题标签集合
      • 标准化处理(小写、去重等)

   b) 相似度计算：
      • 计算两个集合的交集大小
      • 计算两个集合的并集大小
      • 应用Jaccard公式计算相似度

3. 规模时效性计算：
   a) 规模分数计算：
      • 对star数和fork数做对数转换
      • 应用不同权重(0.7,0.3)
      • 归一化到[0,1]区间

   b) 时效性调整：
      • 检查最后更新时间
      • 根据时效性应用乘数因子
      • 1.2(活跃)或0.8(不活跃)"""
    },
    
    # 推荐算法
    'recommend': {
        'user-user': """用户推荐算法实现：

1. 推荐池构建：
   a) 规模计算：
      • N = base_size + scale_factor
        - base_size = 100
        - scale_factor = (scale - 20) × 5
        - N ∈ [100, 200]

   b) 候选集构建：
      P = P₁ ∪ P₂ ∪ P₃ 其中：
      • P₁ (50%): 直接关联用户
        - F = followers ∪ following
        - C = {c | c ∈ contributors(r), r ∈ user.starred_repos}
        - P₁ = F ∪ C

      • P₂ (30%): 主题语言相关
        - L = get_user_languages(user)
        - T = get_user_topics(user)
        - P₂ = search_users(languages=L, topics=T)

      • P₃ (20%): 趋势补充
        - P₃ = get_trending_users()

2. 相似度计算：
   对于每个候选用户 u ∈ P：
   • sim(user, u) = compute_similarity(user, u)
   • 按相似度降序排序
   • 选取前 N 个用户作为推荐集 R

3. 节点分类：
   对于每个推荐用户 r ∈ R：
   a) 规模分类：
      • scale = compute_user_scale(r)
      • 根据scale分配到对应层级

   b) 类型分配：
      • 核心节点：P₁中相似度最高的用户
      • 扩展节点：P₂中的高相似度用户
      • 探索节点：P₃中的新兴用户

4. 结果优化：
   a) 多样性保证：
      • 每个层级节点数量平衡
      • 不同来源节点混合
      • 随机打乱同类节点顺序

   b) 动态调整：
      • 根据用户反馈调整权重
      • 更新候选池组成比例
      • 优化节点分布策略""",

        'user-repo': """仓库推荐算法实现：

1. 推荐池构建：
   a) 规模计算：
      • N = base_size + scale_factor
        - base_size = 60
        - scale_factor = (scale - 20) × 2
        - N ∈ [60, 100]

   b) 候选集构建：
      P = P₁ ∪ P₂ ∪ P₃ 其中：
      • P₁ (50%): 相似仓库
        - S = get_similar_repos(user.starred_repos)
        - L = get_top_repos(user.languages)
        - P₁ = S ∪ L

      • P₂ (30%): 主题相关
        - T = get_user_topics(user)
        - P₂ = search_repos(topics=T)

      • P₃ (20%): 趋势补充
        - P₃ = get_trending_repos()

2. 相似度计算：
   对于每个候选仓库 r ∈ P：
   • sim(user, r) = compute_repo_similarity(user, r)
   • 按相似度降序排序
   • 选取前 N 个仓库作为推荐集 R

3. 节点分类：
   对于每个推荐仓库 r ∈ R：
   a) 规模分类：
      • scale = compute_repo_scale(r)
      • 根据scale分配到对应层级

   b) 类型分配：
      • 核心项目：与用户高度相关的成熟项目
      • 热门项目：当前活跃的热门仓库
      • 新兴项目：近期快速增长的项目

4. 结果优化：
   a) 多样性保证：
      • 语言分布均衡
      • 主题覆盖广泛
      • 规模分布合理

   b) 时效性优化：
      • 优先推荐活跃项目
      • 考虑更新频率
      • 关注社区活跃度"""
    }
}

def get_algorithm_explanation(type: str, mode: Optional[str] = None) -> str:
    """获取算法解释"""
    # 详细的日志记录
    logger.info(f"Received request - type: {type}, mode: {mode}")
    logger.info(f"Available types: {list(explanations.keys())}")
    
    if type in explanations:
        if isinstance(explanations[type], dict):
            logger.info(f"Available modes for {type}: {list(explanations[type].keys())}")
            logger.info(f"Looking for mode: {mode}")
            explanation = explanations[type].get(mode)
            if explanation:
                logger.info(f"Found explanation for {type}/{mode}")
                return explanation
            else:
                logger.warning(f"No explanation found for mode: {mode} in type: {type}")
                logger.warning(f"Available modes were: {list(explanations[type].keys())}")
                return "暂无该模式的解释"
        else:
            logger.info(f"Direct explanation for {type}")
            return explanations[type]
    
    logger.warning(f"Type not found: {type}")
    logger.warning(f"Available types were: {list(explanations.keys())}")
    return "暂无该类型的解释" 