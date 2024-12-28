import requests
import json
from typing import List, Dict, Tuple, Any, Set, Callable, Optional
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
CACHE_SIZE = 512  # 将缓存大小增加到512
MAX_WORKERS = 20  # 增加最大并行线程数到20
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

# 2. 添加新的缓存装饰器用于API结果缓存
def cache_api_result(func):
    """自定义缓存装饰器,支持更复杂的缓存策略"""
    cache = {}
    lock = threading.Lock()
    
    def wrapper(*args, **kwargs):
        key = str(args) + str(kwargs)
        with lock:
            if key in cache:
                result, timestamp = cache[key]
                # 缓存1小时有效
                if time.time() - timestamp < 3600:
                    return result
                else:
                    del cache[key]
        
        result = func(*args, **kwargs)
        
        with lock:
            if len(cache) >= 1000:  # 最大缓存1000条
                # 删除最旧的20%缓存
                oldest = sorted(cache.items(), key=lambda x: x[1][1])[:200]
                for k, _ in oldest:
                    del cache[k]
            cache[key] = (result, time.time())
        
        return result
    
    return wrapper

# 3. 添加并行处理函数
def parallel_process(items: List[Any], process_func: Callable, max_workers: int = MAX_WORKERS) -> List[Any]:
    """并行处理通用函数"""
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_item = {executor.submit(process_func, item): item for item in items}
        for future in concurrent.futures.as_completed(future_to_item):
            try:
                result = future.result()
                if result is not None:
                    results.append(result)
            except Exception as e:
                logger.error(f"Error in parallel processing: {str(e)}")
    return results

# 4. 优化现有的API请求函数
@cache_api_result
def get_user_info_cached(username: str) -> Dict:
    """带高级缓存的用户信息获取"""
    return get_user_info(username)

@cache_api_result
def get_repo_info_cached(repo_full_name: str) -> Dict:
    """带高级缓存的仓库信息获取"""
    return get_repo_info(repo_full_name)

# 5. 添加批量处理函数
def batch_get_user_info(usernames: List[str]) -> Dict[str, Dict]:
    """批量获取用户信息"""
    def process_user(username: str) -> Tuple[str, Dict]:
        info = get_user_info_cached(username)
        return username, info if info else None
    
    results = parallel_process(usernames, process_user)
    return {username: info for username, info in results if info}

def batch_get_repo_info(repo_names: List[str]) -> Dict[str, Dict]:
    """批量获取仓库信息"""
    def process_repo(repo_name: str) -> Tuple[str, Dict]:
        info = get_repo_info_cached(repo_name)
        return repo_name, info if info else None
    
    results = parallel_process(repo_names, process_repo)
    return {repo_name: info for repo_name, info in results if info}

# 6. 优化recommend函数中的并发处理
def process_recommendations(candidates: List[str], find: str) -> List[Dict]:
    """并行处理推荐结果"""
    def process_candidate(candidate: str) -> Optional[Dict]:
        try:
            if find == 'user':
                user_info = get_user_info_cached(candidate)
                if not user_info:
                    return None
                    
                scale = get_user_scale(candidate)
                similarity = calculate_user_user_similarity(name, candidate)
                
                return {
                    'name': candidate,
                    'metrics': {
                        'followers': user_info.get('followers', 0),
                        'following': user_info.get('following', 0),
                        'public_repos': user_info.get('public_repos', 0),
                        'size': scale
                    },
                    'similarity': similarity
                }
            else:
                repo_info = get_repo_info_cached(candidate)
                if not repo_info:
                    return None
                    
                scale = get_repo_scale(candidate)
                similarity = calculate_repo_repo_similarity(name, candidate)
                
                return {
                    'name': candidate,
                    'metrics': {
                        'stars': repo_info.get('stargazers_count', 0),
                        'forks': repo_info.get('forks_count', 0),
                        'watchers': repo_info.get('watchers_count', 0),
                        'size': scale
                    },
                    'similarity': similarity
                }
        except Exception as e:
            logger.error(f"Error processing candidate {candidate}: {str(e)}")
            return None
            
    return parallel_process(candidates, process_candidate)

# 7. 优化session管理
def get_optimized_session() -> requests.Session:
    """获取优化配置的session"""
    if not hasattr(thread_local, "session"):
        thread_local.session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=100,
            pool_maxsize=100,
            max_retries=3,
            pool_block=False
        )
        thread_local.session.mount('http://', adapter)
        thread_local.session.mount('https://', adapter)
    
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
def get_user_repos(username: str, max_repos: int = 20) -> List[Dict]:
    """获取用户的仓库列表(限制数量)"""
    session = get_session()
    try:
        # 设置5秒超时
        response = session.get(
            f"{GITHUB_API}/users/{username}/repos",
            headers=headers,
            params={'per_page': max_repos, 'sort': 'updated'},  # 只获取最近更新的前20个仓库
            timeout=5
        )
        return response.json() if response.status_code == 200 else []
    except Exception as e:
        logger.error(f"Error getting repos for user {username}: {str(e)}")
        return []

