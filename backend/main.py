from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from pydantic import BaseModel
from analyzer import OpenChainAnalyzer

# 创建分析器实例
analyzer = OpenChainAnalyzer()

app = FastAPI(
    title="OpenChain API",
    description="OpenChain 开源社区关系分析API",
    version="1.0.0"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应该设置具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 请求模型
class AnalysisRequest(BaseModel):
    platform: str
    type: str  # 'repo' 或 'user'
    name: str
    find_count: Optional[int] = 5

# 路由定义
@app.get("/")
async def root():
    """API 根路径，返回基本信息"""
    return {
        "message": "Welcome to OpenChain API",
        "version": "1.0.0"
    }

@app.post("/api/analyze")
async def analyze(request: AnalysisRequest):
    """
    分析仓库或用户的关系网络
    
    - **platform**: 平台名称 (github/gitee)
    - **type**: 分析类型 (repo/user)
    - **name**: 仓库名称或用户名
    - **find_count**: 要查找的相关节点数量
    """
    try:
        if request.platform.lower() not in ['github', 'gitee']:
            raise HTTPException(status_code=400, detail="不支持的平台")

        if request.type.lower() not in ['repo', 'user']:
            raise HTTPException(status_code=400, detail="不支持的分析类型")

        if request.type.lower() == 'repo':
            # 处理仓库分析
            owner, repo = request.name.split('/')
            result = await analyzer.analyze_repository(
                owner=owner,
                repo=repo,
                find_count=request.find_count
            )
        else:
            # 处理用户分析
            result = await analyzer.analyze_user(
                username=request.name,
                find_count=request.find_count
            )

        if not result['success']:
            raise HTTPException(status_code=500, detail=result['error'])

        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
async def health_check():
    """健康检查接口"""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 