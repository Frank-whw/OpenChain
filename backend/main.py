from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, Dict, Any, List, Union
from pydantic import BaseModel, Field
from recommend import recommend


app = FastAPI(
    title="OpenChain API",
    description="OpenChain 开源社区关系分析API",
    version="1.0.0"
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

# 路由定义
@app.get("/")
async def root():
    """API 根路径，返回基本信息"""
    return {
        "message": "Welcome to OpenChain API",
        "version": "1.0.0"
    }

@app.get("/api/health")
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
    }
)
async def get_recommendations(
    type: str = Query(..., description="推荐主体类型 (user/repo)"),
    name: str = Query(..., description="主体名称"),
    find: str = Query(..., description="要推荐的目标类型 (user/repo)"),
    count: int = Query(default=10, description="返回结果数量", ge=1, le=100)
):
    """获取推荐结果"""
    print(f"Received recommendation request: {type}/{name} -> {find}")
    
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
                    "msg": "仓库名称格式错误，应为: owner/repo",
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )