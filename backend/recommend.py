import requests
import json
from typing import List, Dict, Tuple
import time
from collections import defaultdict
import concurrent.futures
from functools import lru_cache
import threading
import math

# 全局配置
N = 10  # 推荐结果数量
GITHUB_TOKEN = ""  # GitHub API token
GITHUB_API = "https://api.github.com"
OPENDIGGER_API = "https://oss.open-digger.cn"
MAX_WORKERS = 10  # 最大并行线程数
CACHE_SIZE = 128  # 缓存大小

# API请求头
headers = {
    "Authorization": f"token {GITHUB_TOKEN}",
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
def get_user_info(username: str) -> Dict:
    """获取用户信息（带缓存）"""
    session = get_session()
    response = session.get(f"{GITHUB_API}/users/{username}", headers=headers)
    return response.json() if response.status_code == 200 else {}

@lru_cache(maxsize=CACHE_SIZE)
def get_repo_info(repo_full_name: str) -> Dict:
    """获取仓库信息（带缓存）"""
    session = get_session()
    response = session.get(f"{GITHUB_API}/repos/{repo_full_name}", headers=headers)
    return response.json() if response.status_code == 200 else {}

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
                "per_page": 100
            }
        )
        return response.json().get('items', []) if response.status_code == 200 else []
    except:
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
    """计算用户规模指标（综合多个维度）"""
    session = get_session()
    try:
        # 获取用户基本信息
        user_info = get_user_info(username)
        followers = user_info.get('followers', 0)
        public_repos = user_info.get('public_repos', 0)
        
        # 获取用户活跃度
        response = session.get(f"{OPENDIGGER_API}/github/{username}/activity.json")
        activity = 0
        if response.status_code == 200:
            activity_data = response.json()
            # 计算最近一年的平均活跃度
            recent_activity = list(activity_data.values())[-12:]
            activity = sum(recent_activity) / len(recent_activity) if recent_activity else 0
        
        # 获取用户的代码贡献量
        repos = get_user_repos(username)
        total_commits = sum(repo.get('size', 0) for repo in repos) / 1000  # 转换为KB
        
        # 综合计算规模
        scale = (
            0.3 * math.log(followers + 1) +  # 关注者数量
            0.2 * math.log(public_repos + 1) +  # 公开仓库数量
            0.3 * activity +  # 活跃度
            0.2 * math.log(total_commits + 1)  # 代码贡献量
        )
        
        return max(1, scale)
    except:
        return 1

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
        
        return max(1, scale)
    except:
        return 1

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
    return 0.3 * language_similarity + 0.3 * topic_similarity + 0.2 * size_similarity + 0.2 * desc_similarity

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

