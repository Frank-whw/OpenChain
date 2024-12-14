'use client';
import { schemeCategory10, schemePaired } from 'd3-scale-chromatic';
import { scaleOrdinal } from 'd3-scale';
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

  useEffect(() => {
    if (!data || !svgRef.current) return;

    const svg = d3.select<SVGSVGElement, unknown>(svgRef.current);
    svg.selectAll("*").remove();

    const width = window.innerWidth;
    const height = window.innerHeight;

    // 创建一个容器组来包含所有可缩放的元素
    const g = svg.append("g");

    // 定义缩放行为
    const zoom = d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.1, 4])
      .on("zoom", (event) => {
        g.attr("transform", event.transform.toString());
      });

    // 应用缩放行为到 SVG
    (svg as any).call(zoom);

    const color = type === 'user' ? d3.scaleOrdinal(schemeCategory10) : d3.scaleOrdinal(schemePaired);

    const simulation = d3.forceSimulation<Node>(data.nodes)
      .force("link", d3.forceLink<Node, Link>(data.links).id(d => d.id).distance(100))
      .force("charge", d3.forceManyBody().strength(-1000))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collision", d3.forceCollide().radius(30));

    const link = g.append("g")
      .attr("stroke", "#999")
      .attr("stroke-opacity", 0.6)
      .selectAll("line")
      .data(data.links)
      .join("line")
      .attr("stroke-width", d => Math.sqrt(d.value));

    const node = g.append("g")
      .attr("stroke", "#fff")
      .attr("stroke-width", 1.5)
      .selectAll("circle")
      .data(data.nodes)
      .join("circle")
      .attr("r", d => Math.sqrt(d.openrank) * 5)
      .attr("fill", d => d.id === data.center.id ? "#ff0000" : color(String(d.group)))
      .call(drag(simulation) as any);

    // 添加节点标签
    const labels = g.append("g")
      .selectAll("text")
      .data(data.nodes)
      .join("text")
      .text(d => d.id)
      .attr("font-size", "8px")
      .attr("dx", 12)
      .attr("dy", 4);

    node.append("title")
      .text(d => d.id);

    node.on("click", (event, d) => {
      event.stopPropagation();
      onNodeClick(d);
    });

    simulation.on("tick", () => {
      link
        .attr("x1", d => (d.source as Node).x || 0)
        .attr("y1", d => (d.source as Node).y || 0)
        .attr("x2", d => (d.target as Node).x || 0)
        .attr("y2", d => (d.target as Node).y || 0);

      node
        .attr("cx", d => d.x || 0)
        .attr("cy", d => d.y || 0);

      labels
        .attr("x", d => d.x || 0)
        .attr("y", d => d.y || 0);
    });

    function drag(simulation: d3.Simulation<Node, Link>) {
      function dragstarted(event: any) {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        event.subject.fx = event.subject.x;
        event.subject.fy = event.subject.y;
      }

      function dragged(event: any) {
        event.subject.fx = event.x;
        event.subject.fy = event.y;
      }

      function dragended(event: any) {
        if (!event.active) simulation.alphaTarget(0);
        event.subject.fx = null;
        event.subject.fy = null;
      }

      return d3.drag<SVGElement, Node>()
        .on("start", dragstarted)
        .on("drag", dragged)
        .on("end", dragended);
    }

    // 双击重置缩放
    svg.on("dblclick.zoom", null);
    svg.on("dblclick", () => {
      svg.transition()
        .duration(750)
        .call(zoom.transform as any, d3.zoomIdentity);
    });

  }, [data, type]);

  return (
    <div className="w-full h-full">
      <svg ref={svgRef} width="100%" height="100%" />
      {selectedNode && (
        <div className="absolute p-4 bg-white rounded-lg shadow-lg left-4 bottom-4 max-w-md">
          <h3 className="text-lg font-bold mb-2">{selectedNode.id}</h3>
          <p className="text-sm">OpenRank: {selectedNode.openrank.toFixed(2)}</p>
        </div>
      )}
    </div>
  );
};

export default Graph; 