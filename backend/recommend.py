import requests
import json
from typing import List, Dict, Tuple, Any
import time
from collections import defaultdict
import concurrent.futures
from functools import lru_cache
import threading
import math
import os
import logging
from fastapi import FastAPI

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 创建 FastAPI 应用实例
app = FastAPI()

# 全局配置
N = 5  # 推荐结果数量
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN', '')  # 从环境变量获取 GitHub Token
GITHUB_API = "https://api.github.com"
OPENDIGGER_API = "https://oss.x-lab.info/open_digger/github"
MAX_WORKERS = 10  # 最大并行线程数
CACHE_SIZE = 128  # 缓存大小

# API请求头
headers = {
    "Authorization": f"token {GITHUB_TOKEN}" if GITHUB_TOKEN else "",
    "Accept": "application/vnd.github.v3+json"
}

# 线程本地存储
thread_local = threading.local()

def get_session():
    """获取线程本地的session对象"""
    if not hasattr(thread_local, "session"):
        thread_local.session = requests.Session()
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
        # 构建查询条件
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
                # 验证返回的数据包含必要的字段
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
    """计算用户规模指标（综合多个维度）"""
    session = get_session()
    try:
        # 获取用户基本信息
        user_info = get_user_info(username)
        if not user_info:
            return 20  # 最小规模为 20
            
        followers = user_info.get('followers', 0)
        following = user_info.get('following', 0)
        public_repos = user_info.get('public_repos', 0)
        
        # 计算基础规模（确保至少为1）
        base_scale = max(1, followers + following + public_repos)
        
        # 获取用户的仓库列表
        repos = get_user_repos(username)
        total_size = sum(repo.get('size', 0) for repo in repos)
        
        # 综合计算最终规模
        final_scale = math.sqrt(base_scale * (total_size + 1))
        
        # 归一化到 20-40 范围
        normalized_scale = 20 + (min(final_scale, 10000) / 10000) * 20
        
        return normalized_scale
    except Exception as e:
        logger.error(f"Error calculating user scale for {username}: {str(e)}")
        return 20  # 错误时返回最小规模

def get_repo_scale(repo_full_name: str) -> float:
    """计算仓库规模指标（综合多个维度）"""
    session = get_session()
    try:
        # 获取仓库基本信息
        repo_info = get_repo_info(repo_full_name)
        stars = repo_info.get('stargazers_count', 0)
        forks = repo_info.get('forks_count', 0)
        watchers = repo_info.get('watchers_count', 0)
        size = repo_info.get('size', 0) / 1000  # 转换为KB
        
        # 获取OpenRank值
        response_openrank = session.get(f"{OPENDIGGER_API}/github/{repo_full_name}/openrank.json")
        openrank = list(response_openrank.json().values())[-1] if response_openrank.status_code == 200 else 0
        
        # 获取活跃度
        response_activity = session.get(f"{OPENDIGGER_API}/github/{repo_full_name}/activity.json")
        activity = list(response_activity.json().values())[-1] if response_activity.status_code == 200 else 0
        
        # 综合计算规模
        scale = (
            0.3 * math.log(stars + 1) +  # star数量
            0.2 * math.log(forks + 1) +  # fork数量
            0.1 * math.log(watchers + 1) +  # 观察者数量
            0.2 * openrank +  # OpenRank值
            0.1 * activity +  # 活跃度
            0.1 * math.log(size + 1)  # 代码量
        )
        
        # 归一化到 20-40 范围
        normalized_scale = 20 + (min(scale, 10) / 10) * 20
        
        return normalized_scale
    except Exception as e:
        logger.error(f"Error calculating repo scale for {repo_full_name}: {str(e)}")
        return 20  # 错误时返回最小规模

def calculate_user_user_similarity(user1: str, user2: str) -> float:
    """计算用户-用户相似度（多维度）"""
    # 获取用户信息和仓库
    repos1 = get_user_repos(user1)
    repos2 = get_user_repos(user2)
    
    # 1. 语言相似度
    langs1 = set(repo['language'] for repo in repos1 if repo['language'])
    langs2 = set(repo['language'] for repo in repos2 if repo['language'])
    lang_similarity = len(langs1.intersection(langs2)) / len(langs1.union(langs2)) if langs1 and langs2 else 0
    
    # 2. 主题相似度
    topics1 = set()
    topics2 = set()
    for repo in repos1:
        topics1.update(repo.get('topics', []))
    for repo in repos2:
        topics2.update(repo.get('topics', []))
    topic_similarity = len(topics1.intersection(topics2)) / len(topics1.union(topics2)) if topics1 and topics2 else 0
    
    # 3. 规模相似度
    size1 = sum(repo.get('size', 0) for repo in repos1)
    size2 = sum(repo.get('size', 0) for repo in repos2)
    size_similarity = 1 - abs(size1 - size2) / max(size1 + size2, 1)
    
    # 综合计算
    return 0.4 * lang_similarity + 0.4 * topic_similarity + 0.2 * size_similarity

def calculate_repo_repo_similarity(repo1: str, repo2: str) -> float:
    """计算仓库-仓库相似度（多维度）"""
    info1 = get_repo_info(repo1)
    info2 = get_repo_info(repo2)
    
    # 1. 语言相似度
    language_similarity = 1 if info1.get('language') == info2.get('language') else 0
    
    # 2. 主题相似度
    topics1 = set(info1.get('topics', []))
    topics2 = set(info2.get('topics', []))
    topic_similarity = len(topics1.intersection(topics2)) / len(topics1.union(topics2)) if topics1 or topics2 else 0
    
    # 3. 规模相似度
    size1 = info1.get('size', 0)
    size2 = info2.get('size', 0)
    size_similarity = 1 - abs(size1 - size2) / max(size1 + size2, 1)
    
    # 4. 功能相似度（基于描述）
    desc1 = info1.get('description', '').lower().split()
    desc2 = info2.get('description', '').lower().split()
    desc_words1 = set(desc1)
    desc_words2 = set(desc2)
    desc_similarity = len(desc_words1.intersection(desc_words2)) / len(desc_words1.union(desc_words2)) if desc_words1 and desc_words2 else 0
    
    # 综合计算
    return 0.3 * language_similarity + 0.4 * topic_similarity + 0.2 * size_similarity + 0.1 * desc_similarity

def calculate_user_repo_similarity(username: str, repo_name: str) -> float:
    """计算用户-仓库相似度（多维度）"""
    # 获取用户和仓库信息
    user_repos = get_user_repos(username)
    repo_info = get_repo_info(repo_name)
    
    # 1. 语言匹配度
    user_languages = defaultdict(int)
    for repo in user_repos:
        if repo['language']:
            user_languages[repo['language']] += 1
    total_repos = sum(user_languages.values())
    repo_language = repo_info.get('language', '')
    language_match = user_languages.get(repo_language, 0) / total_repos if total_repos > 0 else 0
    
    # 2. 主题匹配度
    user_topics = set()
    for repo in user_repos:
        user_topics.update(repo.get('topics', []))
    repo_topics = set(repo_info.get('topics', []))
    topic_match = len(repo_topics.intersection(user_topics)) / len(repo_topics.union(user_topics)) if repo_topics or user_topics else 0
    
    # 3. 规模匹配度
    user_avg_size = sum(repo.get('size', 0) for repo in user_repos) / len(user_repos) if user_repos else 0
    repo_size = repo_info.get('size', 0)
    size_match = 1 - abs(user_avg_size - repo_size) / max(user_avg_size + repo_size, 1)
    
    # 综合计算
    return 0.4 * language_match + 0.4 * topic_match + 0.2 * size_match

def process_candidate(args) -> Tuple[str, float]:
    """处理单个候选对象（用于并行处理）"""
    candidate, name, type_str, find = args
    if type_str == "user" and find == "user":
        similarity = calculate_user_user_similarity(name, candidate)
    elif type_str == "repo" and find == "repo":
        similarity = calculate_repo_repo_similarity(name, candidate)
    elif type_str == "user" and find == "repo":
        similarity = calculate_user_repo_similarity(name, candidate)
    else:  # type == "repo" and find == "user"
        similarity = calculate_user_repo_similarity(candidate, name)
    return candidate, similarity

