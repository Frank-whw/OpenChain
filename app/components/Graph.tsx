'use client';

import React, { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';
import { message } from 'antd';
// import AlgorithmExplain from './AlgorithmExplain';
import { Button } from './ui/button';

export interface Node extends d3.SimulationNodeDatum {
  id: string;
  type: 'user' | 'repo';
  nodeType: 'center' | 'mentor' | 'peer' | 'floating';
  metrics: {
    size: number;
    // 仓库相关指标
    stars?: number;
    forks?: number;
    watchers?: number;
    // 用户相关指标
    followers?: number;
    following?: number;
    public_repos?: number;
  };
  similarity?: number;
}

interface Link extends d3.SimulationLinkDatum<Node> {
  value: number;
  source: Node;
  target: Node;
}

interface GraphData {
  success: boolean;
  error_type?: string;
  message?: string;
  data?: {
    nodes: Node[];
    links: Link[];
    center: Node;
  };
}

interface GraphProps {
  data: GraphData;
  onNodeClick: (node: Node) => void;
  selectedNode: Node | null;
  type: 'user' | 'repo';
}

const Graph: React.FC<GraphProps> = ({ data, onNodeClick, selectedNode, type }) => {
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [popupPosition, setPopupPosition] = useState<{ left: number; top: number }>({ left: 0, top: 0 });
  const [error, setError] = useState<string | null>(null);
  const [aiAnalysis, setAiAnalysis] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  // const [showAlgorithmExplain, setShowAlgorithmExplain] = useState(false);

  // 获取错误提示信息
  const getErrorMessage = (error_type: string, message: string) => {
    const errorMessages: { [key: string]: string } = {
      'RATE_LIMIT_ERROR': '🚫 GitHub API 访问受限',
      'USER_NOT_FOUND': '👤 用户不存在或无法访问',
      'REPO_NOT_FOUND': '📦 仓库不存在或无法访问',
      'NO_USER_REPOS': '📭 该用户没有公开仓库',
      'NO_LANGUAGE_PREFERENCE': '🔍 无法确定用户的编程语言偏好',
      'USER_RECOMMENDATION_ERROR': '🤝 获取用户推荐失败',
      'REPO_RECOMMENDATION_ERROR': '📚 获取仓库推荐失败',
      'NO_CONTRIBUTORS': '👥 该仓库暂无贡献者',
      'NO_RECOMMENDATIONS': '🔍 未找到相关推荐',
      'INTERNAL_ERROR': '⚠️ 服务器内部错误'
    };
    return {
      title: errorMessages[error_type] || '未知错误',
      description: message
    };
  };

  // 请求 AI 分析
  const requestAnalysis = async (nodeA: string, nodeB: string) => {
    setIsLoading(true);
    setAiAnalysis('');
    
    try {
      console.log('Requesting analysis for:', nodeA, nodeB);
      const response = await fetch(`/api/analyze?node_a=${encodeURIComponent(nodeA)}&node_b=${encodeURIComponent(nodeB)}`, {
        method: 'GET',
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json',
        },
        cache: 'no-store'
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const result = await response.json();
      console.log('Analysis response:', result);
      
      if (result.status === 'success' && result.analysis) {
        setAiAnalysis(result.analysis);
      } else {
        // 获取错误信息
        const errorInfo = getErrorMessage(result.error_type || 'INTERNAL_ERROR', result.message || '分析失败，请稍后重试');
        message.error({
          content: (
            <div>
              <div style={{ fontWeight: 'bold', marginBottom: '4px' }}>{errorInfo.title}</div>
              <div>{errorInfo.description}</div>
            </div>
          ),
          duration: 5
        });
        setAiAnalysis('AI 分析失败：' + (result.message || '未知错误'));
      }
    } catch (error) {
      console.error('Failed to get AI analysis:', error);
      message.error({
        content: (
          <div>
            <div style={{ fontWeight: 'bold', marginBottom: '4px' }}>⚠️ AI 分析请求失败</div>
            <div>{error instanceof Error ? error.message : '网络错误，请稍后重试'}</div>
          </div>
        ),
        duration: 5
      });
      setAiAnalysis('AI 分析请求失败：' + (error instanceof Error ? error.message : '网络错误，请稍后重试'));
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (!svgRef.current || !containerRef.current || !data?.data) return;

    const nodes = data.data.nodes || [];
    const links = data.data.links || [];
    const center = data.data.center;

    // 检查是否有错误
    if (!data.success) {
      const errorInfo = getErrorMessage(data.error_type || 'INTERNAL_ERROR', data.message || '未知错误');
      setError(errorInfo.title);
      return;
    }

    // 如果请求成功但没有数据
    if (nodes.length === 0) {
      setError('没有找到推荐结果');
      return;
    }

    setError(null);

    // 获取容器的宽高和红框位置
    const container = containerRef.current;
    const rect = container.getBoundingClientRect();
    setPopupPosition({
      left: rect.left - 60,
      top: rect.top - 260,
    });

    const width = container.clientWidth;
    const height = container.clientHeight;

    // 初始化 SVG
    const svg = d3.select(svgRef.current)
      .attr('width', '100%')
      .attr('height', '100%')
      .attr('viewBox', [0, 0, width, height].join(' '))
      .style('display', 'block')
      .style('background', 'transparent');

    svg.selectAll('*').remove();

    // 创建主绘图组
    const g = svg.append('g')
      .attr('width', width)
      .attr('height', height);

    // 缩放行为
    const zoom = d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.2, 4])
      .on('zoom', (event) => {
        g.attr('transform', event.transform.toString());
      });

    svg.call(zoom);

  // 修改计算节点半径的函数
  const getNodeRadius = (d: Node) => {
    const baseSize = d.metrics.size || 20;
    
    if (d.nodeType === 'center') {
      return 45;  // 中心节点大小保持不变
    }
    
    if (d.nodeType === 'mentor') {
      // 导师节点：25-40px，使用指数函数放大差异
      return 25 + Math.pow(Math.min(baseSize, 40) / 40, 0.5) * 15;
    }
    
    if (d.nodeType === 'peer') {
      // 同伴节点：20-30px，使用指数函数
      return 20 + Math.pow(Math.min(baseSize, 40) / 40, 0.5) * 10;
    }
    
    // 游离节点：15-25px，根据相似度决定大小
    const similarity = d.similarity || 0;
    return 15 + Math.pow(similarity, 0.5) * 10;
  };

    // 修改获取节点颜色的函数
    const getNodeColor = (d: Node) => {
      if (d.nodeType === 'center') {
        return d.type === 'user' ? '#1E40AF' : '#9333EA';  // 深蓝色表示用户，深紫色表示仓库
      }
      if (d.nodeType === 'mentor') {
        return d.type === 'user' ? '#3B82F6' : '#A855F7';  // 加深蓝/紫色
      }
      if (d.nodeType === 'peer') {
        return d.type === 'user' ? '#60A5FA' : '#C084FC';  // 加深蓝/紫色
      }
      // 游离节点使用渐变，颜色加深
      if (d.type === 'user') {
        const similarity = d.similarity || 0;
        // 蓝色渐变：从浅到深，整体加深
        return similarity > 0.7 ? '#3B82F6' :  // 更深的蓝色
               similarity > 0.5 ? '#60A5FA' :
               similarity > 0.3 ? '#60A5FA' : '#93C5FD';
      } else {
        const similarity = d.similarity || 0;
        // 紫色渐变：从浅到深，整体加深 - 加深仓库的颜色
        return similarity > 0.7 ? '#9333EA' :  // 最深的紫色
               similarity > 0.5 ? '#A855F7' :  // 深紫色
               similarity > 0.3 ? '#A855F7' : '#C084FC';  // 中等紫色
      }
    };

    // 获取文本颜色
    const getTextColor = (d: Node) => {
      if (d.id === data.data.center.id) return '#fff';  // 中心节点文本为白色
      return '#333';  // 其他节点文本为深
    };

    // 力导向图配置
    const simulation = d3.forceSimulation<Node>(nodes)
      .force('link', d3.forceLink<Node, Link>(links)
        .id(d => d.id)
        .distance(link => {
          const similarity = link.value || 0;
          // 连接线距离根据相似度和节点类型调整
          const minDistance = 100;
          const maxDistance = 400;
          const source = link.source as Node;
          const target = link.target as Node;
          
          // 如果是导师节点，增加距离以避免聚集
          if (source.nodeType === 'mentor' || target.nodeType === 'mentor') {
            return minDistance + Math.pow(1 - similarity, 3) * (maxDistance - minDistance) + 50;
          }
          
          return minDistance + Math.pow(1 - similarity, 4) * (maxDistance - minDistance);
        }))
      .force('charge', d3.forceManyBody()
        .strength((d: any) => {
          const node = d as Node;
          if (node.nodeType === 'center') return -2000;
          if (node.nodeType === 'mentor') return -1200;  // 增加导师节点的斥力
          if (node.nodeType === 'peer') return -800;
          if (node.nodeType === 'floating') return -400;
          return -400;
        }))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collision', d3.forceCollide()
        .radius(d => {
          // 增加导师节点的碰撞半径
          const baseRadius = getNodeRadius(d);
          return d.nodeType === 'mentor' ? baseRadius + 12 : baseRadius + 8;
        })
        .strength(0.8))
      .force('radial', d3.forceRadial(
        (d: Node) => {
          if (d.nodeType === 'center') return 0;
          
          const similarity = d.similarity || 0;
          
          if (d.nodeType === 'floating') {
            const baseDistance = 400;
            return baseDistance + Math.pow(1 - similarity, 4) * 300;
          }
          
          // 调整导师和同伴节点的径向距离
          const baseDistance = 150;
          const maxDistance = 400;
          
          if (d.nodeType === 'mentor') {
            // 导师节点使用更大的基础距离和更强的相似度影响
            return (baseDistance + 30) + Math.pow(1 - similarity, 2) * (maxDistance - baseDistance);
          } else {
            return (baseDistance + 50) + Math.pow(1 - similarity, 3) * (maxDistance - baseDistance);
          }
        },
        width / 2,
        height / 2
      ).strength((d: Node) => {
        // 增加径向力的差异
        if (d.nodeType === 'floating') {
          const similarity = d.similarity || 0;
          return 0.1 + Math.pow(1 - similarity, 2) * 0.15;
        }
        if (d.nodeType === 'mentor') {
          const similarity = d.similarity || 0;
          // 增加导师节点的径向力，使其分布更均匀
          return 0.4 + Math.pow(similarity, 2) * 0.3;
        }
        if (d.nodeType === 'peer') {
          const similarity = d.similarity || 0;
          return 0.2 + Math.pow(similarity, 2) * 0.25;
        }
        return 0.1;
      }));

    // 绘制连接线
    const link = g.append('g')
      .selectAll('line')
      .data(links)
      .join('line')
      .attr('stroke', '#E5E5E5')
      .attr('stroke-opacity', 0.6)
      .attr('stroke-width', 1)
      .attr('stroke-dasharray', function(this: SVGLineElement | null) {
        if (!this) return '';
        return `${this.getTotalLength()} ${this.getTotalLength()}`;
      } as any)
      .attr('stroke-dashoffset', function(this: SVGLineElement | null) {
        if (!this) return 0;
        return this.getTotalLength();
      } as any);

    // 创建节点组
    const node = g.append('g')
      .selectAll<SVGGElement, Node>('g')
      .data(nodes)
      .join<SVGGElement>('g')
      .attr('class', 'node');

    // 拖拽行为
    const dragBehavior = d3.drag<SVGGElement, Node>()
      .on('start', (event) => {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        const d = event.subject;
        d.fx = d.x;
        d.fy = d.y;
      })
      .on('drag', (event) => {
        const d = event.subject;
        d.fx = event.x;
        d.fy = event.y;
      })
      .on('end', (event) => {
        if (!event.active) simulation.alphaTarget(0);
        const d = event.subject;
        d.fx = null;
        d.fy = null;
      });

    node.call(dragBehavior);

    // 修改节点绘制部分
    node.append('circle')
      .attr('r', getNodeRadius)
      .attr('fill', getNodeColor)
      .attr('stroke', '#fff')
      .attr('stroke-width', 1.5)
      .attr('opacity', d => {
        if (d.nodeType === 'floating') return 0.6;
        if (d.nodeType === 'peer') return 0.9;
        return 1;
      })
      .style('transform-origin', 'center')
      .style('transition', 'all 0.3s ease')
      .on('mouseover', function(event, d) {
        // 放大效果
        d3.select(this)
          .transition()
          .duration(200)
          .attr('r', d => getNodeRadius(d) * 1.2)
          .style('filter', 'drop-shadow(0 0 6px rgba(0,0,0,0.2))');
          
        // 如果是漂浮节点显示文本
        if (d.nodeType === 'floating') {
          d3.select(this.parentNode)
            .select('text')
            .text(d.id)
            .transition()
            .duration(200)
            .attr('opacity', 0.8);
        }
        
        // 显示详细信息标签
        const tooltip = d3.select('body').append('div')
          .attr('class', 'tooltip')
          .style('position', 'absolute')
          .style('background', 'white')
          .style('padding', '8px 12px')
          .style('border', '1px solid #ccc')
          .style('border-radius', '6px')
          .style('pointer-events', 'none')
          .style('box-shadow', '0 2px 8px rgba(0,0,0,0.15)')
          .style('z-index', '1000')
          .style('opacity', 0)
          .style('font-size', '12px')
          .style('max-width', '250px');

        let tooltipContent = `
          <div class="font-bold text-base mb-1" style="color: ${getNodeColor(d)}">${d.id}</div>
        `;

        if (d.nodeType !== 'center') {
          tooltipContent += `
            <div class="mb-1" style="color: #666">
              相似度: <span style="color: #000; font-weight: 500">${((d.similarity || 0) * 100).toFixed(1)}%</span>
            </div>
          `;
        }

        tooltipContent += `
          <div style="color: #666">
            ${d.type === 'user' ? `
              关注数: <span style="color: #000">${d.metrics.following || 0}</span><br/>
              粉丝数: <span style="color: #000">${d.metrics.followers || 0}</span><br/>
              仓库数: <span style="color: #000">${d.metrics.public_repos || 0}</span>
            ` : `
              Stars: <span style="color: #000">${d.metrics.stars || 0}</span><br/>
              Forks: <span style="color: #000">${d.metrics.forks || 0}</span><br/>
              Watchers: <span style="color: #000">${d.metrics.watchers || 0}</span>
            `}
            <br/>规模指数: <span style="color: #000">${d.metrics.size?.toFixed(1) || 0}</span>
          </div>
          ${d.nodeType !== 'center' ? `
            <div class="mt-1 text-xs" style="color: #888">
              ${d.nodeType === 'mentor' ? '导师节点' : 
                d.nodeType === 'peer' ? '同伴节点' : '游离节点'}
            </div>
          ` : ''}
        `;

        tooltip.html(tooltipContent)
          .style('left', (event.pageX + 10) + 'px')
          .style('top', (event.pageY - 10) + 'px')
          .transition()
          .duration(200)
          .style('opacity', 1);
          
        // 高亮相连的节点和连接线
        const connectedNodes = new Set();
        link.each(function(l) {
          if (l.source === d || l.target === d) {
            connectedNodes.add(l.source.id);
            connectedNodes.add(l.target.id);
            d3.select(this)
              .transition()
              .duration(200)
              .attr('stroke', '#666')
              .attr('stroke-width', 2)
              .attr('stroke-opacity', 1);
          }
        });
        
        node.selectAll('circle')
          .style('opacity', n => connectedNodes.has(n.id) ? 1 : 0.3);
      })
      .on('mousemove', (event) => {
        // 跟随鼠标移动
        d3.select('.tooltip')
          .style('left', (event.pageX + 10) + 'px')
          .style('top', (event.pageY - 10) + 'px');
      })
      .on('mouseout', function(event, d) {
        // 移除tooltip
        d3.select('.tooltip').remove();
        
        // 恢复原始大小
        d3.select(this)
          .transition()
          .duration(200)
          .attr('r', getNodeRadius)
          .style('filter', null);
          
        // 恢复所有节点和连接线的样式
        link
          .transition()
          .duration(200)
          .attr('stroke', '#E5E5E5')
          .attr('stroke-width', 1)
          .attr('stroke-opacity', 0.6);
          
        node.selectAll('circle')
          .style('opacity', d => {
            if (d.nodeType === 'floating') return 0.6;
            if (d.nodeType === 'peer') return 0.9;
            return 1;
          });
          
        // 如果是漂浮节点，隐藏文本
        if (d.nodeType === 'floating') {
          d3.select(this.parentNode)
            .select('text')
            .text('')
            .transition()
            .duration(200)
            .attr('opacity', 0);
        }
      });

    // 添加点击波纹效果
    node.append('circle')
      .attr('class', 'ripple')
      .attr('r', 0)
      .attr('fill', 'none')
      .attr('stroke', 'none')
      .style('pointer-events', 'none');

    // 添加文本标签
    node.append('text')
      .text(d => {
        // 对于漂浮节点，只在悬停时显示文本
        if (d.nodeType === 'floating') {
          return '';  // 默认不显示文本
        }
        return d.id;
      })
      .attr('x', d => d.nodeType === 'center' ? 0 : 30)
      .attr('y', d => d.nodeType === 'center' ? 0 : 4)
      .attr('dominant-baseline', d => d.nodeType === 'center' ? 'middle' : 'auto')
      .attr('text-anchor', d => d.nodeType === 'center' ? 'middle' : 'start')
      .attr('font-size', d => d.nodeType === 'center' ? '14px' : '12px')
      .attr('fill', getTextColor)
      .attr('opacity', d => {
        // 漂浮节点文本默认透明
        if (d.nodeType === 'floating') return 0;
        return 0.8;
      });

    // 更新位置
    simulation.on('tick', () => {
      link
        .attr('x1', d => (d.source as Node).x!)
        .attr('y1', d => (d.source as Node).y!)
        .attr('x2', d => (d.target as Node).x!)
        .attr('y2', d => (d.target as Node).y!);

      node.attr('transform', (d: Node) => `translate(${d.x},${d.y})`);
    });

    // 修改点击事件处理
    node.on('click', async (event, d) => {
      event.stopPropagation();
      const node = d as Node;
      onNodeClick(node);
      
      // 添加点击波纹动画
      const ripple = d3.select(event.currentTarget).select('.ripple');
      ripple
        .attr('stroke', getNodeColor(node))
        .attr('stroke-width', 2)
        .attr('stroke-opacity', 1)
        .transition()
        .duration(700)
        .attr('r', getNodeRadius(node) * 2)
        .attr('stroke-opacity', 0)
        .on('end', function() {
          d3.select(this).attr('r', 0);
        });
      
      // 如果点击的不是中心节点，请求 AI 分析
      if (node.id !== data.data?.center.id) {
        await requestAnalysis(data.data?.center.id || '', node.id);
      }
    });

    // 修改连接线动画
    link
      .attr('stroke-dasharray', function(this: SVGLineElement) {
        const length = this?.getTotalLength() || 0;
        return `${length} ${length}`;
      })
      .attr('stroke-dashoffset', function(this: SVGLineElement) {
        return this?.getTotalLength() || 0;
      })
      .transition()
      .duration(1000)
      .attr('stroke-dashoffset', 0);

    // 添加初始化动画
    node
      .style('opacity', 0)
      .transition()
      .duration(800)
      .delay((d, i) => {
        // 让漂浮节点最后出现
        if (d.nodeType === 'floating') return 1000 + i * 50;
        return i * 50;
      })
      .style('opacity', d => {
        if (d.nodeType === 'floating') return 0.6;
        if (d.nodeType === 'peer') return 0.9;
        return 1;
      });

    // 添加调试日志
    console.log('Nodes:', data.data.nodes);
    console.log('Links:', data.data.links);

    return () => {
      simulation.stop();
    };
  }, [data, onNodeClick]);

  // 如果有错误，显示错误信息
  if (error) {
    return (
      <div style={{ 
        width: '100%', 
        height: '400px', 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center',
        flexDirection: 'column',
        color: '#ff4d4f',
        backgroundColor: '#fff1f0',
        border: '1px solid #ffccc7',
        borderRadius: '4px',
        padding: '20px'
      }}>
        <h3 className="text-xl font-bold mb-4">推荐失败</h3>
        <div className="text-center">
          <p className="mb-2">{error}</p>
          <p className="text-sm text-gray-500 mb-2">
            可能的原因：
          </p>
          <ul className="list-disc text-left mt-2 ml-4 text-sm text-gray-500">
            <li>GitHub API 访问限制</li>
            <li>网络连接问题</li>
            <li>用户或仓库不存在</li>
            <li>没有找到合适的推荐结果</li>
          </ul>
        </div>
      </div>
    );
  }

  return (
    <div className="relative">
      <div 
        ref={containerRef} 
        style={{ 
          width: '100%', 
          height: 'calc(100vh - 6rem)',
          position: 'relative',
          background: 'transparent',
        }}
      >
        <svg 
          ref={svgRef}
          style={{ 
            width: '100%', 
            height: '100%',
            display: 'block',
            background: 'transparent',
          }} 
        />
      </div>

      {/* <div className="absolute top-4 right-4">
        <Button
          onClick={() => setShowAlgorithmExplain(!showAlgorithmExplain)}
          variant="outline"
          className="bg-white shadow-sm hover:bg-gray-50"
        >
          {showAlgorithmExplain ? '隐藏算法解释' : '查看算法解释'}
        </Button>
      </div> */}

      {selectedNode && data?.data?.center && selectedNode.id !== data.data.center.id && (
        <div
          className="absolute"
          style={{
            left: `${popupPosition.left}px`,
            top: `${popupPosition.top}px`,
            width: '24rem',
          }}
        >
          <div className="bg-white rounded-lg shadow-lg p-6 max-h-[80vh] overflow-y-auto">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-bold">{selectedNode.id}</h3>
            </div>
            {isLoading ? (
              <div className="flex flex-col items-center justify-center h-32">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mb-4" />
                <div className="text-gray-500">正在分析关系...</div>
              </div>
            ) : aiAnalysis ? (
              <div className="prose prose-sm max-w-none">
                {aiAnalysis.startsWith('AI 分析失败') || aiAnalysis.startsWith('AI 分析请求失败') ? (
                  <div className="text-red-500 bg-red-50 p-4 rounded-lg">
                    {aiAnalysis}
                  </div>
                ) : (
                  <div className="whitespace-pre-wrap text-gray-700">
                    {aiAnalysis}
                  </div>
                )}
              </div>
            ) : (
              <div className="text-gray-500 text-center py-4">
                正在等待 AI 分析...
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default Graph;