from collections import defaultdict
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import logging
import requests
import os

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class GitHubUserRecommender:
    def __init__(self):
        self.users = {}
        self.features = {}
        self.user_actions_count = defaultdict(int)
        # 直接使用指定的 token
        self.github_token = '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'
        self.headers = {
            "Authorization": f"Bearer {self.github_token}",  # 使用 Bearer 认证
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "GitHub-Recommendation-System"  # 添加 User-Agent
        }
        self.api_base = "https://api.github.com"
            
    def _get_user_data(self, username: str) -> dict:
        """获取用户的 GitHub 数据"""
        try:
            response = requests.get(
                f"{self.api_base}/users/{username}",
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 403:
                logger.error("API 速率限制已达到")
                return None
            elif response.status_code == 404:
                logger.error(f"用户 {username} 不存在")
                return None
                
            logger.error(f"获取用户数据失败，状态码: {response.status_code}")
            return None
            
        except Exception as e:
            logger.error(f"获取用户数据时发生错误: {str(e)}")
            return None
            
    def _get_user_repos(self, username: str) -> list:
        """获取用户的仓库列表"""
        try:
            response = requests.get(
                f"{self.api_base}/users/{username}/repos",
                headers=self.headers,
                params={"per_page": 100},  # 获取最多100个仓库
                timeout=10
            )
            
            if response.status_code == 200:
                # 过滤掉 fork 的仓库
                repos = response.json()
                return [repo for repo in repos if not repo.get('fork', False)]
            elif response.status_code == 403:
                logger.error("API 速率限制已达到")
                return []
                
            logger.error(f"获取用户仓库失败，状态码: {response.status_code}")
            return []
            
        except Exception as e:
            logger.error(f"获取用户仓库时发生错误: {str(e)}")
            return []
            
    def recommend_users(self, username: str, top_n=5) -> dict:
        """为指定用户推荐相似用户"""
        try:
            # 获取用户数据
            user_data = self._get_user_data(username)
            if not user_data:
                return {
                    'status': 'error',
                    'message': f'无法获取用户 {username} 的数据',
                    'recommendations': []
                }
                
            # 获取用户的仓库
            user_repos = self._get_user_repos(username)
            
            # 获取用户的关注者
            followers_response = requests.get(
                f"{self.api_base}/users/{username}/followers",
                headers=self.headers,
                params={"per_page": 100},
                timeout=10
            )
            
            if followers_response.status_code != 200:
                return {
                    'status': 'error',
                    'message': '无法获取用户的关注者',
                    'recommendations': []
                }
                
            followers = followers_response.json()
            
            # 计算推荐
            recommendations = []
            for follower in followers:
                follower_username = follower['login']
                follower_data = self._get_user_data(follower_username)
                
                if follower_data:
                    follower_repos = self._get_user_repos(follower_username)
                    
                    # 计算相似度
                    similarity = self._calculate_similarity(user_repos, follower_repos)
                    
                    recommendations.append({
                        'username': follower_username,
                        'similarity': similarity,
                        'metrics': {
                            'followers': follower_data.get('followers', 0),
                            'following': follower_data.get('following', 0),
                            'public_repos': follower_data.get('public_repos', 0)
                        }
                    })
            
            # 排序并返回前 top_n 个推荐
            recommendations.sort(key=lambda x: x['similarity'], reverse=True)
            return {
                'status': 'success',
                'message': '推荐成功',
                'recommendations': recommendations[:top_n]
            }
            
        except Exception as e:
            logger.error(f"推荐用户时发生错误: {str(e)}")
            return {
                'status': 'error',
                'message': str(e),
                'recommendations': []
            }
            
    def _calculate_similarity(self, user_repos: list, other_repos: list) -> float:
        """计算两个用户的相似度"""
        try:
            # 获取语言统计
            user_langs = self._get_language_stats(user_repos)
            other_langs = self._get_language_stats(other_repos)
            
            # 计算语言相似度
            lang_similarity = self._calculate_language_similarity(user_langs, other_langs)
            
            # 计算仓库规模相似度
            size_similarity = self._calculate_size_similarity(user_repos, other_repos)
            
            # 综合计算相似度
            return 0.7 * lang_similarity + 0.3 * size_similarity
            
        except Exception as e:
            logger.error(f"计算相似度时发生错误: {str(e)}")
            return 0.0
            
    def _get_language_stats(self, repos: list) -> dict:
        """统计语言使用情况"""
        stats = defaultdict(int)
        for repo in repos:
            lang = repo.get('language')
            if lang:
                stats[lang] += 1
        return stats
        
    def _calculate_language_similarity(self, langs1: dict, langs2: dict) -> float:
        """计算语言相似度"""
        all_langs = set(langs1.keys()) | set(langs2.keys())
        if not all_langs:
            return 0.0
            
        vector1 = np.array([langs1.get(lang, 0) for lang in all_langs])
        vector2 = np.array([langs2.get(lang, 0) for lang in all_langs])
        
        # 归一化
        vector1 = vector1 / (np.sum(vector1) or 1)
        vector2 = vector2 / (np.sum(vector2) or 1)
        
        return float(np.dot(vector1, vector2))
        
    def _calculate_size_similarity(self, repos1: list, repos2: list) -> float:
        """计算仓库规模相似度"""
        if not repos1 or not repos2:
            return 0.0
            
        size1 = sum(repo.get('size', 0) for repo in repos1) / len(repos1)
        size2 = sum(repo.get('size', 0) for repo in repos2) / len(repos2)
        
        # 使用对数尺度计算相似度
        return 1 - min(abs(np.log(size1 + 1) - np.log(size2 + 1)) / 10, 1)

# 使用示例
def recommend_similar_users(username: str, top_n=5):
    """推荐接口函数"""
    recommender = GitHubUserRecommender()
    return recommender.recommend_users(username, top_n)

if __name__ == "__main__":
    # 测试代码
    result = recommend_similar_users('will-ww', 5)
    print(result)