'use client'

import { useState } from 'react'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import Graph from '@/components/Graph'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { fetchGraphData, fetchRelationshipAnalysis } from '@/app/utils/api'

interface GraphDataType {
  center: { id: string; openrank: number };
  nodes: { id: string; openrank: number }[];
  links: { source: string; target: string }[];
}

export default function Home() {
  const [searchTerm, setSearchTerm] = useState('')
  const [graphData, setGraphData] = useState<GraphDataType | null>(null)
  const [selectedNode, setSelectedNode] = useState(null)
  const [analysis, setAnalysis] = useState('')
  const [platform, setPlatform] = useState('GitHub')
  const [type, setType] = useState('Repo')

  const handleSearch = async (searchType: 'user' | 'repo') => {
    try {
      const data = await fetchGraphData(
        platform.toLowerCase(),
        searchType,
        searchTerm
      )
      setGraphData(data)
    } catch (error) {
      console.error('Error fetching data:', error)
    }
  }

  const handleNodeClick = async (node: any) => {
    setSelectedNode(node)
    try {
      const analysisText = await fetchRelationshipAnalysis(
        graphData?.center?.id,
        node.id
      )
      setAnalysis(analysisText)
    } catch (error) {
      console.error('Error fetching analysis:', error)
    }
  }

  return (
    <main className="min-h-screen bg-[#F3F4F6] relative">
      <div className="absolute inset-0 flex items-center justify-center">
        <div className="w-full max-w-7xl">
          {graphData && (
            <div className="w-full h-[600px] mt-8">
              <Graph
                data={graphData}
                onNodeClick={handleNodeClick}
                selectedNode={selectedNode}
                analysis={analysis}
                type={type.toLowerCase() as 'user' | 'repo'}
              />
            </div>
          )}
        </div>
      </div>

      <div className="relative z-10">
        <div className="bg-white rounded-lg shadow-lg p-8 hover:shadow-xl transition-shadow max-w-4xl mx-auto mt-8">
          <h1 className="text-2xl font-bold text-center mb-6">OpenChain</h1>
          <div className="flex flex-wrap gap-4">
            <Select value={platform} onValueChange={setPlatform}>
              <SelectTrigger className="w-[120px]">
                <SelectValue placeholder="Platform" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="GitHub">GitHub</SelectItem>
                <SelectItem value="Gitee">Gitee</SelectItem>
              </SelectContent>
            </Select>

            <Select value={type} onValueChange={setType}>
              <SelectTrigger className="w-[120px]">
                <SelectValue placeholder="Type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="Repo">Repo</SelectItem>
                <SelectItem value="User">User</SelectItem>
              </SelectContent>
            </Select>

            <Input
              type="text"
              placeholder="键入搜索名称..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="flex-1"
            />

            <Button 
              onClick={() => handleSearch('user')}
              className="bg-[#4285F4] hover:bg-[#3367D6] text-white px-8 rounded-full"
            >
              Find User
            </Button>

            <Button 
              onClick={() => handleSearch('repo')}
              className="bg-[#34A853] hover:bg-[#2E7D32] text-white px-8 rounded-full"
            >
              Find Repo
            </Button>
          </div>
        </div>
      </div>
    </main>
  )
}
