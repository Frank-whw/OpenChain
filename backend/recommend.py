import requests
import json
from typing import List, Dict, Tuple, Any, Set, Optional
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

def verify_github_token(token: str) -> bool:
    """验证GitHub Token的有效性"""
    try:
        session = requests.Session()
        session.headers.update({
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        })
        response = session.get(f"{GITHUB_API}/user")
        if response.status_code == 200:
            user_data = response.json()
            logger.info(f"Token verified successfully for user: {user_data.get('login')}")
            return True
        else:
            logger.error(f"Token verification failed with status code: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"Error verifying token: {str(e)}")
        return False

class TokenManager:
    def __init__(self):
        self.tokens = []
        self.current_index = 0
        self._lock = threading.Lock()
        
        # 验证所有token
        for token in GITHUB_TOKENS:
            if verify_github_token(token):
                self.tokens.append(token)
        
        if not self.tokens:
            raise RuntimeError("No valid GitHub tokens available")
            
        logger.info(f"TokenManager initialized with {len(self.tokens)} valid tokens")

    def get_token(self):
        """获取下一个token"""
        with self._lock:
            if not self.tokens:
                raise RuntimeError("No valid GitHub tokens available")
            token = self.tokens[self.current_index]
            self.current_index = (self.current_index + 1) % len(self.tokens)
            return token

    def remove_invalid_token(self, token: str):
        """移除无效的token"""
        with self._lock:
            if token in self.tokens:
                self.tokens.remove(token)
                logger.warning(f"Removed invalid token, {len(self.tokens)} tokens remaining")
                if not self.tokens:
                    raise RuntimeError("No valid GitHub tokens available")

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

def get_trending_repos() -> List[Dict]:
    """获取GitHub趋势仓库作为备选"""
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

def get_user_info(username: str) -> Dict:
    """获取用户信息"""
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
                rate_limits = check_rate_limit()
                if rate_limits:
                    remaining = rate_limits.get('rate', {}).get('remaining', 0)
                    reset_time = datetime.fromtimestamp(rate_limits.get('rate', {}).get('reset', 0))
                    logger.error(f"API rate limit exceeded. Remaining: {remaining}, Reset at: {reset_time}")
                time.sleep(2)
                continue
                
            if response.status_code == 200:
                user_data = response.json()
                # 验证返回的数据包含必要的字段
                required_fields = ['login', 'followers', 'following', 'public_repos']
                if all(key in user_data for key in required_fields):
                    logger.info(f"Successfully fetched user info for: {username}")
                    return user_data
                else:
                    missing_fields = [field for field in required_fields if field not in user_data]
                    logger.error(f"Incomplete user data received for {username}. Missing fields: {missing_fields}")
                    return None
            
            logger.error(f"Unexpected response status: {response.status_code} for user {username}")
            logger.error(f"Response content: {response.text}")
            
        except requests.exceptions.Timeout:
            logger.error(f"Request timeout for user {username} (attempt {attempt + 1}/{max_retries})")
            if attempt < max_retries - 1:
                time.sleep(2)
            continue
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for user {username} (attempt {attempt + 1}/{max_retries}): {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(2)
            continue
        except Exception as e:
            logger.error(f"Unexpected error for user {username}: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(2)
            continue
    
    logger.error(f"All attempts failed for user: {username}")
    return None

def get_repo_info(repo_full_name: str) -> Optional[Dict[str, Any]]:
    """获取仓库信息"""
    session = get_session()
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Fetching repo info for: {repo_full_name} (attempt {attempt + 1}/{max_retries})")
            response = session.get(
                f"{GITHUB_API}/repos/{repo_full_name}",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 404:
                logger.warning(f"Repository not found: {repo_full_name}")
                return None
            
            if response.status_code == 403:
                rate_limits = check_rate_limit()
                if rate_limits:
                    remaining = rate_limits.get('rate', {}).get('remaining', 0)
                    reset_time = datetime.fromtimestamp(rate_limits.get('rate', {}).get('reset', 0))
                    logger.error(f"API rate limit exceeded. Remaining: {remaining}, Reset at: {reset_time}")
                time.sleep(2)
                continue
                
            if response.status_code == 200:
                repo_info = response.json()
                # 验证返回的数据包含必要的字段
                required_fields = ['full_name', 'stargazers_count', 'forks_count', 'watchers_count', 'size']
                if all(key in repo_info for key in required_fields):
                    # 规范化处理 size 值
                    raw_size = repo_info.get('size', 0)
                    # 使用对数函数将 size 映射到 20-36 范围
                    normalized_size = 20 + min(16, math.log(raw_size + 1, 10) * 4) if raw_size > 0 else 20
                    repo_info['size'] = normalized_size
                    
                    logger.info(f"Successfully fetched repo info for: {repo_full_name}")
                    return repo_info
                else:
                    missing_fields = [field for field in required_fields if field not in repo_info]
                    logger.error(f"Incomplete repo data received for {repo_full_name}. Missing fields: {missing_fields}")
                    return None
            
            logger.error(f"Unexpected response status: {response.status_code} for repo {repo_full_name}")
            logger.error(f"Response content: {response.text}")
            
        except requests.exceptions.Timeout:
            logger.error(f"Request timeout for repo {repo_full_name} (attempt {attempt + 1}/{max_retries})")
            if attempt < max_retries - 1:
                time.sleep(2)
            continue
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for repo {repo_full_name} (attempt {attempt + 1}/{max_retries}): {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(2)
            continue
        except Exception as e:
            logger.error(f"Unexpected error for repo {repo_full_name}: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(2)
            continue
    
    logger.error(f"All attempts failed for repo: {repo_full_name}")
    return None

def get_user_repos(username: str) -> List[Dict]:
    """获取用户的仓库列表（只获取第一页，提高速度）"""
    session = get_session()
    response = session.get(
        f"{GITHUB_API}/users/{username}/repos",
        headers=headers,
        params={"per_page": 100}  # 只获取前100个仓库
    )
    return response.json() if response.status_code == 200 else []

def get_repo_contributors(repo_full_name: str) -> List[Dict]:
    """获取仓库的贡献者列表（只获取第一页）"""
    session = get_session()
    response = session.get(
        f"{GITHUB_API}/repos/{repo_full_name}/contributors",
        headers=headers,
        params={"per_page": 100}  # 只获取前100个贡献者
    )
    return response.json() if response.status_code == 200 else []

def get_active_users() -> List[Dict]:
    """获取活跃用户作为备选"""
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

def get_repo_scale(repo_full_name: str) -> float:
    """
    计算仓库规模指标（综合OpenRank、热度、活跃度和代码质量）
    返回范围：20-36
    """
    session = get_session()
    try:
        # 首先尝试获取OpenRank值
        openrank = get_openrank(repo_full_name, 'repo')
        
        # 如果有OpenRank值���使用新的计算方法
        if openrank is not None:
            # 获取仓库基本信息
            repo_info = get_repo_info(repo_full_name)
            if not repo_info:
                return 20
                
            # 1. OpenRank指数 (0-1)
            # OpenRank通常在0-10之间，将其归一化到0-1，使用更严格的归一化
            openrank_score = min(1.0, (openrank / 20) ** 1.5)  # 使用更大的除数和指数
            
            # 2. 社区热度指数 (0-1)
            stars = repo_info.get('stargazers_count', 0)
            forks = repo_info.get('forks_count', 0)
            watchers = repo_info.get('watchers_count', 0)
            
            # 大幅降低热度指标的阈值，使用对数函数进行归一化
            popularity_score = min(1.0, (
                math.log(stars + 1) / math.log(10000) * 0.5 +     # 进一步降低star值
                math.log(forks + 1) / math.log(2000) * 0.3 +      # 进一步降低fork阈值
                math.log(watchers + 1) / math.log(1000) * 0.2     # 进一步降低watcher阈值
            ) ** 1.2)  # 使用指数进一步压缩大值
            
            # 3. 活跃度指数 (0-1)
            commits_url = f"{GITHUB_API}/repos/{repo_full_name}/stats/participation"
            response = session.get(commits_url, headers=headers)
            recent_commits = sum(response.json().get('all', [0] * 52)) if response.status_code == 200 else 0
            
            issues_url = f"{GITHUB_API}/repos/{repo_full_name}/issues?state=all&per_page=100"
            response = session.get(issues_url, headers=headers)
            recent_issues = len([i for i in response.json() if 
                               (datetime.now() - datetime.strptime(i.get('created_at', ''), '%Y-%m-%dT%H:%M:%SZ')).days <= 365]) if response.status_code == 200 else 0
            
            # 大幅降低活跃度指标的阈值，使用对数函数进行归��化
            activity_score = min(1.0, (
                math.log(recent_commits + 1) / math.log(500) * 0.6 +     # 进一步降低commit阈值
                math.log(recent_issues + 1) / math.log(200) * 0.4        # 进一步降低issue阈值
            ) ** 1.3)  # 使用指数进一步压缩大值
            
            # 4. 代码质量指数 (0-1)
            size = repo_info.get('size', 0)  # 这里的 size 已经是规范化后的值
            open_issues = repo_info.get('open_issues_count', 0)
            total_issues = recent_issues or 1
            issue_resolution_rate = 1 - (open_issues / total_issues)
            contributors = get_repo_contributors(repo_full_name)
            contributor_count = len(contributors)
            
            # 大幅降低质量指标的阈值，使用对数函数进行归一化
            quality_score = min(1.0, (
                ((size - 20) / 16) * 0.3 +                              # 使用规范化后的 size
                issue_resolution_rate * 0.4 +
                math.log(contributor_count + 1) / math.log(100) * 0.3    # 进一步降低贡献者阈值
            ) ** 1.2)  # 使用指数进一步压缩大值
            
            # 5. 综合计算最终得分 (0-1)
            final_score = (
                openrank_score * 0.3 +          # 降低OpenRank权重
                popularity_score * 0.3 +
                activity_score * 0.2 +          # 提高活跃度权重
                quality_score * 0.2             # 提高质量权重
            ) ** 1.2  # 使用指数进一步压缩大值
            
            # 6. 使用更平缓的映射函数，确保不会超过36
            normalized_scale = 20 + (final_score * 16)  # 线性映射到20-36范围
            
            return min(36, normalized_scale)  # 确保不会超过36
            
    except Exception as e:
        logger.error(f"Error calculating repo scale for {repo_full_name}: {str(e)}")
        return 20

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
           # 权重分配：OpenRank(0.4) + 社交影响力(0.3) + 仓库质量(0.15) + 活跃度(0.15)
           final_score = (openrank_score * 0.4 +
                         social_impact * 0.3 +
                         repo_quality * 0.15 +
                         activity_score * 0.15)
           
           # 6. 映射到20-40范围
           normalized_scale = 20 + final_score * 20
           
           return normalized_scale
       
       # 如果没有OpenRank值，使用原有计算方法
       else:
           # 获取用户基本信息
           user_info = get_user_info(username)
           if not user_info:
               return 20
               
           # 获取用户的仓库列表
           repos = get_user_repos(username)
           
           # 1. 计算社交影响力指数 (0-1)
           followers = user_info.get('followers', 0)
           social_impact = min(1.0, math.log(followers + 1) / math.log(10000))
           
           # 2. 计算仓库质量指数 (0-1)
           if repos:
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
           final_score = (social_impact * 0.4 +
                         repo_quality * 0.4 +
                         activity_score * 0.2)
           
           # 5. 映射到20-40范围
           normalized_scale = 20 + final_score * 20
           
           return normalized_scale
           
   except Exception as e:
       logger.error(f"Error calculating user scale for {username}: {str(e)}")
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

def determine_node_type(target_scale: float, candidate_scale: float, similarity: float, is_repo: bool = False) -> str:
    """
    确定节点类型
    :param target_scale: 目标用户/仓库的规模分数 (20-40)
    :param candidate_scale: 候选用户/仓库的规模分数 (20-40)
    :param similarity: 相似度分数 (0-1)
    :param is_repo: 是否是仓库节点
    :return: 节点类型
    """
    scale_diff = candidate_scale - target_scale
    
    if is_repo:
        # 仓库节点的判定逻辑
        if similarity >= 0.6:  # 高相似度
            if scale_diff > 5:
                return 'mentor'  # 规模更大的相似仓库
            elif abs(scale_diff) <= 5:
                return 'peer'    # 规模相近的相似仓库
            else:
                return 'floating'  # 规模较小的相似仓库
        else:  # 低相似度
            if abs(scale_diff) <= 3:
                return 'peer'    # 规模相近但相似度低的仓库
            else:
                return 'floating'  # 其他仓库
    else:
        # 用户节点的判定逻辑保持不变
        if target_scale < 25:  # 新手用户
            if abs(scale_diff) <= 3 and similarity >= 0.3:
                return 'peer'
            elif 3 < scale_diff <= 7 and similarity >= 0.4:
                return 'mentor'
            else:
                return 'floating'
        else:  # 普通用户
            if abs(scale_diff) <= 3 and similarity >= 0.4:
                return 'peer'
            elif 3 < scale_diff <= 8 and similarity >= 0.5:
                return 'mentor'
            else:
                return 'floating'

def get_user_main_language(username: str) -> str:
    """获取用户的主要编程语言"""
    try:
        repos = get_user_repos(username)
        if not repos:
            return "unknown"
        
        language_count = defaultdict(int)
        for repo in repos:
            lang = repo.get('language')
            if lang:
                language_count[lang] += 1
        
        if not language_count:
            return "unknown"
            
        return max(language_count.items(), key=lambda x: x[1])[0]
    except Exception as e:
        logger.error(f"Error getting main language for {username}: {str(e)}")
        return "unknown"

def diversified_recommendations(candidates: List[Dict], count: int) -> List[Dict]:
    """
    使用分层随机采样的方式选择推荐结果
    """
    # 按规模分成三层
    top_tier = []    # 高规模用户 (35-40)
    mid_tier = []    # 中等规模用户 (27-35)
    low_tier = []    # 较低规模用户 (20-27)
    
    for candidate in candidates:
        scale = candidate['metrics']['size']
        if scale >= 35:
            top_tier.append(candidate)
        elif scale >= 27:
            mid_tier.append(candidate)
        else:
            low_tier.append(candidate)
    
    # 按比例选择
    result = []
    if count <= 10:
        # 小规模推荐时的比例: 20% 顶层, 50% 中层, 30% 底层
        top_count = max(1, int(count * 0.2))
        mid_count = max(1, int(count * 0.5))
        low_count = count - top_count - mid_count
        
        result.extend(random.sample(top_tier, min(top_count, len(top_tier))))
        result.extend(random.sample(mid_tier, min(mid_count, len(mid_tier))))
        result.extend(random.sample(low_tier, min(low_count, len(low_tier))))
    
    return result

def balanced_recommendations(candidates: List[Dict], target_scale: float) -> List[Dict]:
    """
    平衡相似度和规模差异的推荐
    """
    for candidate in candidates:
        scale = candidate['metrics']['size']
        similarity = candidate['similarity']
        
        # 计算综合得分
        scale_diff = abs(scale - target_scale)
        if scale_diff > 10:  # 规模差距过大严重惩罚
            scale_penalty = 0.5
        else:
            scale_penalty = 1 - (scale_diff / 20)  # 规模差距越大，惩罚越大
            
        candidate['final_score'] = similarity * 0.7 + scale_penalty * 0.3
    
    # 按综合得分排序
    candidates.sort(key=lambda x: x['final_score'], reverse=True)
    return candidates

def interest_diversified_recommendations(candidates: List[Dict], count: int) -> List[Dict]:
    """
    确保推荐结果在技术领域上的多样性
    """
    # 按主要编程语言分组
    language_groups = defaultdict(list)
    for candidate in candidates:
        main_language = get_user_main_language(candidate['name'])
        language_groups[main_language].append(candidate)
    
    # 从每个语言组中选择top用户
    result = []
    languages = list(language_groups.keys())
    while len(result) < count and languages:
        for lang in languages[:]:
            if language_groups[lang]:
                # 选择组最佳候选人
                best_candidate = max(
                    language_groups[lang], 
                    key=lambda x: x['similarity']
                )
                result.append(best_candidate)
                language_groups[lang].remove(best_candidate)
            else:
                languages.remove(lang)
            
            if len(result) >= count:
                break
    
    return result

def optimize_recommendations(candidates: List[Dict], target_scale: float, count: int, is_repo: bool = False) -> List[Dict]:
    """
    综合三种推荐策略的优化推荐函数
    """
    # 1. 首先使用balanced_recommendations计算综合得分
    balanced_candidates = balanced_recommendations(candidates, target_scale)
    
    # 2. 使用分层采样选择候选人
    sampled_candidates = diversified_recommendations(balanced_candidates, count * 2)  # 选择2倍数量以供后续筛选
    
    # 3. 最后使用兴趣领域多样化进行最终筛选
    final_candidates = interest_diversified_recommendations(sampled_candidates, count)
    
    # 4. 为每个推荐结果添加多样性标记
    for candidate in final_candidates:
        candidate['diversity_factor'] = {
            'language_diversity': get_user_main_language(candidate['name']) != "unknown",
            'scale_balance': abs(candidate['metrics']['size'] - target_scale) <= 5,
            'interest_match': candidate['similarity'] >= 0.4
        }
        # 更新节点类型，传入是否为仓库的标志
        candidate['nodeType'] = determine_node_type(
            target_scale,
            candidate['metrics']['size'],
            candidate['similarity'],
            is_repo
        )
    
    return final_candidates

def check_rate_limit():
    """检查 GitHub API 速率限制状态"""
    session = get_session()
    try:
        response = session.get(f"{GITHUB_API}/rate_limit")
        if response.status_code == 200:
            limits = response.json()
            rate = limits.get('rate', {})
            remaining = rate.get('remaining', 0)
            reset_time = datetime.fromtimestamp(rate.get('reset', 0))
            logger.info(f"API Rate Limits - Remaining: {remaining}, Reset at: {reset_time}")
            return limits
        logger.error(f"Failed to get rate limits. Status: {response.status_code}")
        return None
    except Exception as e:
        logger.error(f"Error checking rate limits: {str(e)}")
        return None

def get_backup_recommendations(find: str, count: int) -> List[Dict]:
    """获���备选推荐结果"""
    logger.info(f"Getting backup recommendations for type: {find}")
    try:
        if find == 'user':
            active_users = get_active_users()
            logger.info(f"Found {len(active_users)} active users as backup")
            return [{
                'name': user['login'],
                'metrics': {
                    'followers': user.get('followers', 0),
                    'following': user.get('following', 0),
                    'public_repos': user.get('public_repos', 0),
                    'size': get_user_scale(user['login'])  # 动态计算用户规模
                },
                'similarity': 0.3 + random.random() * 0.3,  # 添加随机性，范围0.3-0.6
                'nodeType': 'peer'
            } for user in active_users[:count]]
        else:
            trending_repos = get_trending_repos()
            logger.info(f"Found {len(trending_repos)} trending repos as backup")
            result = []
            for repo in trending_repos[:count]:
                repo_info = get_repo_info(repo['full_name'])
                if repo_info:
                    # 使用实际的仓库规模
                    size = repo_info.get('size', 25)
                    # 基于star数量计算基础相似度
                    base_similarity = min(0.6, math.log(repo.get('stargazers_count', 0) + 1) / math.log(10000))
                    result.append({
                        'name': repo['full_name'],
                        'metrics': {
                            'stars': repo.get('stargazers_count', 0),
                            'forks': repo.get('forks_count', 0),
                            'watchers': repo.get('watchers_count', 0),
                            'size': size
                        },
                        'similarity': max(0.3, base_similarity),  # 确保最小相似度为0.3
                        'nodeType': 'peer'
                    })
            return result
    except Exception as e:
        logger.error(f"Error getting backup recommendations: {str(e)}")
        return []

def recommend(type_str: str, name: str, find: str, count: int = N) -> Dict[str, Any]:
    """推荐函数"""
    try:
        # 检查API限制
        rate_limits = check_rate_limit()
        if rate_limits:
            remaining = rate_limits.get('rate', {}).get('remaining', 0)
            reset_time = datetime.fromtimestamp(rate_limits.get('rate', {}).get('reset', 0))
            if remaining < 50:
                return {
                    'success': False,
                    'error_type': 'RATE_LIMIT_ERROR',
                    'message': f'GitHub API 速率限制即将达到上限，剩余：{remaining}，重置时间：{reset_time}'
                }

        session = get_session()
        count = N if count is None else min(count, N)
        
        # 获取中心节点信息
        center_metrics = {}
        if type_str == 'user':
            center_info = get_user_info(name)
            if not center_info:
                return {
                    'success': False,
                    'error_type': 'USER_NOT_FOUND',
                    'message': f'用户 {name} 不存在或无法访问'
                }
            user_scale = get_user_scale(name)
            center_metrics = {
                'followers': center_info.get('followers', 0),
                'following': center_info.get('following', 0),
                'public_repos': center_info.get('public_repos', 0),
                'size': user_scale
            }
        else:  # type_str == 'repo'
            center_info = get_repo_info(name)
            if not center_info:
                return {
                    'success': False,
                    'error_type': 'REPO_NOT_FOUND',
                    'message': f'仓库 {name} 不存在或无法访问'
                }
            center_metrics = {
                'stars': center_info.get('stargazers_count', 0),
                'forks': center_info.get('forks_count', 0),
                'watchers': center_info.get('watchers_count', 0),
                'size': get_repo_scale(name)
            }

        # 基础响应结构
        base_response = {
            'success': True,
            'data': {
                'nodes': [{
                    'id': name,
                    'type': type_str,
                    'nodeType': 'center',
                    'metrics': center_metrics,
                    'similarity': 1.0
                }],
                'links': [],
                'center': {
                    'id': name,
                    'type': type_str
                }
            }
        }

        if type_str == 'user' and find == 'user':
            # 获取用户的仓库列表
            user_repos = get_user_repos(name)
            if not user_repos:
                return {
                    'success': False,
                    'error_type': 'NO_USER_REPOS',
                    'message': f'用户 {name} 没有公开仓库或无法获取仓库列表'
                }

            # 获取相似用户
            similar_users = []
            try:
                # ... 现有的用户推荐逻辑 ...
                pass
            except Exception as e:
                return {
                    'success': False,
                    'error_type': 'USER_RECOMMENDATION_ERROR',
                    'message': f'获取用户推荐时发生错误: {str(e)}'
                }

        elif type_str == 'user' and find == 'repo':
            # 获取用户的仓库列表
            user_repos = get_user_repos(name)
            if not user_repos:
                return {
                    'success': False,
                    'error_type': 'NO_USER_REPOS',
                    'message': f'用户 {name} 没有公开仓库或无法获取仓库列表'
                }

            # 获取语言偏好
            languages = _get_language_preferences(user_repos)
            if not languages:
                return {
                    'success': False,
                    'error_type': 'NO_LANGUAGE_PREFERENCE',
                    'message': f'无法确定用户 {name} 的编程语言偏好'
                }

            # 获取推荐仓库
            try:
                # ... 现有的仓库推荐逻辑 ...
                pass
            except Exception as e:
                return {
                    'success': False,
                    'error_type': 'REPO_RECOMMENDATION_ERROR',
                    'message': f'获取仓库推荐时发生错误: {str(e)}'
                }

        elif type_str == 'repo':
            # 获取仓库信息
            repo_info = get_repo_info(name)
            if not repo_info:
                return {
                    'success': False,
                    'error_type': 'REPO_NOT_FOUND',
                    'message': f'仓库 {name} 不存在或无法访问'
                }

            if find == 'user':
                # 获取仓库贡献者
                contributors = get_repo_contributors(name)
                if not contributors:
                    return {
                        'success': False,
                        'error_type': 'NO_CONTRIBUTORS',
                        'message': f'仓库 {name} 没有贡献者或无法获取贡献者列表'
                    }

                try:
                    # ... 现有的用户推荐逻辑 ...
                    pass
                except Exception as e:
                    return {
                        'success': False,
                        'error_type': 'USER_RECOMMENDATION_ERROR',
                        'message': f'获取用户推荐时发生错误: {str(e)}'
                    }

            elif find == 'repo':
                # 获取相似仓库
                try:
                    # ... 现有的仓库推荐逻辑 ...
                    pass
                except Exception as e:
                    return {
                        'success': False,
                        'error_type': 'REPO_RECOMMENDATION_ERROR',
                        'message': f'获取仓库推荐时发生错误: {str(e)}'
                    }

        # 如果没有推荐结果
        if len(base_response['data']['nodes']) <= 1:
            return {
                'success': False,
                'error_type': 'NO_RECOMMENDATIONS',
                'message': '未找到任何推荐结果'
            }

        return base_response

    except Exception as e:
        logger.error(f"Error in recommend function: {str(e)}")
        return {
            'success': False,
            'error_type': 'INTERNAL_ERROR',
            'message': f'内部错误: {str(e)}'
        }

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
                "content": "你是一个致力于维护github开源社区的工作员，你的职责是分析用户和项目之间的相似点，目标是促进协作和技术交流。对于两个github仓库：分析它们的相似之处，目的是找到能够吸引一个仓库的贡献者愿意维护另一个仓库的理由对于两个用户：分析他们的偏好和术栈相似点，目的是促成他们成为好友并深入交流技术。对于一个用户和一个仓库：分析用户的偏好或技术栈与仓库特征的相似点，目的是说服用户参与该仓库的献。输出要求：不要用markdown的语法，你的回答必须是有序列表格式，每个列表项应包含清晰且详细的理由，在每个理由前标上序号。不需要任何叙性语句或解释，只需列出分析结果。语气务必坚定，确保每个理由都显得可信且具有说服力。请判断清楚2个主体分别是用户还是仓库。不要用markdown语法，请用没有格式的纯文本。"
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
                        if 'login' in result[0]:  # 户列表
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