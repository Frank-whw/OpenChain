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
1. 基础指标：
   - followers数量
   - following数量
   - public_repos数量
   
2. 计算公式：
   scale = min(max(
       (followers * 0.5 + following * 0.3 + public_repos * 0.2) / 50,
       20
   ), 100)
   
3. 指标含义：
   - 20-40: 初级开发者
   - 41-60: 中级开发者
   - 61-80: 高级开发者
   - 81-100: 专家级开发者""",
        
        'repo': """仓库规模指数计算方法：
1. 基础指标：
   - stars数量
   - forks数量
   - watchers数量
   
2. 计算公式：
   scale = min(max(
       (stars * 0.5 + forks * 0.3 + watchers * 0.2) / 100,
       20
   ), 100)
   
3. 指标含义：
   - 20-40: 小型项目
   - 41-60: 中型项目
   - 61-80: 大型项目
   - 81-100: 超大型项目"""
    },
    
    # 相似度解释
    'similarity': {
        'user-user': """用户-用相似度加权计算：
1. 语言偏好匹配 (30%)
   - 分析两个用户的仓库使用的编程语言
   - 计算语言使用频率的余弦相似度
   
2. 主题兴趣匹配 (30%)
   - 分析两个用户的仓库主题标签
   - 计算主题标签的Jaccard相似度
   
3. 活跃度匹配 (40%)
   - 比较两个用户的活跃程度
   - 考虑followers、following、repos数量
   - 使用对数尺度计算差异""",
        
        'user-repo': """用户-仓库相似度计算：
1. 语言匹配度 (30%)
   - 分析用户的语言偏好
   - 与仓库的主要语言进行匹配
   
2. 主题匹配度 (30%)
   - 分析用户的兴趣主题
   - 与仓库的主题标签进行匹配
   
3. 活跃度匹配 (40%)
   - 比较用户活跃度与仓库活跃度
   - 考虑仓库的stars、forks等指标
   - 使用对数尺度平滑差异"""
    },
    
    # 推荐池算法
    'pool': {
        'user-user': """用户推荐池构建算法：
1. 初始候选人来源：
   - 目标用户的followers/following
   - 相似仓库的贡献者
   - 共同参与的项目成员
   
2. 扩展策略：
   - 从活跃用户中补充
   - 从相关主题的活跃用户补充
   - 从trending用户中补充
   
3. 池大小控制：
   - 基础池大小：100
   - 根据用户规模动态调整
   - 最终范围：100-200""",
        
        'user-repo': """仓库推荐池构建算法：
1. 初始候选仓库来源：
   - 用户star的仓库
   - 用户语言相关的热门仓库
   - 用户主题相关的仓库
   
2. 扩展策略：
   - 从trending仓库补充
   - 从相似仓库补充
   - 从相关主题补充
   
3. 池大小控制：
   - 基础池大小：60
   - 根据用户规模调整
   - 最终范围：60-100"""
    },
    
    # 节点分类算法
    'node': {
        'user-user': """用户推荐的节点分类：
1. Mentor节点 (6-10个)：
   - 规模指数 >= 33
   - 经验丰富的开发者
   - 可能成为良师益友
   
2. Peer节点 (9-15个)：
   - 规模指数 25-33
   - 技术水平相近
   - 适合技术交流
   
3. Floating节点 (10-20个)：
   - 规模指数 < 25
   - 潜在的合作伙伴
   - 提供更多可能性""",
        
        'user-repo': """仓库推荐的节点分类：
1. Mentor节点 (3-5个)：
   - 规模指数 >= 33
   - 成熟的大型项目
   - 值得深入学习
   
2. Peer节点 (4-7个)：
   - 规模指数 25-33
   - 适合参与贡献
   - 技术栈匹配
   
3. Floating节点 (6-12个)：
   - 规模指数 < 25
   - 新兴项目
   - 探索机会"""
    },
    
    # 相似度算法
    'similarity_algo': {
        'user-user': """用户相似度算法详解：
1. 语言偏好相似度：
   - 统计每个用户的语言使用频率
   - 构建语言向量
   - 计算向量余弦相似度
   
2. 主题兴趣相似度：
   - 收集用户仓库的所有主题
   - 计算主题集合的交集和并集
   - 使用Jaccard系数计算相似度
   
3. 活跃度相似度：
   - 提取活跃度指标
   - 使用对数转换降低量级差异
   - 计算归一化差异""",
        
        'user-repo': """用户-仓库相似度算法详解：
1. 语言匹配度计算：
   - 统计用户的语言偏好分布
   - 与仓库主要语言比对
   - 计算加权匹配分数
   
2. 主题匹配度计算：
   - 收集用户的兴趣主题集合
   - 与仓库主题标签比对
   - 计算重叠度得分
   
3. 活跃度匹配计算：
   - 用户活跃度：仓库数量
   - 仓库活跃度：stars+forks
   - 使用对数尺度计算差异"""
    },
    
    # 推荐算法
    'recommend': {
        'user-user': """用户推荐算法流程：
1. 构建推荐池：
   - 收集初始候选人
   - 扩展候选池
   - 控制池大小
   
2. 计算相似度：
   - 多维度相似度计算
   - 加权综合得分
   - 排序筛选
   
3. 节点分类：
   - 根据规模分类
   - 分配节点类型
   - 控制节点数量
   
4. 结果优化：
   - 随机打乱同类节点
   - 确保多样性
   - 动态调整分布""",
        
        'user-repo': """仓库推荐算法流程：
1. 构建推荐池：
   - 收集候选仓库
   - 扩展候选池
   - 控制池大小
   
2. 计算相似度：
   - 语言匹配度
   - 主题匹配度
   - 活跃度匹配
   
3. 节点分类：
   - 规模指数分类
   - 分配节点类型
   - 控制节点数量
   
4. 结果优化：
   - 确保推荐多样性
   - 平衡节点分布
   - 随机化处理"""
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