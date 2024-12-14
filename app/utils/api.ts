export interface RecommendationResult {
  success: boolean;
  data?: {
    nodes: Array<{
      id: string;
      type: 'user' | 'repo';
      metrics: {
        size: number;
        stars?: number;
        followers?: number;
        [key: string]: any;
      };
      similarity: number;
    }>;
    links: Array<{
      source: string;
      target: string;
      value: number;
    }>;
    center: {
      id: string;
      type: 'user' | 'repo';
    };
  };
  error?: string;
}

export async function fetchRecommendations(
  type: 'user' | 'repo',
  name: string,
  find: 'user' | 'repo'
): Promise<RecommendationResult> {
  try {
    const url = `/api/recommend?type=${type}&name=${encodeURIComponent(name)}&find=${find}`
    
    console.log('Fetching recommendations:', url)
    
    const response = await fetch(url)
    const data = await response.json()
    
    if (!response.ok) {
      throw new Error(data.detail || data.message || '请求失败')
    }
    
    if (!data.success) {
      throw new Error(data.error || '获取数据失败')
    }
    
    return data
  } catch (error: any) {
    console.error('API Error:', error)
    throw new Error(error.message || '网络错误')
  }
}

export async function fetchMetrics(type: 'user' | 'repo', name: string) {
  try {
    const response = await fetch(
      `/api/metrics?type=${type}&name=${encodeURIComponent(name)}`
    )
    const data = await response.json()
    
    if (!response.ok) {
      throw new Error(data.detail || data.message || '获取指标失败')
    }
    
    return data
  } catch (error: any) {
    console.error('Metrics Error:', error)
    throw new Error(error.message || '网络错误')
  }
}

