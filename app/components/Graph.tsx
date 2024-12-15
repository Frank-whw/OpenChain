'use client';

import React, { useEffect, useRef } from 'react';
import * as d3 from 'd3';

export interface Node extends d3.SimulationNodeDatum {
  id: string;
  group: number;
  openrank: number;
  x?: number;
  y?: number;
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

  useEffect(() => {
    if (!data || !svgRef.current || !containerRef.current) return;

    const container = containerRef.current;
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

    // 力导向图配置
    const simulation = d3.forceSimulation<Node>(data.nodes)
      .force('link', d3.forceLink<Node, Link>(data.links)
        .id(d => d.id)
        .distance(80))
      .force('charge', d3.forceManyBody()
        .strength(-300))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collision', d3.forceCollide()
        .radius(40));

    // 绘制连接线
    const link = g.append('g')
      .selectAll('line')
      .data(data.links)
      .join('line')
      .attr('stroke', '#ccc')
      .attr('stroke-opacity', 0.6)
      .attr('stroke-width', d => Math.sqrt(d.value));

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

    // 添加节点圆形
    node.append('circle')
      .attr('r', d => Math.max(Math.sqrt(d.openrank) * 4, 12))
      .attr('fill', d => d.id === data.center.id ? '#ff6b6b' : '#4285F4')
      .attr('stroke', '#fff')
      .attr('stroke-width', 1.5);

    // 添加文本标签
    node.append('text')
      .text(d => d.id)
      .attr('x', d => Math.max(Math.sqrt(d.openrank) * 4, 12) + 4)
      .attr('y', 4)
      .attr('font-size', '10px')
      .attr('fill', '#333');

    // 更新位置
    simulation.on('tick', () => {
      link
        .attr('x1', d => (d.source as Node).x!)
        .attr('y1', d => (d.source as Node).y!)
        .attr('x2', d => (d.target as Node).x!)
        .attr('y2', d => (d.target as Node).y!);

      node.attr('transform', d => `translate(${d.x},${d.y})`);
    });

    // 点击事件
    node.on('click', (event, d) => {
      event.stopPropagation();
      onNodeClick(d);
    });

    return () => {
      simulation.stop();
    };
  }, [data, type, onNodeClick]);

  return (
    <div 
      ref={containerRef} 
      style={{ 
        width: '100%', 
        height: 'calc(100vh - 6rem)',
        position: 'relative',
        background: 'transparent'
      }}
    >
      <svg 
        ref={svgRef}
        style={{ 
          width: '100%', 
          height: '100%',
          display: 'block',
          background: 'transparent'
        }} 
      />
      {selectedNode && (
        <div className="absolute p-4 bg-white rounded-lg shadow-lg left-4 bottom-4 max-w-md">
          <h3 className="text-lg font-bold mb-2">{selectedNode.id}</h3>
          <p className="text-sm">
            OpenRank: {selectedNode.openrank ? selectedNode.openrank.toFixed(2) : 'N/A'}
          </p>
        </div>
      )}
    </div>
  );
};

export default Graph;