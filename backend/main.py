from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, Dict, Any, List, Union
from pydantic import BaseModel, Field
from recommend import recommend, N, analyze_with_llm, logger


app = FastAPI(
    title="OpenChain API",
    description="OpenChain 开源社区关系分析API",
    version="1.0.0",
    openapi_tags=[
        {
            "name": "general",
            "description": "基础接口"
        },
        {
            "name": "recommendation",
            "description": "推荐系统接口"
        },
        {
            "name": "analysis",
            "description": "关系分析接口"
        }
    ]
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 响应模型
class GraphNode(BaseModel):
    id: str = Field(..., description="节点标识")
    type: str = Field(..., description="节点类型 (user/repo)")
    metrics: Dict[str, Any] = Field(..., description="节点指标")
    similarity: float = Field(..., description="相似度")

class GraphLink(BaseModel):
    source: str = Field(..., description="源节点")
    target: str = Field(..., description="目标节点")
    value: float = Field(..., description="连接权重")

class GraphData(BaseModel):
    nodes: List[GraphNode] = Field(..., description="节点列表")
    links: List[GraphLink] = Field(..., description="连接列表")
    center: Dict[str, str] = Field(..., description="中心节点信息")

class RecommendResponse(BaseModel):
    success: bool = Field(..., description="是否成功")
    data: GraphData = Field(..., description="图数据")

class ValidationError(BaseModel):
    loc: List[Union[str, int]] = Field(..., description="错误位置")
    msg: str = Field(..., description="错误信息")
    type: str = Field(..., description="错误类型")

class HTTPValidationError(BaseModel):
    detail: List[ValidationError] = Field(..., description="错误详情")

class AnalysisResponse(BaseModel):
    status: str = Field(..., description="分析状态 (success/error)")
    analysis: str = Field(..., description="分析结果")
    message: Optional[str] = Field(None, description="错误信息")

# 路由定义
@app.get("/", tags=["general"])
async def root():
    """API 根路径，返回基本信息"""
    return {
        "message": "Welcome to OpenChain API",
        "version": "1.0.0"
    }

@app.get("/api/health", tags=["general"])
async def health_check():
    """健康检查接口"""
    return {"status": "healthy"}

@app.get(
    "/api/recommend",
    response_model=RecommendResponse,
    responses={
        200: {"description": "成功获取推荐结果"},
        400: {"description": "参数错误", "model": HTTPValidationError},
        404: {"description": "未找到推荐结果"},
        500: {"description": "服务器错误"}
    },
    tags=["recommendation"]
)
async def get_recommendations(
    type: str = Query(..., description="推荐类型：'user' 或 'repo'"),
    name: str = Query(..., description="用户名或仓库全名"),
    find: str = Query(..., description="要查找的类型：'user' 或 'repo'"),
    count: Optional[int] = Query(None, description=f"返回结果数量，默认为 {N}", ge=1, le=100)
):
    """推荐 API 端点"""
    try:
        # 参数验证
        if type not in ['user', 'repo']:
            raise HTTPException(
                status_code=400,
                detail=[{
                    "loc": ["query", "type"],
                    "msg": "type 参数必须是 user 或 repo",
                    "type": "value_error"
                }]
            )
        if find not in ['user', 'repo']:
            raise HTTPException(
                status_code=400,
                detail=[{
                    "loc": ["query", "find"],
                    "msg": "find 参数必须是 user 或 repo",
                    "type": "value_error"
                }]
            )
        if type == 'repo' and '/' not in name:
            raise HTTPException(
                status_code=400,
                detail=[{
                    "loc": ["query", "name"],
                    "msg": "仓库名称格式错误，应: owner/repo",
                    "type": "value_error"
                }]
            )

        # 获取推荐结果
        recommendations = recommend(type, name, find, count)
        
        if not recommendations:
            raise HTTPException(status_code=404, detail="未找到推荐结果")

        # 构造返回数据
        nodes = []
        links = []
        
        # 添加中心节点
        nodes.append({
            'id': name,
            'type': type,
            'metrics': recommendations.get('metrics', {'size': 1}),
            'similarity': 1.0
        })

        # 添加推荐节点和连接
        for item in recommendations.get('recommendations', []):
            nodes.append({
                'id': item['name'],
                'type': find,
                'metrics': item['metrics'],
                'similarity': item['similarity']
            })
            links.append({
                'source': name,
                'target': item['name'],
                'value': item['similarity']
            })

        return {
            'success': True,
            'data': {
                'nodes': nodes,
                'links': links,
                'center': {
                    'id': name,
                    'type': type
                }
            }
        }
    except HTTPException as e:
        print(f"Validation error: {str(e)}")
        raise e
    except Exception as e:
        print(f"Recommendation error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=[{
                "loc": ["server"],
                "msg": str(e),
                "type": "server_error"
            }]
        )

@app.get(
    "/api/analyze",
    response_model=AnalysisResponse,
    responses={
        200: {"description": "成功获取分析结果"},
        400: {"description": "参数错误", "model": HTTPValidationError},
        500: {"description": "服务器错误"}
    },
    tags=["analysis"],
    summary="分析节点关系",
    description="分析两个节点（用户或仓库）之间的关系，返回详细的分析结果"
)
async def analyze_nodes(
    node_a: str = Query(..., description="第一个节点的标识（用户名或仓库全名）", example="microsoft"),
    node_b: str = Query(..., description="第二个节点的标识（用户名或仓库全名）", example="google/tensorflow")
):
    """
    分析两个节点（用户或仓库）之间的关系
    
    - **node_a**: 第一个节点的标识（用户名或仓库全名，例如：'octocat' 或 'microsoft/vscode'）
    - **node_b**: 第二个节点的标识（用户名或仓库全名，例如：'torvalds' 或 'facebook/react'）
    
    返回：
    - 分析结果，包含两个节点之间的关系分析
    """
    try:
        logger.info(f"Analyzing relationship between {node_a} and {node_b}")
        analysis = analyze_with_llm(node_a, node_b)
        if not analysis:
            raise HTTPException(
                status_code=500,
                detail="分析结果为空"
            )
        return {
            "status": "success",
            "analysis": analysis,
            "message": None
        }
    except Exception as e:
        logger.error(f"Analysis failed: {str(e)}")
        return {
            "status": "error",
            "analysis": "",
            "message": str(e)
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )