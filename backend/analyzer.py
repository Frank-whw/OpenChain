import os
import json
import requests
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta
import time
from collections import defaultdict
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class OpenChainAnalyzer:
    def __init__(self):
        self.github_token = os.getenv('GITHUB_TOKEN')
        if not self.github_token:
            raise ValueError("GitHub Token not found in environment variables")
            
        self.headers = {
            'Authorization': f'token {self.github_token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        self.base_url = 'https://api.github.com'
        self.opendigger_base_url = 'https://oss.x-lab.info/open_digger/github'
        self.cache = {}
        self.cache_timeout = 3600  # 缓存1小时

    def _get_cached_data(self, key: str) -> Optional[Dict]:
        """获取缓存数据"""
        if key in self.cache:
            data, timestamp = self.cache[key]
            if time.time() - timestamp < self.cache_timeout:
                return data
            del self.cache[key]
        return None

    def _set_cached_data(self, key: str, data: Dict):
        """设置缓存数据"""
        self.cache[key] = (data, time.time())

    async def get_repository_info(self, owner: str, repo: str) -> Dict:
        """获取仓库详细信息"""
        cache_key = f"repo_{owner}_{repo}"
        cached_data = self._get_cached_data(cache_key)
        if cached_data:
            return cached_data

        # 获取基本信息
        url = f'{self.base_url}/repos/{owner}/{repo}'
        response = requests.get(url, headers=self.headers)
        if response.status_code != 200:
            raise Exception(f"Failed to fetch repository info: {response.status_code}")
        
        repo_data = response.json()

        # 获取OpenDigger数据
        opendigger_url = f'{self.opendigger_base_url}/{owner}/{repo}/openrank.json'
        try:
            openrank_response = requests.get(opendigger_url)
            if openrank_response.status_code == 200:
                openrank_data = openrank_response.json()
                # 获取最新的OpenRank值
                latest_openrank = list(openrank_data.values())[-1] if openrank_data else None
                repo_data['openrank'] = latest_openrank
        except:
            repo_data['openrank'] = self._calculate_simple_openrank(repo_data)

        self._set_cached_data(cache_key, repo_data)
        return repo_data

    def _calculate_simple_openrank(self, repo_data: Dict) -> float:
        """计算简化版OpenRank值"""
        stars = repo_data.get('stargazers_count', 0)
        forks = repo_data.get('forks_count', 0)
        watchers = repo_data.get('subscribers_count', 0)
        
        openrank = (stars * 0.5 + forks * 0.3 + watchers * 0.2) / 100
        return min(1.0, openrank)

    async def get_repository_dependencies(self, owner: str, repo: str) -> List[Dict]:
        """获取仓库依赖关系"""
        cache_key = f"deps_{owner}_{repo}"
        cached_data = self._get_cached_data(cache_key)
        if cached_data:
            return cached_data

        # 获取依赖图
        url = f'{self.base_url}/repos/{owner}/{repo}/dependency-graph/dependencies'
        response = requests.get(url, headers=self.headers)
        
        dependencies = []
        if response.status_code == 200:
            data = response.json()
            for dep in data.get('dependencies', []):
                if dep.get('package', {}).get('ecosystem') == 'github':
                    dep_name = dep['package']['name']
                    try:
                        dep_owner, dep_repo = dep_name.split('/')
                        dep_info = await self.get_repository_info(dep_owner, dep_repo)
                        dependencies.append({
                            'name': dep_name,
                            'openrank': dep_info.get('openrank', 0),
                            'stars': dep_info.get('stargazers_count', 0),
                            'description': dep_info.get('description', '')
                        })
                    except:
                        continue

        self._set_cached_data(cache_key, dependencies)
        return dependencies

    async def get_repository_contributors(self, owner: str, repo: str, limit: int = 10) -> List[Dict]:
        """获取仓库贡献者信息"""
        cache_key = f"contributors_{owner}_{repo}"
        cached_data = self._get_cached_data(cache_key)
        if cached_data:
            return cached_data

        url = f'{self.base_url}/repos/{owner}/{repo}/contributors'
        response = requests.get(url, headers=self.headers)
        
        contributors = []
        if response.status_code == 200:
            data = response.json()
            for contributor in data[:limit]:
                contributors.append({
                    'login': contributor['login'],
                    'contributions': contributor['contributions'],
                    'avatar_url': contributor['avatar_url']
                })

        self._set_cached_data(cache_key, contributors)
        return contributors

    async def analyze_repository(self, owner: str, repo: str, find_count: int = 5) -> Dict[str, Any]:
        """主要分析函数"""
        try:
            # 获取主仓库信息
            main_repo = await self.get_repository_info(owner, repo)
            main_repo_full = f"{owner}/{repo}"

            # 获取依赖关系
            dependencies = await self.get_repository_dependencies(owner, repo)
            
            # 获取贡献者
            contributors = await self.get_repository_contributors(owner, repo)

            # 构建图数据
            nodes = [{
                'id': main_repo_full,
                'type': 'repository',
                'size': 100,
                'distance': 0,
                'openrank': main_repo.get('openrank', 0),
                'stars': main_repo.get('stargazers_count', 0),
                'description': main_repo.get('description', '')
            }]

            links = []

            # 添加依赖节点
            for dep in dependencies[:find_count]:
                nodes.append({
                    'id': dep['name'],
                    'type': 'repository',
                    'size': int(dep['openrank'] * 100) if dep.get('openrank') else 50,
                    'distance': 1,
                    'openrank': dep.get('openrank', 0),
                    'stars': dep.get('stars', 0),
                    'description': dep.get('description', '')
                })
                links.append({
                    'source': main_repo_full,
                    'target': dep['name'],
                    'type': 'depends_on'
                })

            # 添加贡献者节点
            for contributor in contributors[:find_count]:
                nodes.append({
                    'id': contributor['login'],
                    'type': 'user',
                    'size': min(80, contributor['contributions'] // 10 + 30),
                    'distance': 1,
                    'contributions': contributor['contributions'],
                    'avatar_url': contributor['avatar_url']
                })
                links.append({
                    'source': contributor['login'],
                    'target': main_repo_full,
                    'type': 'contributes_to'
                })

            return {
                'success': True,
                'data': {
                    'main_repository': main_repo_full,
                    'nodes': nodes,
                    'links': links,
                    'stats': {
                        'openrank': main_repo.get('openrank', 0),
                        'stars': main_repo.get('stargazers_count', 0),
                        'forks': main_repo.get('forks_count', 0),
                        'watchers': main_repo.get('subscribers_count', 0),
                        'dependencies_count': len(dependencies),
                        'contributors_count': len(contributors)
                    }
                }
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    async def analyze_user(self, username: str, find_count: int = 5) -> Dict[str, Any]:
        """分析用户的仓库和贡献"""
        try:
            # 获取用户信息
            url = f'{self.base_url}/users/{username}'
            response = requests.get(url, headers=self.headers)
            if response.status_code != 200:
                raise Exception(f"Failed to fetch user info: {response.status_code}")
            
            user_data = response.json()

            # 获取用户的仓库
            repos_url = f'{self.base_url}/users/{username}/repos?sort=stars&direction=desc'
            repos_response = requests.get(repos_url, headers=self.headers)
            if repos_response.status_code != 200:
                raise Exception(f"Failed to fetch user repos: {repos_response.status_code}")
            
            repos = repos_response.json()

            # 构建图数据
            nodes = [{
                'id': username,
                'type': 'user',
                'size': 100,
                'distance': 0,
                'followers': user_data.get('followers', 0),
                'avatar_url': user_data.get('avatar_url', '')
            }]

            links = []

            # 添加用户的热门仓库
            for repo in repos[:find_count]:
                repo_name = f"{repo['owner']['login']}/{repo['name']}"
                nodes.append({
                    'id': repo_name,
                    'type': 'repository',
                    'size': min(80, repo['stargazers_count'] // 100 + 30),
                    'distance': 1,
                    'stars': repo['stargazers_count'],
                    'description': repo.get('description', '')
                })
                links.append({
                    'source': username,
                    'target': repo_name,
                    'type': 'owns'
                })

            return {
                'success': True,
                'data': {
                    'main_user': username,
                    'nodes': nodes,
                    'links': links,
                    'stats': {
                        'public_repos': user_data.get('public_repos', 0),
                        'followers': user_data.get('followers', 0),
                        'following': user_data.get('following', 0),
                        'contributions': sum(repo['stargazers_count'] for repo in repos[:5])
                    }
                }
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            } 