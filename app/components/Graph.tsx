'use client';

import React, { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';
import { message } from 'antd';

export interface Node extends d3.SimulationNodeDatum {
  id: string;
  group: number;
  type: 'user' | 'repo';
  nodeType: 'center' | 'mentor' | 'peer' | 'floating';
  metrics: {
    size: number;
    stars?: number;
    followers?: number;
  };
  similarity?: number;
}

interface Link extends d3.SimulationLinkDatum<Node> {
  value: number;
  source: Node;
  target: Node;
}

interface GraphData {
  nodes: Node[];
  links: Link[];
  center: Node;
  status?: string;
  message?: string;
  recommendations?: Array<{
    name: string;
    metrics: {
      stars?: number;
      forks?: number;
      size?: number;
    };
    similarity: number;
  }>;
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
      
      const data = await response.json();
      console.log('Analysis response:', data);
      
      if (data.status === 'success' && data.analysis) {
        setAiAnalysis(data.analysis);
      } else {
        throw new Error(data.message || '分析失败，请稍后重试');
      }
    } catch (error) {
      console.error('Failed to get AI analysis:', error);
      setAiAnalysis(error instanceof Error ? error.message : '获取 AI 分析失败，请稍后重试');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (!data || !svgRef.current || !containerRef.current) return;

    // 检查是否有错误信息
    if (data.status === 'error') {
      message.error(data.message || '获取推荐数据失败');
      setError(data.message || '获取推荐数据失败');
      return;
    }

    setError(null);

    // 检查节点数据而不是 recommendations
    if (!data.nodes || data.nodes.length === 0) {
      message.warning('没有找到推荐结果');
      return;
    }

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
      // 游离节点使用渐变色，根据相似度变化
      if (d.type === 'user') {
        const similarity = d.similarity || 0;
        // 蓝色渐变：从浅到深
        return similarity > 0.7 ? '#60A5FA' :
               similarity > 0.5 ? '#93C5FD' :
               similarity > 0.3 ? '#BFDBFE' : '#DBEAFE';
      } else {
        const similarity = d.similarity || 0;
        // 紫色渐变：从浅到深
        return similarity > 0.7 ? '#C084FC' :
               similarity > 0.5 ? '#DDD6FE' :
               similarity > 0.3 ? '#E9D5FF' : '#F3E8FF';
      }
    };

    // 获取文本颜色
    const getTextColor = (d: Node) => {
      if (d.id === data.center.id) return '#fff';  // 中心节点文本为白色
      return '#333';  // 其他节点文本为深灰色
    };

    // 力导向图配置
    const simulation = d3.forceSimulation<Node>(data.nodes)
      .force('link', d3.forceLink<Node, Link>(data.links)
        .id(d => d.id)
        .distance(link => {
          const similarity = link.value || 0;
          // 缩小连接线的距离范围
          const minDistance = 50;   // 减小最小距离
          const maxDistance = 400;  // 减小最大距离
          return minDistance + Math.pow(1 - similarity, 4) * (maxDistance - minDistance);
        }))
      .force('charge', d3.forceManyBody()
        .strength((d: Node) => {
          const similarity = d.similarity || 0;
          if (d.nodeType === 'center') return -2000;  // 减小中心节点斥力
          
          const rank = data.nodes
            .filter(n => n.nodeType === d.nodeType)
            .sort((a, b) => (b.similarity || 0) - (a.similarity || 0))
            .findIndex(n => n.id === d.id);
          
          const rankFactor = Math.pow(1 - rank / Math.max(1, data.nodes.filter(n => n.nodeType === d.nodeType).length - 1), 0.5);
          
          const baseStrength = {
            'mentor': -800,   // 减小斥力
            'peer': -600,     // 减小斥力
            'floating': -400  // 减小斥力
          }[d.nodeType] || -400;
          
          return baseStrength * (1 + similarity * 0.3 + rankFactor * 0.7);
        }))
      .force('center', d3.forceCenter(width / 2, height / 2).strength(0.1))
      .force('collision', d3.forceCollide()
        .radius((d: Node) => getNodeRadius(d) + 5)  // 显式类型标注
        .strength(0.5))
      .force('radial', d3.forceRadial(
        (d: Node) => {
          if (d.id === data.center.id) return 0;
          const similarity = d.similarity || 0;
          
          const getDistanceBySimilarity = (sim: number, minDist: number, maxDist: number) => {
            const rank = data.nodes
              .filter(n => n.nodeType === d.nodeType)
              .sort((a, b) => (b.similarity || 0) - (a.similarity || 0))
              .findIndex(n => n.id === d.id);
            
            const rankRatio = rank / Math.max(1, data.nodes.filter(n => n.nodeType === d.nodeType).length - 1);
            const similarityFactor = Math.pow(1 - sim, 2);
            const rankFactor = Math.pow(rankRatio, 0.5);
            
            return minDist + (similarityFactor * 0.3 + rankFactor * 0.7) * (maxDist - minDist);
          };
          
          if (d.nodeType === 'mentor') {
            // 导师节点：100-400px (缩小范围)
            return getDistanceBySimilarity(similarity, 100, 400);
          }
          if (d.nodeType === 'peer') {
            // 同伴节点：150-500px (缩小范围)
            return getDistanceBySimilarity(similarity, 150, 500);
          }
          if (d.nodeType === 'floating') {
            // 游离节点：250-600px (缩小范围)
            return getDistanceBySimilarity(similarity, 250, 600);
          }
          return 150;
        },
        width / 2,
        height / 2
      ).strength((d: Node) => {
        // 增加径向力强度，使节点更稳定
        const similarity = d.similarity || 0;
        if (d.nodeType === 'floating') {
          return 0.4 + similarity * 0.4;  // 0.4-0.8 增加基础强度
        }
        if (d.nodeType === 'mentor') {
          return 0.8 + similarity * 0.2;  // 0.8-1.0
        }
        if (d.nodeType === 'peer') {
          return 0.6 + similarity * 0.3;  // 0.6-0.9
        }
        return 1;
      }))

    // 绘制连接线
    const link = g.append('g')
      .selectAll('line')
      .data(data.links)
      .join('line')
      .attr('stroke', '#E5E5E5')
      .attr('stroke-opacity', 0.6)
      .attr('stroke-width', 1);

    // 创建节点组
    const node = g.append('g')
      .selectAll<SVGGElement, Node>('g')
      .data(data.nodes)
      .join<SVGGElement>('g');

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
        if (d.nodeType === 'floating') return 0.8;
        if (d.nodeType === 'peer') return 0.9;
        return 1;
      })
      // 添加过渡动画
      .style('transform-origin', 'center')
      .style('transition', 'all 0.3s ease')
      // 修改节点的悬停效果
      .on('mouseover', function(event, d) {
        // 放大效果
        d3.select(this)
          .transition()
          .duration(200)
          .attr('r', d => getNodeRadius(d) * 1.2)
          .style('filter', 'drop-shadow(0 0 6px rgba(0,0,0,0.2))');
          
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
            if (d.nodeType === 'floating') return 0.8;
            if (d.nodeType === 'peer') return 0.9;
            return 1;
          });
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
      .text(d => d.nodeType === 'floating' ? '' : d.id)  // 游离节点默认不显示文本
      .attr('x', d => d.nodeType === 'center' ? 0 : 30)
      .attr('y', d => d.nodeType === 'center' ? 0 : 4)
      .attr('dominant-baseline', d => d.nodeType === 'center' ? 'middle' : 'auto')
      .attr('text-anchor', d => d.nodeType === 'center' ? 'middle' : 'start')
      .attr('font-size', d => d.nodeType === 'center' ? '14px' : '12px')
      .attr('fill', getTextColor)
      .attr('opacity', d => d.nodeType === 'floating' ? 0 : 0.8);

    // 更新位置
    simulation.on('tick', () => {
      link
        .attr('x1', d => (d.source as Node).x!)
        .attr('y1', d => (d.source as Node).y!)
        .attr('x2', d => (d.target as Node).x!)
        .attr('y2', d => (d.target as Node).y!);

      node.attr('transform', d => `translate(${d.x},${d.y})`);
    });

    // 修改点击事件处理
    node.on('click', async (event, d) => {
      event.stopPropagation();
      onNodeClick(d);
      
      // 添加点击波纹动画
      const ripple = d3.select(event.currentTarget).select('.ripple');
      ripple
        .attr('stroke', getNodeColor(d))
        .attr('stroke-width', 2)
        .attr('stroke-opacity', 1)
        .transition()
        .duration(700)
        .attr('r', getNodeRadius(d) * 2)
        .attr('stroke-opacity', 0)
        .on('end', function() {
          d3.select(this).attr('r', 0);
        });
      
      // 如果点击的不是中心节点，请求 AI 分析
      if (d.id !== data.center.id) {
        await requestAnalysis(data.center.id, d.id);
      }
    });

    // 添加连接线动画
    link
      .attr('stroke-dasharray', function() {
        const length = this.getTotalLength();
        return `${length} ${length}`;
      })
      .attr('stroke-dashoffset', function() {
        return this.getTotalLength();
      })
      .transition()
      .duration(1000)
      .attr('stroke-dashoffset', 0);

    // 添加初始化动画
    node
      .style('opacity', 0)
      .transition()
      .duration(800)
      .delay((d, i) => i * 50)  // 错开每个节点的出现时间
      .style('opacity', 1);

    // 添加调试日志
    console.log('Nodes:', data.nodes);
    console.log('Links:', data.links);

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
          <p className="text-sm text-gray-500">
            可能的原因：
            <ul className="list-disc text-left mt-2 ml-4">
              <li>GitHub API 访问限制</li>
              <li>网络连接问题</li>
              <li>用户或仓库不存在</li>
              <li>没有找到合适的推荐结果</li>
            </ul>
          </p>
        </div>
      </div>
    );
  }

  return (
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
      {selectedNode && selectedNode.id !== data.center.id && (
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
              <div className="flex items-center justify-center h-32">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500" />
              </div>
            ) : aiAnalysis ? (
              <div className="prose prose-sm max-w-none">
                <div className="whitespace-pre-wrap text-gray-700">
                  {aiAnalysis}
                </div>
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