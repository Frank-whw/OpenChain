import requests
import json
from typing import List, Dict, Tuple, Any, Set
import time
from collections import defaultdict
import concurrent.futures
from functools import lru_cache
import threading
import math
import os
import logging
from fastapi import FastAPI
from datetime import datetime
from dotenv import load_dotenv
import random

# 加载 .env 文件
load_dotenv()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 创建 FastAPI 应用实例
app = FastAPI()

# 全局配置
N = 10  # 修改推荐结果数量为10个
CACHE_SIZE = 128  # 缓存大小
MAX_WORKERS = 10  # 最大并行线程数
GITHUB_API = "https://api.github.com"
OPENDIGGER_API = "https://oss.x-lab.info/open_digger/github"

# GitHub Token 配置
GITHUB_TOKENS = [
    os.getenv('GITHUB_TOKEN'),
    os.getenv('GITHUB_TOKEN_2'),
    os.getenv('GITHUB_TOKEN_3'),
    os.getenv('GITHUB_TOKEN_4')
]

# 过滤掉空token并验证
GITHUB_TOKENS = [token for token in GITHUB_TOKENS if token and token.startswith('ghp_')]
logger.info(f"Found {len(GITHUB_TOKENS)} valid GitHub tokens")

if not GITHUB_TOKENS:
    logger.error("No valid GitHub tokens found in environment variables!")
    raise RuntimeError("No valid GitHub tokens available")

class TokenManager:
    def __init__(self):
        self.tokens = GITHUB_TOKENS
        self.current_index = 0
        self._lock = threading.Lock()
        logger.info(f"TokenManager initialized with {len(self.tokens)} tokens")

    def get_token(self):
        """获取下一个token"""
        with self._lock:
            token = self.tokens[self.current_index]
            self.current_index = (self.current_index + 1) % len(self.tokens)
            return token

token_manager = TokenManager()

# API请求头
headers = {
    "Authorization": f"token {GITHUB_TOKENS[0]}" if GITHUB_TOKENS else "",
    "Accept": "application/vnd.github.v3+json"
}

# 线程本地存储
thread_local = threading.local()

def get_session():
    """获取线程本地的session对象"""
    if not hasattr(thread_local, "session"):
        thread_local.session = requests.Session()
    
    # 获取新token并更新headers
    token = token_manager.get_token()
    thread_local.session.headers.update({
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    })
    
    return thread_local.session

@lru_cache(maxsize=CACHE_SIZE)
def get_trending_repos() -> List[Dict]:
    """获取GitHub趋势仓库作为备选（带缓存）"""
    session = get_session()
    try:
        response = session.get(
            f"{GITHUB_API}/search/repositories",
            headers=headers,
            params={
                "q": "stars:>1000",
                "sort": "stars",
                "order": "desc",
                "per_page": N  # 使用全局配置的 N 值
            }
        )
        return response.json().get('items', [])[:N] if response.status_code == 200 else []
    except Exception as e:
        logger.error(f"Error in get_trending_repos: {str(e)}")
        return []

def _get_trending_repos(languages: List[str] = None) -> List[Dict]:
    """获取热门仓库"""
    session = get_session()
    
    try:
        # 构建查询件
        query_parts = []
        
        # 基础条件：stars数量要求（降低要求）
        query_parts.append('stars:>10')
        
        # 语言条件
        if languages and languages[0]:
            query_parts.append(f'language:{languages[0]}')
        
        # 组合查询条件
        query = ' '.join(query_parts)
        
        logger.info(f"Searching repositories with query: {query}")
        
        # 添加重试机制
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = session.get(
                    f"{GITHUB_API}/search/repositories",
                    params={
                        'q': query,
                        'sort': 'stars',
                        'order': 'desc',
                        'per_page': N  # 使用全局配置的 N 值
                    },
                    headers=headers,
                    timeout=10
                )
                
                if response.status_code == 403:
                    logger.error(f"API rate limit exceeded (attempt {attempt + 1}/{max_retries})")
                    time.sleep(2)
                    continue
                    
                if response.status_code == 200:
                    data = response.json()
                    if 'items' in data:
                        # 过滤掉 fork 的仓库
                        items = [item for item in data['items'] if not item.get('fork', False)]
                        logger.info(f"Found {len(items)} repositories before filtering")
                        filtered_items = items[:N]  # 确保只返回 N 个结果
                        logger.info(f"Returning {len(filtered_items)} repositories after filtering")
                        return filtered_items
                    
                logger.warning(f"Unexpected response status: {response.status_code}")
                
            except Exception as e:
                logger.error(f"Request failed (attempt {attempt + 1}/{max_retries}): {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                continue
        
        # 如果所有尝试都失败，返回备选仓库列表
        logger.info("Returning fallback repository list")
        fallback_repos = [
            {
                'full_name': 'facebook/react',
                'language': 'JavaScript',
                'stargazers_count': 200000,
                'forks_count': 40000,
                'description': 'A declarative, efficient, and flexible JavaScript library for building user interfaces.'
            },
            {
                'full_name': 'tensorflow/tensorflow',
                'language': 'Python',
                'stargazers_count': 170000,
                'forks_count': 30000,
                'description': 'An Open Source Machine Learning Framework for Everyone'
            },
            {
                'full_name': 'microsoft/vscode',
                'language': 'TypeScript',
                'stargazers_count': 140000,
                'forks_count': 25000,
                'description': 'Visual Studio Code'
            }
        ][:N]  # 确保备选列表也只返回 N 个结果
        logger.info(f"Returning {len(fallback_repos)} fallback repositories")
        return fallback_repos
    except Exception as e:
        logger.error(f"Error in _get_trending_repos: {str(e)}")
        return []

def _get_language_preferences(repos: List[Dict]) -> List[str]:
    """获取语言偏好"""
    languages = {}
    for repo in repos:
        lang = repo.get('language')
        if lang:
            languages[lang] = languages.get(lang, 0) + 1
    return sorted(languages.keys(), key=lambda x: languages[x], reverse=True)[:3]

@lru_cache(maxsize=CACHE_SIZE)
def get_user_info(username: str) -> Dict:
    """获取用户信息（带缓存）"""
    session = get_session()
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Fetching user info for: {username} (attempt {attempt + 1}/{max_retries})")
            response = session.get(
                f"{GITHUB_API}/users/{username}",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 404:
                logger.warning(f"User not found: {username}")
                return None
            
            if response.status_code == 403:
                logger.error(f"API rate limit exceeded (attempt {attempt + 1}/{max_retries})")
                time.sleep(2)
                continue
                
            if response.status_code == 200:
                user_data = response.json()
                # 验证返回的数据包必要的字段
                if all(key in user_data for key in ['login', 'followers', 'following', 'public_repos']):
                    return user_data
                else:
                    logger.error(f"Incomplete user data received for: {username}")
                    return None
            
            logger.error(f"Unexpected response status: {response.status_code}")
            
        except Exception as e:
            logger.error(f"Request failed (attempt {attempt + 1}/{max_retries}): {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(2)
            continue
    
    logger.error(f"All attempts failed for user: {username}")
    return None

@lru_cache(maxsize=CACHE_SIZE)
def get_repo_info(repo_full_name: str) -> Dict:
    """获取仓库信息（带缓存）"""
    session = get_session()
    try:
        logger.info(f"Fetching repo info for: {repo_full_name}")
        response = session.get(f"{GITHUB_API}/repos/{repo_full_name}", headers=headers)
        
        if response.status_code == 404:
            logger.warning(f"Repository not found: {repo_full_name}")
            return {}
        elif response.status_code == 403:
            logger.error("API rate limit exceeded")
            return {}
        elif response.status_code != 200:
            logger.error(f"Failed to fetch repo info: {response.status_code}")
            return {}
        
        return response.json()
    except Exception as e:
        logger.error(f"Error fetching repo info: {str(e)}")
        return {}

@lru_cache(maxsize=CACHE_SIZE)
def get_user_repos(username: str) -> List[Dict]:
    """获取用户的仓库列表（只获取第一页，提高速度）"""
    session = get_session()
    response = session.get(
        f"{GITHUB_API}/users/{username}/repos",
        headers=headers,
        params={"per_page": 100}  # 只获取前100个仓库
    )
    return response.json() if response.status_code == 200 else []

@lru_cache(maxsize=CACHE_SIZE)
def get_repo_contributors(repo_full_name: str) -> List[Dict]:
    """获取仓库的贡献者列表（只获取第一页）"""
    session = get_session()
    response = session.get(
        f"{GITHUB_API}/repos/{repo_full_name}/contributors",
        headers=headers,
        params={"per_page": 100}  # 只获取前100个贡献者
    )
    return response.json() if response.status_code == 200 else []

@lru_cache(maxsize=CACHE_SIZE)
def get_active_users() -> List[Dict]:
    """获取活跃用户作为备选（带缓存）"""
    session = get_session()
    try:
        response = session.get(
            f"{GITHUB_API}/search/users",
            headers=headers,
            params={
                "q": "followers:>1000",
                "sort": "followers",
                "order": "desc",
                "per_page": 100
            }
        )
        return response.json().get('items', []) if response.status_code == 200 else []
    except:
        return []

def get_user_scale(username: str) -> float:
   """
   计算用户规模指标（综合影响力、活跃度和贡献质量）
   返回范围：20-40
   """
   session = get_session()
   try:
       # 获取用户基本信息
       user_info = get_user_info(username)
       if not user_info:
           return 20
           
       # 获取用户的仓库列表
       repos = get_user_repos(username)
       
       # 1. 计算社交影响力指数 (0-1)
       followers = user_info.get('followers', 0)
       social_impact = min(1.0, math.log(followers + 1) / math.log(10000))  # 上限10000
       
       # 2. 计算仓库质量指数 (0-1)
       if repos:
           # 计算用户仓库的平均star数和fork数
           avg_stars = sum(repo.get('stargazers_count', 0) for repo in repos) / len(repos)
           avg_forks = sum(repo.get('forks_count', 0) for repo in repos) / len(repos)
           repo_quality = min(1.0, (math.log(avg_stars + 1) / math.log(1000) + 
                                  math.log(avg_forks + 1) / math.log(500)) / 2)
       else:
           repo_quality = 0
           
       # 3. 计算活跃度指数 (0-1)
       public_repos = user_info.get('public_repos', 0)
       recent_repos = [repo for repo in repos 
                      if (datetime.now() - datetime.strptime(repo.get('updated_at', ''), '%Y-%m-%dT%H:%M:%SZ')).days <= 365]
       activity_ratio = len(recent_repos) / public_repos if public_repos > 0 else 0
       activity_score = min(1.0, (math.log(public_repos + 1) / math.log(100)) * activity_ratio)
       
       # 4. 综合计算最终得分 (0-1)
       # 权重分配：社交影响力(0.4) + 仓库质量(0.4) + 活跃度(0.2)
       final_score = (social_impact * 0.4 + 
                     repo_quality * 0.4 + 
                     activity_score * 0.2)
       
       # 5. 映射到20-40范围
       normalized_scale = 20 + final_score * 20
       
       return normalized_scale
       
   except Exception as e:
       logger.error(f"Error calculating user scale for {username}: {str(e)}")
       return 20

def get_repo_scale(repo_full_name: str) -> float:
   """
   计算仓库规模指标（综合热度、活跃度和代码质量）
   返回范围：20-40
   """
   session = get_session()
   try:
       # 获取仓库本信息
       repo_info = get_repo_info(repo_full_name)
       if not repo_info:
           return 20
           
       # 1. 计算社区热度指数 (0-1)
       stars = repo_info.get('stargazers_count', 0)
       forks = repo_info.get('forks_count', 0)
       watchers = repo_info.get('subscribers_count', 0)
       
       popularity_score = min(1.0, (math.log(stars + 1) / math.log(50000) * 0.5 +  # stars权重更高
                                  math.log(forks + 1) / math.log(10000) * 0.3 +    # forks次之
                                  math.log(watchers + 1) / math.log(5000) * 0.2))   # watchers最低
       
       # 2. 计算活跃度指数 (0-1)
       # 获取最近一年的提交统计
       commits_url = f"{GITHUB_API}/repos/{repo_full_name}/stats/participation"
       response = session.get(commits_url, headers=headers)
       recent_commits = sum(response.json().get('all', [0] * 52)) if response.status_code == 200 else 0
       
       # 获取最近的issue和PR数量
       issues_url = f"{GITHUB_API}/repos/{repo_full_name}/issues?state=all&per_page=100"
       response = session.get(issues_url, headers=headers)
       recent_issues = len([i for i in response.json() if 
                          (datetime.now() - datetime.strptime(i.get('created_at', ''), '%Y-%m-%dT%H:%M:%SZ')).days <= 365]) if response.status_code == 200 else 0
       
       activity_score = min(1.0, (math.log(recent_commits + 1) / math.log(1000) * 0.6 +  # 提交次数权重更高
                                 math.log(recent_issues + 1) / math.log(500) * 0.4))      # issue/PR次之
       
       # 3. 计算代码质量指数 (0-1)
       size = repo_info.get('size', 0)  # 仓库大小（KB）
       open_issues = repo_info.get('open_issues_count', 0)  # 开放的issue数量
       total_issues = recent_issues or 1  # 避免零
       issue_resolution_rate = 1 - (open_issues / total_issues)  # issue解决率
       
       # 获取贡献者数量
       contributors = get_repo_contributors(repo_full_name)
       contributor_count = len(contributors)
       
       quality_score = min(1.0, (math.log(size + 1) / math.log(1000000) * 0.3 +        # 代码量
                                issue_resolution_rate * 0.4 +                            # issue解决率
                                math.log(contributor_count + 1) / math.log(100) * 0.3))  # 贡献者��量
       
       # 4. 综合计算最终得分 (0-1)
       # 权重分配：社区热度(0.4) + 活跃度(0.3) + 代码质量(0.3)
       final_score = (popularity_score * 0.4 + 
                     activity_score * 0.3 + 
                     quality_score * 0.3)
       
       # 5. 映射到20-40范围
       normalized_scale = 20 + final_score * 20
       
       return normalized_scale
       
   except Exception as e:
       logger.error(f"Error calculating repo scale for {repo_full_name}: {str(e)}")
       return 20

def calculate_user_user_similarity(user1: str, user2: str) -> float:
    """计算用户-用户相似度（多维度）"""
    # 获取用户信息和仓库
    repos1 = get_user_repos(user1)
    repos2 = get_user_repos(user2)
    
    # 1. 语言相似度 (30%)
    langs1 = set(repo['language'] for repo in repos1 if repo['language'])
    langs2 = set(repo['language'] for repo in repos2 if repo['language'])
    lang_similarity = len(langs1.intersection(langs2)) / len(langs1.union(langs2)) if langs1 and langs2 else 0
    
    # 2. 主题相似度 (40%)
    topics1 = set()
    topics2 = set()
    for repo in repos1:
        topics1.update(repo.get('topics', []))
    for repo in repos2:
        topics2.update(repo.get('topics', []))
    topic_similarity = len(topics1.intersection(topics2)) / len(topics1.union(topics2)) if topics1 and topics2 else 0
    
    # 3. 规模相似度 (30%)
    size1 = sum(repo.get('size', 0) for repo in repos1)
    size2 = sum(repo.get('size', 0) for repo in repos2)
    size_similarity = 1 - abs(size1 - size2) / max(size1 + size2, 1)
    
    # 综合计算 (20% + 30% + 50%)
    return 0.2 * lang_similarity + 0.3 * topic_similarity + 0.5 * size_similarity

def calculate_repo_repo_similarity(repo1: str, repo2: str) -> float:
    """计算仓库-仓库相似度（多维度）"""
    info1 = get_repo_info(repo1)
    info2 = get_repo_info(repo2)
    
    # 1. 语言相似度 (30%)
    language_similarity = 1 if info1.get('language') == info2.get('language') else 0
    
    # 2. 主题相似度 (40%)
    topics1 = set(info1.get('topics', []))
    topics2 = set(info2.get('topics', []))
    topic_similarity = len(topics1.intersection(topics2)) / len(topics1.union(topics2)) if topics1 or topics2 else 0
    
    # 3. 规模相似度 (30%)
    size1 = info1.get('size', 0)
    size2 = info2.get('size', 0)
    size_similarity = 1 - abs(size1 - size2) / max(size1 + size2, 1)
    
    # 综合计算 (30% + 40% + 30%)
    return 0.3 * language_similarity + 0.4 * topic_similarity + 0.3 * size_similarity

def calculate_user_repo_similarity(username: str, repo_name: str) -> float:
    """计算用户-仓库相似度（多维度）"""
    # 获取用户和仓库信息
    user_repos = get_user_repos(username)
    repo_info = get_repo_info(repo_name)
    
    # 1. 语言匹配度 (30%)
    user_languages = defaultdict(int)
    for repo in user_repos:
        if repo['language']:
            user_languages[repo['language']] += 1
    total_repos = sum(user_languages.values())
    repo_language = repo_info.get('language', '')
    language_match = user_languages.get(repo_language, 0) / total_repos if total_repos > 0 else 0
    
    # 2. 主题匹配度 (40%)
    user_topics = set()
    for repo in user_repos:
        user_topics.update(repo.get('topics', []))
    repo_topics = set(repo_info.get('topics', []))
    topic_match = len(repo_topics.intersection(user_topics)) / len(repo_topics.union(user_topics)) if repo_topics or user_topics else 0
    
    # 3. 规模匹配度 (30%)
    user_avg_size = sum(repo.get('size', 0) for repo in user_repos) / len(user_repos) if user_repos else 0
    repo_size = repo_info.get('size', 0)
    size_match = 1 - abs(user_avg_size - repo_size) / max(user_avg_size + repo_size, 1)
    
    # 综合计算 (30% + 40% + 30%)
    return 0.3 * language_match + 0.4 * topic_match + 0.3 * size_match

def get_candidates_batch(repos: List[Dict], session: requests.Session, max_per_repo: int = 10) -> Set[str]:
    """批量获取仓库贡献者"""
    candidates = set()
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_to_repo = {
            executor.submit(get_repo_contributors, repo['full_name']): repo 
            for repo in repos
        }
        for future in concurrent.futures.as_completed(future_to_repo):
            try:
                contributors = future.result()[:max_per_repo]
                candidates.update(c['login'] for c in contributors)
            except Exception:
                continue
    return candidates

def recommend(type_str: str, name: str, find: str, count: int = N) -> Dict[str, Any]:
    """推荐函数"""
    try:
        session = get_session()
        count = N if count is None else min(count, N)
        total_count = count * 3  # 获取3倍的推荐结果，多出的部分用作游离节点
        
        # 扩大推荐池大小 (50-100)，并增加随机性
        user_scale = get_user_scale(name)
        base_pool_size = 50  # 基础池大小
        scale_factor = (user_scale - 20) * 2.5  # 增加规模因子的影响
        pool_size = int(base_pool_size + scale_factor)
        pool_size = min(max(pool_size, 50), 100)  # 确保在50-100之间
        
        logger.info(f"Processing recommendation request: {type_str}/{name} -> {find}, count={count}, total_count={total_count}, pool_size={pool_size}")

        # 获取中心节点信息
        center_metrics = {}
        if type_str == 'user':
            center_info = get_user_info(name)
            if center_info:
                center_metrics = {
                    'followers': center_info.get('followers', 0),
                    'following': center_info.get('following', 0),
                    'public_repos': center_info.get('public_repos', 0),
                    'size': user_scale
                }
        else:  # type_str == 'repo'
            center_info = get_repo_info(name)
            if center_info:
                center_metrics = {
                    'stars': center_info.get('stargazers_count', 0),
                    'forks': center_info.get('forks_count', 0),
                    'watchers': center_info.get('watchers_count', 0),
                    'size': get_repo_scale(name)
                }

        # 更新基础响应中的指标信息
        base_response = {
            'metrics': center_metrics,  # 使用获取到的中心节点指标
            'recommendations': [],
            'status': 'success',
            'message': ''
        }

        if type_str == 'user' and find == 'user':
            user_info = get_user_info(name)
            if not user_info:
                return base_response

            # 获取用户的仓库和贡献信息
            user_repos = get_user_repos(name)
            
            # 判断用户类型和活跃度
            if not user_repos or user_info.get('public_repos', 0) == 0:
                user_type = "newcomer"
                is_active = False
            elif user_scale > 33:
                user_type = "high_active"
                is_active = True
            elif user_scale > 25:
                user_type = "low_active"
                is_active = False
            else:
                user_type = "newcomer"
                is_active = False

            try:
                # 获取候选用户
                with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
                    # 获取更大范围的候选用户
                    similar_scale_query = f'followers:>5 repos:>1'  # 降低筛选条件
                    candidates = session.get(
                        f"{GITHUB_API}/search/users",
                        params={
                            'q': similar_scale_query,
                            'sort': 'followers',
                            'per_page': pool_size * 2  # 获取更多候选人
                        }
                    ).json().get('items', [])
                    
                    # 随机打乱候选人顺序，增加推荐的多样性
                    candidates = [c['login'] for c in candidates if c['login'] != name]
                    random.shuffle(candidates)
                    candidates = candidates[:pool_size]  # 取前pool_size个
                    
                    # 并行获取所有候选用户的信息和计算相似度
                    future_to_candidate = {}
                    for candidate in candidates:
                        def process_candidate(candidate=candidate):
                            return (
                                candidate,
                                calculate_user_user_similarity(name, candidate),
                                get_user_info(candidate),
                                get_user_scale(candidate)
                            )
                        future_to_candidate[executor.submit(process_candidate)] = candidate
                    
                    all_recommendations = []
                    for future in concurrent.futures.as_completed(future_to_candidate):
                        try:
                            candidate, similarity, user_info, candidate_scale = future.result()
                            if user_info:
                                # 基于相似度确定节点类型
                                if similarity >= 0.7:
                                    node_type = 'mentor'    # 高相似度用户
                                elif similarity >= 0.4:
                                    node_type = 'peer'      # 中等相似度用户
                                else:
                                    node_type = 'floating'  # 低相似度用户

                                all_recommendations.append({
                                    'name': candidate,
                                    'metrics': {
                                        'followers': user_info.get('followers', 0),
                                        'following': user_info.get('following', 0),
                                        'public_repos': user_info.get('public_repos', 0),
                                        'size': candidate_scale
                                    },
                                    'similarity': similarity,
                                    'nodeType': node_type  # 添加节点类型
                                })
                        except Exception as e:
                            logger.error(f"Error processing candidate: {str(e)}")
                            continue
                    
                    # 最终推荐结果也可以加入一定随机性
                    if len(all_recommendations) > count:
                        # 保留相似度最高的前20%
                        top_count = max(1, count // 5)
                        top_recommendations = all_recommendations[:top_count]
                        # 从剩余结果中随机选择
                        remaining_count = count - top_count
                        remaining_pool = all_recommendations[top_count:]
                        random.shuffle(remaining_pool)
                        selected_recommendations = remaining_pool[:remaining_count]
                        # 合并结果
                        base_response['recommendations'] = top_recommendations + selected_recommendations
                    else:
                        base_response['recommendations'] = all_recommendations

                # 并行获取用户信息和关注列表
                with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
                    future_user_info = executor.submit(get_user_info, name)
                    future_following = executor.submit(
                        lambda: session.get(f"{GITHUB_API}/users/{name}/following", headers=headers).json() 
                        if session.get(f"{GITHUB_API}/users/{name}/following", headers=headers).status_code == 200 else []
                    )
                    
                    user_info = future_user_info.result()
                    following_set = {user['login'] for user in future_following.result()}

                if user_type == "newcomer":
                    # 并行获取用户语言统计和候选用户
                    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
                        # 并行处理所有仓库的语言统计
                        user_languages = defaultdict(int)
                        futures_languages = [
                            executor.submit(lambda r: r.get('language'), repo)
                            for repo in user_repos if repo
                        ]
                        for future in concurrent.futures.as_completed(futures_languages):
                            lang = future.result()
                            if lang:
                                user_languages[lang] += 1
                        
                        # 并行获取候选用户
                        candidates = get_newcomer_candidates(name, user_languages, session)
                        candidates = list(candidates - following_set - {name})[:pool_size]
                        
                        # 并行获取所有候选用户的信息和计算相似度
                        future_to_candidate = {}
                        for candidate in candidates:
                            def process_candidate(candidate=candidate):
                                return (
                                    candidate,
                                    calculate_user_user_similarity(name, candidate),
                                    get_user_info(candidate),
                                    get_user_scale(candidate)
                                )
                            future_to_candidate[executor.submit(process_candidate)] = candidate
                        
                        all_recommendations = []
                        for future in concurrent.futures.as_completed(future_to_candidate):
                            try:
                                candidate, similarity, user_info, candidate_scale = future.result()
                                if user_info:
                                    # 基于相似度确定节点类型
                                    if similarity >= 0.7:
                                        node_type = 'mentor'    # 高相似度用户
                                    elif similarity >= 0.4:
                                        node_type = 'peer'      # 中等相似度用户
                                    else:
                                        node_type = 'floating'  # 低相似度用户

                                    all_recommendations.append({
                                        'name': candidate,
                                        'metrics': {
                                            'followers': user_info.get('followers', 0),
                                            'following': user_info.get('following', 0),
                                            'public_repos': user_info.get('public_repos', 0),
                                            'size': candidate_scale
                                        },
                                        'similarity': similarity,
                                        'nodeType': node_type  # 添加节点类型
                                    })
                            except Exception as e:
                                logger.error(f"Error processing candidate: {str(e)}")
                                continue
                        
                        # 按相似度排序
                        all_recommendations.sort(key=lambda x: x['similarity'], reverse=True)
                        base_response['recommendations'] = all_recommendations

                else:
                    # 活跃用户和非活跃用户的处理
                    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
                        candidates = set()
                        if is_active:
                            # 并行获取 starred 仓库和用户仓库的贡献者
                            future_starred = executor.submit(
                                lambda: session.get(
                                    f"{GITHUB_API}/users/{name}/starred?per_page=5",
                                    headers=headers
                                ).json() if session.get(
                                    f"{GITHUB_API}/users/{name}/starred?per_page=5",
                                    headers=headers
                                ).status_code == 200 else []
                            )
                            future_repos = executor.submit(
                                lambda: [r for r in get_user_repos(name)[:5] if not r.get('fork')]
                            )
                            
                            starred_repos = future_starred.result()
                            user_repos = future_repos.result()
                            
                            # 并行获取所有仓库的贡献者
                            futures_contributors = [
                                executor.submit(get_repo_contributors, repo['full_name'])
                                for repo in (starred_repos + user_repos)
                            ]
                            
                            for future in concurrent.futures.as_completed(futures_contributors):
                                try:
                                    contributors = future.result()
                                    candidates.update(c['login'] for c in contributors)
                                except Exception:
                                    continue
                        else:
                            # 并行获取关注者的关注者
                            future_followers = executor.submit(_get_user_followers, name)
                            followers = future_followers.result()[:5]
                            
                            futures_follower_followers = [
                                executor.submit(_get_user_followers, follower['login'])
                                for follower in followers
                            ]
                            
                            for future in concurrent.futures.as_completed(futures_follower_followers):
                                try:
                                    follower_followers = future.result()[:10]
                                    candidates.update(f['login'] for f in follower_followers)
                                except Exception:
                                    continue
                        
                        # 过滤并限制候选池大小
                        candidates = list(candidates - following_set - {name})[:pool_size]
                        
                        # 并行处理所有候选用户
                        future_to_candidate = {}
                        for candidate in candidates:
                            def process_candidate(candidate=candidate):
                                return (
                                    candidate,
                                    calculate_user_user_similarity(name, candidate),
                                    get_user_info(candidate),
                                    get_user_scale(candidate)
                                )
                            future_to_candidate[executor.submit(process_candidate)] = candidate
                        
                        all_recommendations = []
                        for future in concurrent.futures.as_completed(future_to_candidate):
                            try:
                                candidate, similarity, user_info, candidate_scale = future.result()
                                if user_info:
                                    # 基于相似度确定节点类型
                                    if similarity >= 0.7:
                                        node_type = 'mentor'    # 高相似度用户
                                    elif similarity >= 0.4:
                                        node_type = 'peer'      # 中等相似度用户
                                    else:
                                        node_type = 'floating'  # 低相似度用户

                                    all_recommendations.append({
                                        'name': candidate,
                                        'metrics': {
                                            'followers': user_info.get('followers', 0),
                                            'following': user_info.get('following', 0),
                                            'public_repos': user_info.get('public_repos', 0),
                                            'size': candidate_scale
                                        },
                                        'similarity': similarity,
                                        'nodeType': node_type  # 添加节点类型
                                    })
                            except Exception as e:
                                logger.error(f"Error processing candidate: {str(e)}")
                                continue
                        
                        # 按相似度排序
                        all_recommendations.sort(key=lambda x: x['similarity'], reverse=True)
                        base_response['recommendations'] = all_recommendations

            except Exception as e:
                logger.error(f"Error in user recommendation: {str(e)}")
                return base_response

        elif type_str == 'user' and find == 'repo':
            # 获取用户的仓库列表
            user_repos = get_user_repos(name)
            if not user_repos:
                error_msg = f'无法获取用户 {name} 的仓库列表，可能是由于 API 限制或网络问题'
                logger.warning(error_msg)
                base_response.update({
                    'status': 'error',
                    'message': error_msg
                })
                return base_response

            # 获取用户的语言偏好
            languages = _get_language_preferences(user_repos)
            
            # 获取相似语言的热门仓库
            trending_repos = _get_trending_repos(languages)
            if not trending_repos:
                error_msg = '无法获取热门仓库列表，可能是由于 API 限制或网络问题'
                logger.warning(error_msg)
                base_response.update({
                    'status': 'error',
                    'message': error_msg
                })
                return base_response

            # 计算相似度
            similarities = []
            for repo in trending_repos:
                repo_full_name = repo.get('full_name')
                if repo_full_name:  # 排除用户自己的仓库
                    try:
                        similarity = calculate_user_repo_similarity(name, repo_full_name)
                        similarities.append((repo_full_name, similarity))
                    except Exception as e:
                        logger.error(f"Error calculating similarity for {repo_full_name}: {str(e)}")

            # 排序并返回结果
            similarities.sort(key=lambda x: x[1], reverse=True)
            for repo_name, similarity in similarities[:count]:
                try:
                    repo_info = get_repo_info(repo_name)
                    if repo_info:
                        base_response['recommendations'].append({
                            'name': repo_name,
                            'metrics': {
                                'stars': repo_info.get('stargazers_count', 0),
                                'forks': repo_info.get('forks_count', 0),
                                'watchers': repo_info.get('watchers_count', 0),
                                'size': repo_info.get('size', 0)
                            },
                            'similarity': max(0.1, similarity)  # 确保最小相似度为0.1
                        })
                except Exception as e:
                    logger.error(f"Error getting info for repo {repo_name}: {str(e)}")

            # 如果推荐结果不足，尝试获取更多候选仓库
            if len(base_response['recommendations']) < count:
                logger.info("Not enough recommendations, fetching more candidates...")
                # 获取更多候选仓库
                more_repos = _get_trending_repos([])  # 不限制语言
                for repo in more_repos:
                    if len(base_response['recommendations']) >= count:
                        break
                    repo_full_name = repo.get('full_name')
                    if repo_full_name and \
                       repo_full_name not in [r['name'] for r in base_response['recommendations']]:
                        try:
                            similarity = calculate_user_repo_similarity(name, repo_full_name)
                            repo_info = get_repo_info(repo_full_name)
                            if repo_info:
                                base_response['recommendations'].append({
                                    'name': repo_full_name,
                                    'metrics': {
                                        'stars': repo_info.get('stargazers_count', 0),
                                        'forks': repo_info.get('forks_count', 0),
                                        'watchers': repo_info.get('watchers_count', 0),
                                        'size': repo_info.get('size', 0)
                                    },
                                    'similarity': max(0.1, similarity)
                                })
                        except Exception as e:
                            logger.error(f"Error processing additional repo {repo_full_name}: {str(e)}")

        elif type_str == 'repo':
            # 获取仓库信息
            repo_info = get_repo_info(name)
            if not repo_info:
                error_msg = f'仓库 {name} 不存在或无法访问'
                logger.warning(error_msg)
                base_response.update({
                    'status': 'error',
                    'message': error_msg
                })
                return base_response

            # 更新仓库指标
            base_response['metrics'].update({
                'stars': repo_info.get('stargazers_count', 0),
                'forks': repo_info.get('forks_count', 0),
                'watchers': repo_info.get('watchers_count', 0),
                'size': repo_info.get('size', 0)
            })

            if find == 'user':
                try:
                    # 获取仓库的贡献者
                    contributors = get_repo_contributors(name)
                    if not contributors:
                        error_msg = f'无法获取仓库 {name} 的贡献者信息，可能是由于 API 限制或网络问题'
                        logger.warning(error_msg)
                        base_response.update({
                            'status': 'error',
                            'message': error_msg
                        })
                        return base_response

                    # 获取活跃用户作为备选
                    active_users = get_active_users()
                    if not active_users:
                        error_msg = '无法获取活跃用户列表，可能是由于 API 限制或网络问题'
                        logger.warning(error_msg)
                        base_response.update({
                            'status': 'error',
                            'message': error_msg
                        })
                        return base_response

                    # 合并候选用户列表
                    candidates = list(set([user['login'] for user in contributors] + [user['login'] for user in active_users]))
                    if not candidates:
                        error_msg = '未找到合适的推荐用户'
                        logger.warning(error_msg)
                        base_response.update({
                            'status': 'error',
                            'message': error_msg
                        })
                        return base_response

                    # 计算相似度
                    similarities = []
                    for candidate in candidates[:count]:
                        try:
                            similarity = calculate_user_repo_similarity(candidate, name)
                            if similarity > 0:
                                similarities.append((candidate, similarity))
                        except Exception as e:
                            logger.error(f"Error calculating similarity for {candidate}: {str(e)}")

                    # 排序并返回结果
                    similarities.sort(key=lambda x: x[1], reverse=True)
                    for user, similarity in similarities[:count]:
                        try:
                            user_info = get_user_info(user)
                            if user_info:
                                base_response['recommendations'].append({
                                    'name': user,
                                    'metrics': {
                                        'followers': user_info.get('followers', 0),
                                        'following': user_info.get('following', 0),
                                        'public_repos': user_info.get('public_repos', 0)
                                    },
                                    'similarity': similarity
                                })
                        except Exception as e:
                            logger.error(f"Error getting info for user {user}: {str(e)}")

                except Exception as e:
                    error_msg = f'推荐用户时发生错误: {str(e)}'
                    logger.error(error_msg)
                    base_response.update({
                        'status': 'error',
                        'message': error_msg
                    })
                    return base_response

            elif find == 'repo':
                try:
                    # 获取相似语言的热门仓库
                    trending_repos = _get_trending_repos([repo_info.get('language')])
                    if not trending_repos:
                        error_msg = '无法获取热门仓库列表，可能是由于 API 限制或网络问题'
                        logger.warning(error_msg)
                        base_response.update({
                            'status': 'error',
                            'message': error_msg
                        })
                        return base_response

                    # 计算相似度
                    similarities = []
                    for repo in trending_repos:
                        repo_full_name = repo.get('full_name')
                        if repo_full_name and repo_full_name != name:  # 排除自己
                            try:
                                similarity = calculate_repo_repo_similarity(name, repo_full_name)
                                # 移除相似度大于0的限制，保留所有结果
                                similarities.append((repo_full_name, similarity))
                            except Exception as e:
                                logger.error(f"Error calculating similarity for {repo_full_name}: {str(e)}")

                    # 排序并返回结果
                    similarities.sort(key=lambda x: x[1], reverse=True)
                    # 确保获取足够数量的推荐结果
                    for repo_name, similarity in similarities[:count]:
                        try:
                            repo_info = get_repo_info(repo_name)
                            if repo_info:
                                base_response['recommendations'].append({
                                    'name': repo_name,
                                    'metrics': {
                                        'stars': repo_info.get('stargazers_count', 0),
                                        'forks': repo_info.get('forks_count', 0),
                                        'watchers': repo_info.get('watchers_count', 0),
                                        'size': repo_info.get('size', 0)
                                    },
                                    'similarity': max(0.1, similarity)  # 确保最小相似度为0.1
                                })
                        except Exception as e:
                            logger.error(f"Error getting info for repo {repo_name}: {str(e)}")

                    # 如果推荐结果不足，尝试获取更多候选仓库
                    if len(base_response['recommendations']) < count:
                        logger.info("Not enough recommendations, fetching more candidates...")
                        # 获取更多候选仓库
                        more_repos = _get_trending_repos([])  # 不限制语言
                        for repo in more_repos:
                            if len(base_response['recommendations']) >= count:
                                break
                            repo_full_name = repo.get('full_name')
                            if repo_full_name and repo_full_name != name and \
                               repo_full_name not in [r['name'] for r in base_response['recommendations']]:
                                try:
                                    similarity = calculate_repo_repo_similarity(name, repo_full_name)
                                    repo_info = get_repo_info(repo_full_name)
                                    if repo_info:
                                        base_response['recommendations'].append({
                                            'name': repo_full_name,
                                            'metrics': {
                                                'stars': repo_info.get('stargazers_count', 0),
                                                'forks': repo_info.get('forks_count', 0),
                                                'watchers': repo_info.get('watchers_count', 0),
                                                'size': repo_info.get('size', 0)
                                            },
                                            'similarity': max(0.1, similarity)
                                        })
                                except Exception as e:
                                    logger.error(f"Error processing additional repo {repo_full_name}: {str(e)}")

                except Exception as e:
                    error_msg = f'推荐仓库时发生错误: {str(e)}'
                    logger.error(error_msg)
                    base_response.update({
                        'status': 'error',
                        'message': error_msg
                    })
                    return base_response

        # 检查是否有推荐结果
        if not base_response['recommendations'] and base_response['status'] != 'error':
            error_msg = '未找到任何推荐结果'
            logger.warning(error_msg)
            base_response.update({
                'status': 'error',
                'message': error_msg
            })

        return base_response

    except Exception as e:
        logger.error(f"Error in recommend function: {str(e)}")
        return base_response

def process_recommendation(item_similarity: Tuple[str, float], find: str) -> Dict:
    """处理单个推荐结果（用于并行理）"""
    item, similarity = item_similarity
    if find == "user":
        scale = get_user_scale(item)
    else:
        scale = get_repo_scale(item)
    return {
        "name": item,
        "similarity": similarity,
        "scale": scale
    }

def main(type_str: str, name: str, find: str):
    """主函数使用并行处理）"""
    try:
        # 获取推荐结果
        recommendations = recommend(type_str, name, find)
        
        # 并行处理推荐结果
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            final_results = list(executor.map(
                lambda x: process_recommendation(x, find),
                recommendations
            ))
        
        # 输出结果
        print(json.dumps(final_results, indent=2))
        
    except Exception as e:
        print(f"Error: {str(e)}")

def analyze_with_llm(node_a: str, node_b: str) -> str:
    """用大模型分析两个节点间的关系"""
    url = "https://spark-api-open.xf-yun.com/v1/chat/completions"
    data = {
        "max_tokens": 4096,
        "top_k": 4,
        "temperature": 0.5,
        "messages": [
            {
                "role": "system",
                "content": "你是一个致力于维护github开源社区的工作员，你的职责是分析用户和项目之间的相似点，目标是促进协作和技术交流。对于两个github仓库：分析它们的相似之处，目的是找到能够吸引一个仓库的贡献者愿意维护另一个仓库的理由对于两个用户：分析他们的偏好和术栈相似点，目的是促成他们成为好友并深入交流技术。对于一个用户和一个仓库：分析用户的偏好或技术栈与仓库特征的相似点，目的是说服用户参与该仓库的贡献。输出要求：不要用markdown的语法，你的回答必须是有序列表格式，每个列表项应包含清晰且详细的理由，在每个理由前标上序号。不需要任何叙性语句或解释，只需列出分析结果。语气务必坚定，确保每个理由都显得可信且具有说服力。请判断清楚2个主体分别是用户还是仓库。不要用markdown语法，请用没有格式的纯文本。"
            },
            {
                "role": "user",
                "content": f"请分析 {node_a} 和 {node_b}"
            }
        ],
        "model": "4.0Ultra",
        "stream": False
    }

    headers = {
        "Authorization": "Bearer MBxygdMlrkwHhPfBBwrJ:beWImlkiOrRHkYaLENCz"
    }

    try:
        response = requests.post(url, headers=headers, json=data)
        response.encoding = "utf-8"
        result = response.json()
        content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
        return content
    except Exception as e:
        logger.error(f"LLM analysis failed: {str(e)}")
        return f"AI 分析失败: {str(e)}"

def _get_user_followers(username: str) -> List[Dict]:
    """获取用户的关注者"""
    session = get_session()
    response = session.get(
        f"{GITHUB_API}/users/{username}/followers",
        headers=headers
    )
    return response.json() if response.status_code == 200 else []

def _get_repo_contributors(owner: str, repo: str) -> List[Dict]:
    """获取仓库的贡献者"""
    session = get_session()
    response = session.get(
        f"{GITHUB_API}/repos/{owner}/{repo}/contributors",
        headers=headers
    )
    return response.json() if response.status_code == 200 else []

def _get_repo_dependencies(owner: str, repo: str) -> List[Dict]:
    """获取仓库的依赖"""
    session = get_session()
    response = session.get(
        f"{GITHUB_API}/repos/{owner}/{repo}/dependency-graph/dependencies",
        headers=headers
    )
    if response.status_code != 200:
        return []
    
    dependencies = []
    data = response.json()
    for dep in data.get('dependencies', []):
        if dep.get('package', {}).get('ecosystem') == 'github':
            dependencies.append({
                'name': dep['package']['name']
            })
    return dependencies

def batch_get_user_info(usernames: List[str], session: requests.Session) -> Dict[str, Dict]:
    """批量获取用户信息"""
    user_infos = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_to_username = {
            executor.submit(get_user_info, username): username
            for username in usernames
        }
        for future in concurrent.futures.as_completed(future_to_username):
            username = future_to_username[future]
            try:
                user_info = future.result()
                if user_info:
                    user_infos[username] = user_info
            except Exception:
                continue
    return user_infos

def get_newcomer_candidates(name: str, user_languages: Dict[str, int], session: requests.Session) -> Set[str]:
    """并行获取新手用户的候选人"""
    candidates = set()
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = []
        
        # 1. 获取导师
        if user_languages:
            main_language = max(user_languages.items(), key=lambda x: x[1])[0]
            mentor_query = f'language:{main_language} followers:>100 repos:>10'
            futures.append(
                executor.submit(
                    lambda: session.get(
                        f"{GITHUB_API}/search/users",
                        params={
                            'q': mentor_query,
                            'sort': 'followers',
                            'per_page': 10
                        }
                    ).json().get('items', []) if session.get(
                        f"{GITHUB_API}/search/users",
                        params={
                            'q': mentor_query,
                            'sort': 'followers',
                            'per_page': 10
                        }
                    ).status_code == 200 else []
                )
            )
            
            # 2. 获取同伴
            peer_query = f'language:{main_language} followers:10..50 repos:3..15'
            futures.append(
                executor.submit(
                    lambda: session.get(
                        f"{GITHUB_API}/search/users",
                        params={
                            'q': peer_query,
                            'sort': 'joined',
                            'per_page': 10
                        }
                    ).json().get('items', []) if session.get(
                        f"{GITHUB_API}/search/users",
                        params={
                            'q': peer_query,
                            'sort': 'joined',
                            'per_page': 10
                        }
                    ).status_code == 200 else []
                )
            )
            
            # 3. 获取star的项目贡献者
            futures.append(
                executor.submit(
                    lambda: session.get(
                        f"{GITHUB_API}/users/{name}/starred?per_page=3"
                    ).json() if session.get(
                        f"{GITHUB_API}/users/{name}/starred?per_page=3"
                    ).status_code == 200 else []
                )
            )
            
            # 处理所有结果
            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result()
                    if isinstance(result, list):
                        if 'login' in result[0]:  # 用户列表
                            candidates.update(user['login'] for user in result)
                        else:  # 仓库列表
                            for repo in result:
                                contributors = get_repo_contributors(repo['full_name'])[:5]
                                candidates.update(c['login'] for c in contributors)
                except Exception:
                    continue
    
    return candidates

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 4:
        print("Usage: python recommender.py <type> <name> <find>")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2], sys.argv[3])                                    