def recommend(type_str: str, name: str, find: str) -> List[Tuple[str, float]]:
    """主推荐函数（使用并行处理，确保返回非空结果）"""
    candidates = set()
    session = get_session()
    
    if type_str == "user" and find == "user":
        # 获取用户的关注者和被关注者
        followers_response = session.get(f"{GITHUB_API}/users/{name}/followers", headers=headers)
        following_response = session.get(f"{GITHUB_API}/users/{name}/following", headers=headers)
        
        if followers_response.status_code == 200:
            candidates.update(user['login'] for user in followers_response.json())
        if following_response.status_code == 200:
            candidates.update(user['login'] for user in following_response.json())
        
        # 如果候选集不够，添加活跃用户
        if len(candidates) < N:
            active_users = get_active_users()
            candidates.update(user['login'] for user in active_users)
        
        # 如果还是没有候选集，添加随机用户
        if not candidates:
            random_users_response = session.get(
                f"{GITHUB_API}/search/users",
                headers=headers,
                params={"q": "followers:>100", "sort": "followers", "order": "desc", "per_page": 100}
            )
            if random_users_response.status_code == 200:
                candidates.update(user['login'] for user in random_users_response.json().get('items', []))
        
        candidates.discard(name)
    
    elif type_str == "repo" and find == "repo":
        org, repo = name.split('/')
        org_repos_response = session.get(f"{GITHUB_API}/orgs/{org}/repos", headers=headers)
        
        if org_repos_response.status_code == 200:
            repo_info = get_repo_info(name)
            owner = repo_info.get('owner', {}).get('login', '')
            candidates.update(r['full_name'] for r in org_repos_response.json() 
                            if r['full_name'] != name and r.get('owner', {}).get('login', '') != owner)
        
        # 如果候选集不够，添加相似主题的仓库
        if len(candidates) < N:
            repo_info = get_repo_info(name)
            topics = repo_info.get('topics', [])
            if topics:
                topic_query = ' '.join(topics[:3])  # 使用前3个主题
                similar_repos_response = session.get(
                    f"{GITHUB_API}/search/repositories",
                    headers=headers,
                    params={"q": f"topic:{topic_query}", "sort": "stars", "order": "desc", "per_page": 100}
                )
                if similar_repos_response.status_code == 200:
                    candidates.update(repo['full_name'] for repo in similar_repos_response.json().get('items', [])
                                   if repo['full_name'] != name)
        
        # 如果还是没有候选集，添加热门仓库
        if not candidates:
            trending_repos = get_trending_repos()
            candidates.update(repo['full_name'] for repo in trending_repos if repo['full_name'] != name)
    
    elif type_str == "user" and find == "repo":
        # 获取用户star的仓库
        starred_response = session.get(f"{GITHUB_API}/users/{name}/starred", headers=headers)
        
        if starred_response.status_code == 200:
            user_repos = set(repo['full_name'] for repo in get_user_repos(name))
            candidates.update(repo['full_name'] for repo in starred_response.json() 
                            if repo['full_name'] not in user_repos)
        
        # 如果候选集不够，添加用户主要语言的热门仓库
        if len(candidates) < N:
            user_repos = get_user_repos(name)
            main_language = max(
                (repo['language'] for repo in user_repos if repo['language']),
                key=lambda x: sum(1 for r in user_repos if r.get('language') == x),
                default=None
            )
            if main_language:
                lang_repos_response = session.get(
                    f"{GITHUB_API}/search/repositories",
                    headers=headers,
                    params={"q": f"language:{main_language}", "sort": "stars", "order": "desc", "per_page": 100}
                )
                if lang_repos_response.status_code == 200:
                    candidates.update(repo['full_name'] for repo in lang_repos_response.json().get('items', [])
                                   if repo['full_name'] not in user_repos)
        
        # 如果还是没有候选集，添加热门仓库
        if not candidates:
            trending_repos = get_trending_repos()
            candidates.update(repo['full_name'] for repo in trending_repos)
    
    else:  # type == "repo" and find == "user"
        # 获取仓库的贡献者
        contributors = get_repo_contributors(name)
        candidates = set(c['login'] for c in contributors)
        
        # 如果候选集不够，添加相似仓库的贡献者
        if len(candidates) < N:
            repo_info = get_repo_info(name)
            language = repo_info.get('language', '')
            if language:
                similar_repos_response = session.get(
                    f"{GITHUB_API}/search/repositories",
                    headers=headers,
                    params={"q": f"language:{language}", "sort": "stars", "order": "desc", "per_page": 10}
                )
                if similar_repos_response.status_code == 200:
                    for repo in similar_repos_response.json().get('items', []):
                        repo_contributors = get_repo_contributors(repo['full_name'])
                        candidates.update(c['login'] for c in repo_contributors)
        
        # 如果还是没有候选集，添加活跃用户
        if not candidates:
            active_users = get_active_users()
            candidates.update(user['login'] for user in active_users)
    
    # 确保candidates非空
    if not candidates and find == "user":
        active_users = get_active_users()
        candidates.update(user['login'] for user in active_users)
    elif not candidates and find == "repo":
        trending_repos = get_trending_repos()
        candidates.update(repo['full_name'] for repo in trending_repos)
    
    # 并行处理候选对象
    args_list = [(candidate, name, type_str, find) for candidate in candidates]
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        results = list(executor.map(process_candidate, args_list))
    
    # 排序并返回前N个结果
    results.sort(key=lambda x: x[1], reverse=True)
    return results[:N]

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

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 4:
        print("Usage: python recommender.py <type> <name> <find>")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2], sys.argv[3])