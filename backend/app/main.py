from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import logging
from recommend import recommend

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title="OpenChain API",
    description="OpenChain 开源社区关系分析API",
    version="1.0.0"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 请求模型
class GraphRequest(BaseModel):
    platform: str = Field(..., description="平台名称，目前只支持github")
    type: str = Field(..., description="查询类型：user或repo")
    name: str = Field(..., description="查询名称")
    find: str = Field(..., description="查找类型：user或repo")
    find_count: int = Field(default=10, ge=1, le=100, description="返回结果数量")

    class Config:
        schema_extra = {
            "example": {
                "platform": "github",
                "type": "user",
                "name": "frank-whw",
                "find": "repo",
                "find_count": 10
            }
        }

# 响应模型
class GraphNode(BaseModel):
    name: str
    similarity: float = Field(ge=0, le=1)
    scale: float = Field(ge=0, le=1)
    extra_info: Optional[Dict[str, Any]] = Field(default_factory=dict)

class GraphResponse(BaseModel):
    success: bool
    data: Optional[List[GraphNode]] = None
    error: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None

    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "data": [{
                    "name": "example/repo",
                    "similarity": 0.8,
                    "scale": 0.6,
                    "extra_info": {
                        "language": "Python",
                        "stars": 100,
                        "description": "Example repository"
                    }
                }],
                "meta": {"version": "1.0.0"}
            }
        }

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

@app.post("/api/graph")
async def get_graph_data(request: GraphRequest):
    """获取图数据"""
    try:
        logger.info(f"Processing graph request: {request.dict()}")
        logger.info("Calling recommend function...")
        
        # 调用推荐函数
        results = recommend(
            type_str=request.type,
            name=request.name,
            find=request.find
        )
        
        # 处理结果
        nodes = []
        for item, similarity in results:
            if request.find == "user":
                scale = get_user_scale(item)
            else:
                scale = get_repo_scale(item)
                
            nodes.append({
                "name": item,
                "similarity": similarity,
                "scale": scale,
                "extra_info": {}  # 可以在这里添加额外信息
            })
            
        return {"success": True, "data": nodes}
        
    except Exception as e:
        error_msg = f"Recommendation error: {str(e)}"
        logger.error(f"HTTP error: {error_msg}")
        return {"success": False, "error": error_msg} 