@lru_cache(maxsize=CACHE_SIZE)
def get_repo_contributors(repo_full_name: str, max_contributors: int = 20) -> List[Dict]:
    """获取仓库的贡献者(限制数量)"""
    session = get_session()
    try:
        # 设置5秒超时
        response = session.get(
            f"{GITHUB_API}/repos/{repo_full_name}/contributors",
            headers=headers,
            params={'per_page': max_contributors},  # 只获取前20个贡献者
            timeout=5
        )
        return response.json() if response.status_code == 200 else []
    except Exception as e:
        logger.error(f"Error getting contributors for repo {repo_full_name}: {str(e)}")
        return []

@lru_cache(maxsize=CACHE_SIZE)
def get_user_starred(username: str, max_stars: int = 10) -> List[Dict]:
    """获取用户star的仓库(限制数量)"""
    session = get_session()
    try:
        # 设置5秒超时
        response = session.get(
            f"{GITHUB_API}/users/{username}/starred",
            headers=headers,
            params={'per_page': max_stars},  # 只获取前10个star的���库
            timeout=5
        )
        return response.json() if response.status_code == 200 else []
    except Exception as e:
        logger.error(f"Error getting starred repos for user {username}: {str(e)}")
        return []

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
   计算用户规模指标（综合OpenRank、影响力、活跃度和贡献质量）
   返回范围：20-40
   """
   session = get_session()
   try:
       # 首先尝试获取OpenRank值
       openrank = get_openrank(username, 'user')
       
       # 如果有OpenRank值，使用新的计算方法
       if openrank is not None:
           # 获取用户基本信息
           user_info = get_user_info(username)
           if not user_info:
               return 20
               
           # 获取用户的仓库列表
           repos = get_user_repos(username)
           
           # 1. OpenRank指数 (0-1)
           # OpenRank通常在0-10之间，将其归一化到0-1
           openrank_score = min(1.0, openrank / 10)
           
           # 2. 社交影响力指数 (0-1)
           followers = user_info.get('followers', 0)
           social_impact = min(1.0, math.log(followers + 1) / math.log(10000))
           
           # 3. 仓库质量指数 (0-1)
           if repos:
               avg_stars = sum(repo.get('stargazers_count', 0) for repo in repos) / len(repos)
               avg_forks = sum(repo.get('forks_count', 0) for repo in repos) / len(repos)
               repo_quality = min(1.0, (math.log(avg_stars + 1) / math.log(1000) +
                                      math.log(avg_forks + 1) / math.log(500)) / 2)
           else:
               repo_quality = 0
           
           # 4. 活跃度指数 (0-1)
           public_repos = user_info.get('public_repos', 0)
           recent_repos = [repo for repo in repos
                          if (datetime.now() - datetime.strptime(repo.get('updated_at', ''), '%Y-%m-%dT%H:%M:%SZ')).days <= 365]
           activity_ratio = len(recent_repos) / public_repos if public_repos > 0 else 0
           activity_score = min(1.0, (math.log(public_repos + 1) / math.log(100)) * activity_ratio)
           
           # 5. 综合计算最终得分 (0-1)
           final_score = (openrank_score * 0.4 +
                         social_impact * 0.3 +
                         repo_quality * 0.15 +
                         activity_score * 0.15)
           
           # 6. 映射到20-40范围
           normalized_scale = 20 + final_score * 20
           
           return normalized_scale
       
       # 如果没有OpenRank值，使用原有计算方法
       else:
           # 保持原有的计算逻辑不变
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
    计算仓库规模指标（综合OpenRank、热度、活跃度和代码质量）
    返回范围：20-40
    """
    session = get_session()
    try:
        # 首先尝试获取OpenRank值
        openrank = get_openrank(repo_full_name, 'repo')
        
        # 如果有OpenRank值，使用新的计算方法
        if openrank is not None:
            # 获取仓库基本信息
            repo_info = get_repo_info(repo_full_name)
            if not repo_info:
                return 20
                
            # 1. OpenRank指数 (0-1)
            # OpenRank通常在0-10之间，将其归一化到0-1
            openrank_score = min(1.0, openrank / 10)
            
            # 2. 社区热度指数 (0-1)
            stars = repo_info.get('stargazers_count', 0)
            forks = repo_info.get('forks_count', 0)
            watchers = repo_info.get('watchers_count', 0)
            
            popularity_score = min(1.0, (
                math.log(stars + 1) / math.log(10000) * 0.5 +     
                math.log(forks + 1) / math.log(2000) * 0.3 +      
                math.log(watchers + 1) / math.log(1000) * 0.2     
            ) ** 1.2)
            
            # 3. 活跃度指数 (0-1)
            commits_url = f"{GITHUB_API}/repos/{repo_full_name}/stats/participation"
            response = session.get(commits_url, headers=headers)
            recent_commits = sum(response.json().get('all', [0] * 52)) if response.status_code == 200 else 0
            
            issues_url = f"{GITHUB_API}/repos/{repo_full_name}/issues?state=all&per_page=100"
            response = session.get(issues_url, headers=headers)
            recent_issues = len([i for i in response.json() if 
                               (datetime.now() - datetime.strptime(i.get('created_at', ''), '%Y-%m-%dT%H:%M:%SZ')).days <= 365]) if response.status_code == 200 else 0
            
            activity_score = min(1.0, (
                math.log(recent_commits + 1) / math.log(500) * 0.6 +     
                math.log(recent_issues + 1) / math.log(200) * 0.4        
            ) ** 1.3)
            
            # 4. 代码质量指数 (0-1)
            size = repo_info.get('size', 0)
            open_issues = repo_info.get('open_issues_count', 0)
            total_issues = recent_issues or 1
            issue_resolution_rate = 1 - (open_issues / total_issues)
            contributors = get_repo_contributors(repo_full_name)
            contributor_count = len(contributors)
            
            quality_score = min(1.0, (
                math.log(size + 1) / math.log(1000000) * 0.3 +        
                issue_resolution_rate * 0.4 +                            
                math.log(contributor_count + 1) / math.log(100) * 0.3    
            ) ** 1.2)
            
            # 5. 综合计算最终得分 (0-1)
            final_score = (
                openrank_score * 0.3 +          
                popularity_score * 0.3 +
                activity_score * 0.2 +          
                quality_score * 0.2             
            ) ** 1.2
            
            # 6. 映射到20-40范围
            normalized_scale = 20 + (final_score * 20)
            
            return min(40, normalized_scale)
            
        # 如果没有OpenRank值，使用原有计算方法
        else:
            # 保持原有的计算逻辑不变
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
                                math.log(contributor_count + 1) / math.log(100) * 0.3))  # 贡献者数量
            
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
    
    if not user_repos or not repo_info:
        return 0.1  # 返回一个基础相似度
    
    # 1. 语言匹配度 (30%)
    user_languages = defaultdict(int)
    for repo in user_repos:
        if repo['language']:
            user_languages[repo['language']] += 1
    total_repos = sum(user_languages.values())
    repo_language = repo_info.get('language', '')
    language_match = user_languages.get(repo_language, 0) / total_repos if total_repos > 0 else 0.1
    
    # 2. 主题匹配度 (30%)
    user_topics = set()
    for repo in user_repos:
        user_topics.update(repo.get('topics', []))
    repo_topics = set(repo_info.get('topics', []))
    # 降低主题匹配的要求
    topic_match = len(repo_topics.intersection(user_topics)) / max(len(repo_topics), 1) if repo_topics else 0.1
    
    # 3. 活跃度匹配 (40%)
    user_activity = len(user_repos)
    repo_activity = repo_info.get('stargazers_count', 0) + repo_info.get('forks_count', 0)
    # 使用对数尺度来平滑差异
    activity_match = 1 - abs(math.log(user_activity + 1) - math.log(repo_activity + 1)) / max(math.log(max(user_activity, repo_activity) + 1), 1)
    
    # 综合计�� (30% + 30% + 40%)
    similarity = 0.3 * language_match + 0.3 * topic_match + 0.4 * activity_match
    
    # 确保最小相似度
    return max(0.1, similarity)

def get_candidates_batch(repos: List[Dict], session: requests.Session, max_per_repo: int = 10) -> Set[str]:
    """批量获取仓库贡献者，增加多样性和实时性"""
    candidates = set()
    
    # 1. 从仓库贡献者获取候选人
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_to_repo = {
            executor.submit(get_repo_contributors, repo['full_name']): repo 
            for repo in repos[:5]  # 限制仓库数量以提高效率
        }
        for future in concurrent.futures.as_completed(future_to_repo):
            try:
                contributors = future.result()[:max_per_repo]
                candidates.update(c['login'] for c in contributors)
            except Exception:
                continue

    # 2. 从相似仓库获取候选人
    try:
        for repo in repos[:3]:  # 取前3个仓库
            similar_repos = get_similar_repos(repo['full_name'])[:3]  # 每个仓库取3个相似仓库
            for similar_repo in similar_repos:
                contributors = get_repo_contributors(similar_repo['full_name'])[:5]
                candidates.update(c['login'] for c in contributors)
    except Exception as e:
        logger.error(f"Error getting similar repos contributors: {str(e)}")

    # 3. 从最近活跃用户获取候选人
    try:
        for repo in repos[:2]:  # 取前2个仓库
            response = session.get(
                f"{GITHUB_API}/repos/{repo['full_name']}/events",
                params={'per_page': 10}
            )
            if response.status_code == 200:
                events = response.json()
                for event in events:
                    if event['type'] in ['PushEvent', 'PullRequestEvent', 'IssuesEvent']:
                        candidates.add(event['actor']['login'])
    except Exception as e:
        logger.error(f"Error getting recent active users: {str(e)}")

    # 4. 从trending用户获取候选人
    try:
        response = session.get(
            f"{GITHUB_API}/search/users",
            params={
                'q': f"language:{repos[0]['language']} followers:>10",
                'sort': 'joined',
                'order': 'desc',
                'per_page': 5
            }
        )
        if response.status_code == 200:
            trending_users = response.json().get('items', [])
            candidates.update(user['login'] for user in trending_users)
    except Exception as e:
        logger.error(f"Error getting trending users: {str(e)}")

    # 5. 从相关话题获取候选人
    try:
        topics = set()
        for repo in repos[:3]:
            topics.update(repo.get('topics', []))
        
        if topics:
            topic = random.choice(list(topics))
            response = session.get(
                f"{GITHUB_API}/search/repositories",
                params={
                    'q': f"topic:{topic}",
                    'sort': 'updated',
                    'order': 'desc',
                    'per_page': 3
                }
            )
            if response.status_code == 200:
                topic_repos = response.json().get('items', [])
                for repo in topic_repos:
                    contributors = get_repo_contributors(repo['full_name'])[:3]
                    candidates.update(c['login'] for c in contributors)
    except Exception as e:
        logger.error(f"Error getting topic related users: {str(e)}")

    return candidates

def recommend(type_str: str, name: str, find: str, count: Optional[int] = None) -> Dict:
    """推荐函数"""
    try:
        session = get_session()
        count = N if count is None else min(count, N)
        total_count = count * 5  # 增加总数以适应更多的连接节点
        
        # 增加推荐池规模
        user_scale = get_user_scale(name)
        base_pool_size = 100  # 最小池大小
        scale_factor = (user_scale - 20) * 5  # 保持不变
        pool_size = int(base_pool_size + scale_factor)
        pool_size = min(max(pool_size, 100), 200)  # 保持不变
        
        logger.info(f"Processing recommendation request: {type_str}/{name} -> {find}, count={count}, pool_size={pool_size}")
        
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
                                        node_type = 'mentor'    # ��相似度用户
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
            try:
                # 获取用户的仓库列表
                user_repos = get_user_repos(name)
                if not user_repos:
                    error_msg = f'无法获取用户 {name} 的仓库列表'
                    logger.warning(error_msg)
                    base_response.update({
                        'status': 'error',
                        'message': error_msg
                    })
                    return base_response

                # 获取用户的语言偏好
                languages = _get_language_preferences(user_repos)
                if not languages:
                    languages = ['JavaScript', 'Python', 'Java']
                    
                # 构建候选池
                candidates = set()
                
                # 1. 获取语言相关的热门仓库
                similar_repos_query = f'language:{languages[0]} stars:>100'
                response = session.get(
                    f"{GITHUB_API}/search/repositories",
                    params={
                        'q': similar_repos_query,
                        'sort': 'stars',
                        'per_page': pool_size
                    }
                )
                if response.status_code == 200:
                    candidates.update(repo['full_name'] for repo in response.json().get('items', []))
                    
                # 2. 获取用户star的仓库的相似仓库
                starred_repos = get_user_starred(name)
                for repo in starred_repos[:5]:  # 只使用前5个star的仓库
                    similar_repos = get_similar_repos(repo['full_name'])
                    candidates.update(r['full_name'] for r in similar_repos)
                    
                # 随机打乱候选列表
                candidates = list(candidates)
                random.shuffle(candidates)
                candidates = candidates[:pool_size]
                
                # 处理所有候选仓库
                all_recommendations = []
                with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
                    future_to_repo = {
                        executor.submit(
                            lambda r: (r, calculate_repo_similarity(name, r), get_repo_info(r), get_repo_scale(r)),
                            repo
                        ): repo for repo in candidates[:pool_size * 2]  # 处理更多候选仓库
                    }
                    
                    for future in concurrent.futures.as_completed(future_to_repo):
                        try:
                            repo_name, similarity, repo_info, scale = future.result()
                            if repo_info and similarity > 0:
                                # 根据相似度确定节点类型
                                if similarity >= 0.7:
                                    node_type = 'mentor'
                                elif similarity >= 0.4:
                                    node_type = 'peer'
                                else:
                                    node_type = 'floating'
                                    
                                all_recommendations.append({
                                    'name': repo_name,
                                    'metrics': {
                                        'stars': repo_info.get('stargazers_count', 0),
                                        'forks': repo_info.get('forks_count', 0),
                                        'watchers': repo_info.get('watchers_count', 0),
                                        'size': scale
                                    },
                                    'similarity': similarity,
                                    'nodeType': node_type
                                })
                        except Exception as e:
                            logger.error(f"Error processing repo {repo_name}: {str(e)}")
                
                # 分离不同类型的节点
                mentor_nodes = [r for r in all_recommendations if r['nodeType'] == 'mentor']
                peer_nodes = [r for r in all_recommendations if r['nodeType'] == 'peer']
                floating_nodes = [r for r in all_recommendations if r['nodeType'] == 'floating']
                
                # 选择最终结果
                final_recommendations = []
                
                # 1. 添加核心节点（mentor + peer）
                core_nodes = sorted(mentor_nodes + peer_nodes, key=lambda x: x['similarity'], reverse=True)
                final_recommendations.extend(core_nodes[:count])
                
                # 2. 添加漂浮节点（与其他模式保持一致的比例）
                random.shuffle(floating_nodes)
                floating_count = max(count, len(core_nodes))  # 至少与核心节点数量相等
                final_recommendations.extend(floating_nodes[:floating_count])
                
                base_response['recommendations'] = final_recommendations
                
            except Exception as e:
                error_msg = f'推荐仓库时发生错误: {str(e)}'
                logger.error(error_msg)
                base_response.update({
                    'status': 'error',
                    'message': error_msg
                })
                return base_response

        elif type_str == 'repo' and find == 'user':
            try:
                # 根据仓库规模计算推荐池大小
                repo_scale = get_repo_scale(name)
                base_pool_size = 40  # 基础池大小
                scale_factor = (repo_scale - 20) * 2  # 根据规模调整因子
                pool_size = int(base_pool_size + scale_factor)
                pool_size = min(max(pool_size, 40), 80)  # 限制在40-80范围内
                
                logger.info(f"Repository scale: {repo_scale}, pool_size: {pool_size}")
                
                # 获取仓库的贡献者和相关用户
                contributors = get_repo_contributors(name)
                if not contributors:
                    error_msg = f'无法获取仓库 {name} 的贡献者信息'
                    logger.warning(error_msg)
                    base_response.update({
                        'status': 'error',
                        'message': error_msg
                    })
                    return base_response

                # 获取活跃用户作为备选
                active_users = get_active_users()
                if not active_users:
                    error_msg = '无法获取活跃用户列表'
                    logger.warning(error_msg)
                    base_response.update({
                        'status': 'error',
                        'message': error_msg
                    })
                    return base_response

                # 合并候选用户列表并随机打乱
                candidates = list(set([user['login'] for user in contributors] + 
                            [user['login'] for user in active_users]))
                random.shuffle(candidates)
                candidates = candidates[:pool_size * 2]  # 获取2倍的候选用户

                # 处理所有候选用户
                all_recommendations = []
                with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
                    future_to_user = {
                        executor.submit(
                            lambda u: (u, calculate_user_repo_similarity(u, name), get_user_info(u), get_user_scale(u)),
                            user
                        ): user for user in candidates[:pool_size]  # 使用计算出的pool_size
                    }
                    
                    for future in concurrent.futures.as_completed(future_to_user):
                        try:
                            user_name, similarity, user_info, scale = future.result()
                            if user_info:  # 移除 similarity > 0 的条件，允许低相似度的用户作为漂浮节点
                                # 根据相似度确定节点类型
                                if similarity >= 0.7:
                                    node_type = 'mentor'
                                elif similarity >= 0.4:
                                    node_type = 'peer'
                                else:
                                    node_type = 'floating'  # 低相似度的用户作为漂浮节点
                                    
                                all_recommendations.append({
                                    'name': user_name,
                                    'metrics': {
                                        'followers': user_info.get('followers', 0),
                                        'following': user_info.get('following', 0),
                                        'public_repos': user_info.get('public_repos', 0),
                                        'size': scale
                                    },
                                    'similarity': max(0.1, similarity),  # 确保最小相似度为0.1
                                    'nodeType': node_type
                                })
                        except Exception as e:
                            logger.error(f"Error processing user {user_name}: {str(e)}")

                # 分离不同类型的节点
                mentor_nodes = [r for r in all_recommendations if r['nodeType'] == 'mentor']
                peer_nodes = [r for r in all_recommendations if r['nodeType'] == 'peer']
                floating_nodes = [r for r in all_recommendations if r['nodeType'] == 'floating']
                
                # 选择最终结果
                final_recommendations = []
                
                # 1. 添加核心节点（mentor + peer）
                core_nodes = sorted(mentor_nodes + peer_nodes, key=lambda x: x['similarity'], reverse=True)
                final_recommendations.extend(core_nodes[:count])
                
                # 2. 添加漂浮节点（与其他模式保持一致的比例）
                random.shuffle(floating_nodes)
                floating_count = max(count, len(core_nodes))  # 至少与核心节点数量相等
                final_recommendations.extend(floating_nodes[:floating_count])
                
                base_response['recommendations'] = final_recommendations

            except Exception as e:
                error_msg = f'推荐用户时发生错误: {str(e)}'
                logger.error(error_msg)
                base_response.update({
                    'status': 'error',
                    'message': error_msg
                })

        elif type_str == 'repo' and find == 'repo':
            try:
                # 根据仓库规模计算推荐池大小
                repo_scale = get_repo_scale(name)
                base_pool_size = 40  # 基础池大小
                scale_factor = (repo_scale - 20) * 2  # 根据规模调整因子
                pool_size = int(base_pool_size + scale_factor)
                pool_size = min(max(pool_size, 40), 80)  # 限制在40-80范围内
                
                logger.info(f"Repository scale: {repo_scale}, pool_size: {pool_size}")
                
                # 获取相似语言的热门仓库
                repo_info = get_repo_info(name)
                if not repo_info:
                    error_msg = f'仓库 {name} 不存在或无法访问'
                    logger.warning(error_msg)
                    base_response.update({
                        'status': 'error',
                        'message': error_msg
                    })
                    return base_response
                    
                # 获取候选仓库
                candidates = set()
                
                # 1. 获取相同语言的热门仓库
                similar_repos_query = f'language:{repo_info.get("language", "")} stars:>10'
                response = session.get(
                    f"{GITHUB_API}/search/repositories",
                    params={
                        'q': similar_repos_query,
                        'sort': 'stars',
                        'per_page': pool_size * 2
                    }
                )
                if response.status_code == 200:
                    candidates.update(repo['full_name'] for repo in response.json().get('items', []))
                    
                # 2. 获取相关主题的仓库
                for topic in repo_info.get('topics', []):
                    topic_query = f'topic:{topic} stars:>10'
                    response = session.get(
                        f"{GITHUB_API}/search/repositories",
                        params={
                            'q': topic_query,
                            'sort': 'updated',
                            'per_page': pool_size
                        }
                    )
                    if response.status_code == 200:
                        candidates.update(repo['full_name'] for repo in response.json().get('items', []))
                
                # 随机打乱候选列表
                candidates = list(candidates - {name})  # 排除自身
                random.shuffle(candidates)
                candidates = candidates[:pool_size * 2]  # 获取2倍的候选仓库
                
                # 处理所有候选仓库
                all_recommendations = []
                with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
                    future_to_repo = {
                        executor.submit(
                            lambda r: (r, calculate_repo_repo_similarity(name, r), get_repo_info(r), get_repo_scale(r)),
                            repo
                        ): repo for repo in candidates[:pool_size]  # 使用计算出的pool_size
                    }
                    
                    for future in concurrent.futures.as_completed(future_to_repo):
                        try:
                            repo_name, similarity, repo_info, scale = future.result()
                            if repo_info:  # 移除 similarity > 0 的条件
                                # 根据相似度确定节点类型
                                if similarity >= 0.7:
                                    node_type = 'mentor'
                                elif similarity >= 0.4:
                                    node_type = 'peer'
                                else:
                                    node_type = 'floating'  # 低相似度的仓库作为漂浮节点
                                    
                                all_recommendations.append({
                                    'name': repo_name,
                                    'metrics': {
                                        'stars': repo_info.get('stargazers_count', 0),
                                        'forks': repo_info.get('forks_count', 0),
                                        'watchers': repo_info.get('watchers_count', 0),
                                        'size': scale
                                    },
                                    'similarity': max(0.1, similarity),  # 确保最小相似度为0.1
                                    'nodeType': node_type
                                })
                        except Exception as e:
                            logger.error(f"Error processing repo {repo_name}: {str(e)}")
                
                # 分离不同类型的节点
                mentor_nodes = [r for r in all_recommendations if r['nodeType'] == 'mentor']
                peer_nodes = [r for r in all_recommendations if r['nodeType'] == 'peer']
                floating_nodes = [r for r in all_recommendations if r['nodeType'] == 'floating']
                
                # 选择最终结果
                final_recommendations = []
                
                # 1. 添加核心节点（mentor + peer）
                core_nodes = sorted(mentor_nodes + peer_nodes, key=lambda x: x['similarity'], reverse=True)
                final_recommendations.extend(core_nodes[:count])
                
                # 2. 添加漂浮节点（与其他模式保持一致的比例）
                random.shuffle(floating_nodes)
                floating_count = max(count, len(core_nodes))  # 至少与核心节点数量相等
                final_recommendations.extend(floating_nodes[:floating_count])
                
                base_response['recommendations'] = final_recommendations
                
            except Exception as e:
                error_msg = f'推荐仓库时发生错误: {str(e)}'
                logger.error(error_msg)
                base_response.update({
                    'status': 'error',
                    'message': error_msg
                })

        # 检查是否有推荐结果
        if not base_response['recommendations'] and base_response['status'] != 'error':
            error_msg = '未找到任何推荐结果'
            logger.warning(error_msg)
            base_response.update({
                'status': 'error',
                'message': error_msg
            })

        # 修改节点处理逻辑
        if total_count > 0:
            # 随机打乱所有推荐结果
            random.shuffle(all_recommendations)
            
            # 根据节点大小分类
            large_nodes = []    # size >= 33
            medium_nodes = []   # 25 <= size < 33
            small_nodes = []    # size < 25
            
            for item in all_recommendations:
                node_size = item['metrics'].get('size', 20)
                if node_size >= 33:
                    large_nodes.append(item)
                elif node_size >= 25:
                    medium_nodes.append(item)
                else:
                    small_nodes.append(item)
            
            # 随机打乱每个类别内的节点
            random.shuffle(large_nodes)
            random.shuffle(medium_nodes)
            random.shuffle(small_nodes)
            
            # 选择核心节点（mentor + peer）
            core_nodes = []
            
            # 从大规模节点中选择 mentor 节点（6-10个）
            mentor_count = min(len(large_nodes), max(6, min(10, count // 3)))
            for item in large_nodes[:mentor_count]:
                item['nodeType'] = 'mentor'
                core_nodes.append(item)
            
            # 从中等规模节点中选择 peer 节点（9-15个）
            peer_count = min(len(medium_nodes), max(9, min(15, count // 2)))
            for item in medium_nodes[:peer_count]:
                item['nodeType'] = 'peer'
                core_nodes.append(item)
            
            # 确保连接节点总数在15-25个之间
            total_connected = len(core_nodes)
            if total_connected < 15:
                # 如果连接节点不足15个，从剩余节点中补充
                remaining = large_nodes[mentor_count:] + medium_nodes[peer_count:]
                random.shuffle(remaining)
                for item in remaining[:15-total_connected]:
                    item['nodeType'] = 'peer'  # 默认作为peer节点
                    core_nodes.append(item)
            elif total_connected > 25:
                # 如果超过25个，随机移除一些
                random.shuffle(core_nodes)
                core_nodes = core_nodes[:25]
            
            # 增加漂浮节点（10-20个）
            floating_nodes = []
            remaining_slots = max(10, min(20, pool_size - len(core_nodes)))
            
            # 合并所有可用的漂浮节点并随机打乱
            potential_floating = [n for n in all_recommendations if n not in core_nodes]
            random.shuffle(potential_floating)
            
            for item in potential_floating[:remaining_slots]:
                item['nodeType'] = 'floating'
                floating_nodes.append(item)
            
            # 合并最终结果
            final_recommendations = core_nodes + floating_nodes
            
            base_response['recommendations'] = final_recommendations

        return base_response

    except Exception as e:
        logger.error(f"Error in recommend: {str(e)}")
        return None

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

def get_openrank(name: str, type: str = 'repo') -> float:
    """
    从OpenDigger获取OpenRank值
    :param name: 用户名或仓库全名
    :param type: 'repo' 或 'user'
    :return: OpenRank值，如果不存在返回None
    """
    try:
        # 构建API URL
        if type == 'repo':
            url = f"{OPENDIGGER_API}/{name}/openrank.json"
        else:
            url = f"{OPENDIGGER_API}/users/{name}/openrank.json"
            
        response = requests.get(url)
        if response.status_code != 200:
            return None
            
        data = response.json()
        if not data:
            return None
            
        # 获取最近一个月的OpenRank值
        latest_month = max(data.keys())
        return data[latest_month]
        
    except Exception as e:
        logger.error(f"Error fetching OpenRank for {name}: {str(e)}")
        return None

def calculate_repo_similarity(user_name: str, repo_name: str) -> float:
    """计算用户和仓库之间的相似度"""
    try:
        # 获取用户信息和仓库信息
        user_repos = get_user_repos(user_name)
        repo_info = get_repo_info(repo_name)
        
        if not user_repos or not repo_info:
            return 0.0
            
        # 1. 语言相似度 (0.4)
        user_languages = _get_language_preferences(user_repos)
        repo_language = repo_info.get('language')
        language_score = 0.4 if repo_language in user_languages else 0.0
        
        # 2. 主题相似度 (0.3)
        user_topics = set()
        for repo in user_repos:
            user_topics.update(repo.get('topics', []))
        repo_topics = set(repo_info.get('topics', []))
        topic_score = 0.3 * len(user_topics & repo_topics) / max(1, len(repo_topics)) if repo_topics else 0
        
        # 3. 规模匹配度 (0.3)
        user_scale = get_user_scale(user_name)
        repo_scale = get_repo_scale(repo_name)
        scale_diff = abs(user_scale - repo_scale) / 40  # 归一化差异
        scale_score = 0.3 * (1 - min(scale_diff, 1))
        
        return language_score + topic_score + scale_score
        
    except Exception as e:
        logger.error(f"Error calculating repo similarity: {str(e)}")
        return 0.0

def get_repo_scale(repo_name: str) -> float:
    """计算仓库规模指标"""
    try:
        repo_info = get_repo_info(repo_name)
        if not repo_info:
            return 20.0
            
        # 获取OpenRank值
        openrank = get_openrank(repo_name, 'repo')
        
        if openrank:
            # 如果有OpenRank，使用OpenRank为主的计算方式
            stars = repo_info.get('stargazers_count', 0)
            forks = repo_info.get('forks_count', 0)
            
            # 计算活跃度 (0-1)
            last_update = repo_info.get('updated_at', '')
            is_active = last_update.startswith('2023') or last_update.startswith('2024')
            activity_score = 1.0 if is_active else 0.5
            
            # 计算规模分数 (20-40)
            base_score = 20 + openrank * 20
            
            # 根据stars和forks适当调整
            star_factor = min(1, math.log(stars + 1) / math.log(10000))
            fork_factor = min(1, math.log(forks + 1) / math.log(1000))
            
            final_score = base_score * (1 + star_factor * 0.2 + fork_factor * 0.1) * activity_score
            return min(max(final_score, 20), 40)
            
        else:
            # 如果没有OpenRank，使用传统指标
            stars = repo_info.get('stargazers_count', 0)
            forks = repo_info.get('forks_count', 0)
            watchers = repo_info.get('watchers_count', 0)
            
            # 计算基础分数
            star_score = min(1, math.log(stars + 1) / math.log(10000))
            fork_score = min(1, math.log(forks + 1) / math.log(1000))
            watcher_score = min(1, math.log(watchers + 1) / math.log(1000))
            
            # 综合计算
            base_score = (star_score * 0.5 + fork_score * 0.3 + watcher_score * 0.2)
            
            # 映射到20-40范围
            return 20 + base_score * 20
            
    except Exception as e:
        logger.error(f"Error calculating repo scale: {str(e)}")
        return 20.0

def get_similar_repos(repo_full_name: str) -> List[Dict]:
    """获取与指定仓库相似的仓库列表"""
    session = get_session()
    try:
        # 获取仓库信息
        repo_info = get_repo_info(repo_full_name)
        if not repo_info:
            return []
            
        # 获取仓库的语言和主题
        language = repo_info.get('language', '')
        topics = repo_info.get('topics', [])
        
        # 构建查询条件
        query_parts = []
        if language:
            query_parts.append(f'language:{language}')
        if topics:
            # 最多使用前3个主题
            for topic in topics[:3]:
                query_parts.append(f'topic:{topic}')
        
        # 添加基本条件
        query_parts.append('stars:>10')
        
        # 组合查询条件
        query = ' '.join(query_parts)
        
        # 搜索相似仓库
        response = session.get(
            f"{GITHUB_API}/search/repositories",
            params={
                'q': query,
                'sort': 'stars',
                'order': 'desc',
                'per_page': 10
            }
        )
        
        if response.status_code != 200:
            return []
            
        # 过滤掉原仓库
        results = []
        for repo in response.json().get('items', []):
            if repo.get('full_name') != repo_full_name:
                results.append(repo)
                
        return results[:10]  # 返回最多10个相似仓库
        
    except Exception as e:
        logger.error(f"Error getting similar repos for {repo_full_name}: {str(e)}")
        return []

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 4:
        print("Usage: python recommender.py <type> <name> <find>")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2], sys.argv[3])                                    