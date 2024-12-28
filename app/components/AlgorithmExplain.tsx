import React, { useState } from 'react';
import { Button } from './ui/button';

interface AlgorithmExplainProps {
  type: string;
}

const AlgorithmExplain: React.FC<AlgorithmExplainProps> = ({ type }) => {
  const [selectedType, setSelectedType] = useState<string>('');
  const [explanation, setExplanation] = useState<string>('');
  const [loading, setLoading] = useState(false);

  const explanationTypes = [
    { 
      id: 'scale', 
      label: '规模指数', 
      mode: type === 'user-repo' ? 'repo' : 'user'
    },
    { 
      id: 'similarity', 
      label: '相似度', 
      mode: type
    },
    { 
      id: 'pool', 
      label: '推荐池算法', 
      mode: type
    },
    { 
      id: 'node', 
      label: '节点分类算法', 
      mode: type
    },
    { 
      id: 'similarity_algo', 
      label: '相似度算法', 
      mode: type
    },
    { 
      id: 'recommend', 
      label: '推荐算法', 
      mode: type
    },
  ];

  const fetchExplanation = async (explainType: string, mode: string) => {
    setLoading(true);
    try {
      console.log(`Fetching explanation for type: ${explainType}, mode: ${mode}`);
      const response = await fetch(`/api/explain?type=${explainType}&mode=${encodeURIComponent(mode)}`);
      const data = await response.json();
      
      if (data.status === 'success') {
        setExplanation(data.explanation);
        setSelectedType(explainType);
      } else {
        console.error('Error response:', data);
        setExplanation('获取解释失败：' + data.message);
      }
    } catch (error) {
      console.error('Fetch error:', error);
      setExplanation('获取解释失败：' + (error instanceof Error ? error.message : '未知错误'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6 bg-white rounded-lg shadow-lg">
      <h3 className="text-2xl font-bold mb-6 text-gray-800">算法解释</h3>
      
      {/* 按钮组 */}
      <div className="flex flex-wrap gap-3 mb-6">
        {explanationTypes.map(({ id, label, mode }) => (
          <Button
            key={id}
            variant={selectedType === id ? "default" : "outline"}
            onClick={() => fetchExplanation(id, mode)}
            disabled={loading}
            className={`
              text-base px-4 py-2 font-medium
              ${selectedType === id 
                ? 'bg-blue-600 text-white hover:bg-blue-700' 
                : 'text-gray-700 hover:bg-gray-100'}
            `}
          >
            {label}
          </Button>
        ))}
      </div>

      {/* 内容区域 */}
      <div className="min-h-[200px]">
        {loading ? (
          <div className="flex items-center justify-center h-[200px]">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500" />
            <span className="ml-3 text-gray-600">加载中...</span>
          </div>
        ) : explanation ? (
          <div className="bg-gray-50 p-6 rounded-lg">
            <pre className="text-base whitespace-pre-wrap text-gray-700 leading-relaxed">
              {explanation}
            </pre>
          </div>
        ) : (
          <div className="flex items-center justify-center h-[200px] text-gray-500">
            请选择要查看的算法说明
          </div>
        )}
      </div>
    </div>
  );
};

export default AlgorithmExplain; 