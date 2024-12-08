// API基础配置
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

interface AnalysisResponse {
  success: boolean;
  data?: {
    main_repository?: string;
    main_user?: string;
    nodes: Array<{
      id: string;
      type: string;
      size: number;
      distance: number;
      openrank?: number;
      stars?: number;
      description?: string;
      contributions?: number;
      avatar_url?: string;
    }>;
    links: Array<{
      source: string;
      target: string;
      type: string;
    }>;
    stats: {
      openrank?: number;
      stars?: number;
      forks?: number;
      watchers?: number;
      dependencies_count?: number;
      contributors_count?: number;
      public_repos?: number;
      followers?: number;
      following?: number;
      contributions?: number;
    };
  };
  error?: string;
}

export async function fetchGraphData(platform: string, what: string, name: string) {
  try {
    const response = await fetch(`${API_BASE_URL}/api/analyze`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        platform,
        type: what,
        name,
        find_count: 5
      }),
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || '请求失败');
    }

    const data: AnalysisResponse = await response.json();
    
    if (!data.success || !data.data) {
      throw new Error(data.error || '数据获取失败');
    }

    // 转换数据格式以适配前端Graph组件
    return {
      center: { 
        id: data.data.main_repository || data.data.main_user || name,
        openrank: data.data.stats.openrank || 100
      },
      nodes: data.data.nodes.map(node => ({
        id: node.id,
        openrank: node.type === 'repository' ? (node.openrank || 0.5) * 100 : node.size,
        group: node.type
      })),
      links: data.data.links.map(link => ({
        source: link.source,
        target: link.target,
        value: 1
      }))
    };
  } catch (error) {
    console.error('API请求错误:', error);
    throw error;
  }
}

export async function fetchRelationshipAnalysis(centerId: string, nodeId: string) {
  try {
    // TODO: 实现关系分析API
    // 目前返回模拟数据
    return `分析 ${centerId} 和 ${nodeId} 之间的关系...
    
    - 类型: ${nodeId.includes('/') ? '仓库关系' : '贡献者关系'}
    - 关系强度: 较强
    - 互动频率: 频繁
    `;
  } catch (error) {
    console.error('关系分析请求错误:', error);
    return '无法获取关系分析数据';
  }
}