def recommend(type_str: str, name: str, find: str, count: int = N) -> Dict[str, Any]:
    """
    推荐函数
    :param type_str: 'user' 或 'repo'
    :param name: 用户名或仓库全名
    :param find: 要查找的类型 'user' 或 'repo'
    :param count: 返回结果数量，如果为 None 则使用全局配置的 N
    :return: 推荐结果
    """
    # 使用全局配置的 N 值
    count = N if count is None else min(count, N)
    
    try:
        session = get_session()
        logger.info(f"Processing recommendation request: {type_str}/{name} -> {find}, count={count}")

        # 创建基本响应结构
        base_response = {
            'metrics': {
                'stars': 0,
                'forks': 0,
                'watchers': 0,
                'size': 0,
                'followers': 0,
                'following': 0,
                'public_repos': 0
            },
            'recommendations': [],
            'status': 'success',
            'message': ''
        }

        if type_str == 'user':
            # 获取用户信息
            user_info = get_user_info(name)
            if user_info is None:
                error_msg = f'用户 {name} 不存在或无法访问'
                logger.warning(error_msg)
                base_response.update({
                    'status': 'error',
                    'message': error_msg
                })
                return base_response

            # 计算用户规模
            user_scale = get_user_scale(name)

            # 更新用户指标
            base_response['metrics'].update({
                'followers': user_info.get('followers', 0),
                'following': user_info.get('following', 0),
                'public_repos': user_info.get('public_repos', 0),
                'size': user_scale  # 使用计算出的规模作为 size
            })

            if find == 'user':
                try:
                    # 获取用户的关注者
                    followers = _get_user_followers(name)
                    if not followers:
                        error_msg = f'无法获取用户 {name} 的关注者信息，可能是由于 API 限制或网络问题'
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
                    candidates = list(set([user['login'] for user in followers] + [user['login'] for user in active_users]))
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
                        if candidate != name:  # 排除自己
                            try:
                                similarity = calculate_user_user_similarity(name, candidate)
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
                                # 计算推荐用户的规模
                                recommended_user_scale = get_user_scale(user)
                                base_response['recommendations'].append({
                                    'name': user,
                                    'metrics': {
                                        'followers': user_info.get('followers', 0),
                                        'following': user_info.get('following', 0),
                                        'public_repos': user_info.get('public_repos', 0),
                                        'size': recommended_user_scale  # 添加规模指标
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

                except Exception as e:
                    error_msg = f'推荐仓库时发生错误: {str(e)}'
                    logger.error(error_msg)
                    base_response.update({
                        'status': 'error',
                        'message': error_msg
                    })
                    return base_response

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
        error_msg = str(e)
        logger.error(f"Error in recommend function: {error_msg}")
        return {
            'metrics': {
                'stars': 0,
                'forks': 0,
                'watchers': 0,
                'size': 0,
                'followers': 0,
                'following': 0,
                'public_repos': 0
            },
            'recommendations': [],
            'status': 'error',
            'message': f'系统错误: {error_msg}'
        }

def process_recommendation(item_similarity: Tuple[str, float], find: str) -> Dict:
    """处理单个推荐结果（用于并行处理）"""
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
    """主函数（使用并行处理）"""
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
    """使用大模型分析两个节点之间的关系"""
    url = "https://spark-api-open.xf-yun.com/v1/chat/completions"
    data = {
        "max_tokens": 4096,
        "top_k": 4,
        "temperature": 0.5,
        "messages": [
            {
                "role": "system",
                "content": "你是一个致力于维护github开源社区的工作人员，你的职责是分析用户和项目之间的相似点，目标是促进协作和技术交流。对于两个github仓库：分析它们的相似之处，目的是找到能够吸引一个仓库的贡献者愿意维护另一个仓库的理由。对于两个用户：分析他们的偏好和技术栈相似点，目的是促成他们成为好友并深入交流技术。对于一个用户和一个仓库：分析用户的偏好或技术栈与仓库特征的相似点，目的是说服用户参与该仓库的贡献。输出要求：不要用markdown的语法，你的回答必须是有序列表格式，每个列表项应包含清晰且详细的理由，在每个理由前标上序号。不需要任何叙述性语句或解释，只需列出分析结果。语气务必坚定，确保每个理由都显得可信且具有说服力。请判断清楚2个主体分别是用户还是仓库。不要用markdown语法，请用没有格式的纯文本。"
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

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 4:
        print("Usage: python recommender.py <type> <name> <find>")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2], sys.argv[3])