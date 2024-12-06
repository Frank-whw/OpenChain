import { useEffect, useRef } from 'react'
import * as d3 from 'd3'

interface GraphProps {
  data: any
  onNodeClick: (node: any) => void
  selectedNode: any
  analysis: string
  type: 'user' | 'repo'
}

export default function Graph({ data, onNodeClick, selectedNode, analysis, type }: GraphProps) {
  const svgRef = useRef(null)

  useEffect(() => {
    if (!data) return

    const svg = d3.select(svgRef.current)
    svg.selectAll("*").remove()

    const width = window.innerWidth
    const height = window.innerHeight

    const color = type === 'user' ? d3.scaleOrdinal(d3.schemeCategory10) : d3.scaleOrdinal(d3.schemePaired)

    const simulation = d3.forceSimulation(data.nodes)
      .force("link", d3.forceLink(data.links).id(d => d.id).distance(100))
      .force("charge", d3.forceManyBody().strength(-1000))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collision", d3.forceCollide().radius(30))

    const link = svg.append("g")
      .attr("stroke", "#999")
      .attr("stroke-opacity", 0.6)
      .selectAll("line")
      .data(data.links)
      .join("line")
      .attr("stroke-width", d => Math.sqrt(d.value))

    const node = svg.append("g")
      .attr("stroke", "#fff")
      .attr("stroke-width", 1.5)
      .selectAll("circle")
      .data(data.nodes)
      .join("circle")
      .attr("r", d => Math.sqrt(d.openrank) * 5)
      .attr("fill", d => d.id === data.center.id ? "#ff0000" : color(d.group))
      .call(drag(simulation))

    node.append("title")
      .text(d => d.id)

    node.on("click", (event, d) => {
      onNodeClick(d)
    })

    simulation.on("tick", () => {
      link
        .attr("x1", d => d.source.x)
        .attr("y1", d => d.source.y)
        .attr("x2", d => d.target.x)
        .attr("y2", d => d.target.y)

      node
        .attr("cx", d => d.x)
        .attr("cy", d => d.y)
    })

    function drag(simulation) {
      function dragstarted(event) {
        if (!event.active) simulation.alphaTarget(0.3).restart()
        event.subject.fx = event.subject.x
        event.subject.fy = event.subject.y
      }

      function dragged(event) {
        event.subject.fx = event.x
        event.subject.fy = event.y
      }

      function dragended(event) {
        if (!event.active) simulation.alphaTarget(0)
        event.subject.fx = null
        event.subject.fy = null
      }

      return d3.drag()
        .on("start", dragstarted)
        .on("drag", dragged)
        .on("end", dragended)
    }
  }, [data, type])

  return (
    <div className="w-full h-full">
      <svg ref={svgRef} width="100%" height="100%" />
      {selectedNode && (
        <div className="absolute p-4 bg-white rounded-lg shadow-lg left-4 bottom-4 max-w-md">
          <h3 className="text-lg font-bold mb-2">{selectedNode.id}</h3>
          <p className="text-sm">{analysis}</p>
        </div>
      )}
    </div>
  )
}

