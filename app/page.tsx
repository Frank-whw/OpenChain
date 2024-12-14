'use client'

import { useState } from 'react'
import { Input } from '@/app/components/ui/input'
import { Button } from '@/app/components/ui/button'
import Graph from '@/app/components/Graph'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/app/components/ui/select"
import { fetchRecommendations } from '@/app/utils/api'
import type { Node } from '@/app/components/Graph'

type EntityType = 'user' | 'repo';

export default function Home() {
  const [searchTerm, setSearchTerm] = useState('')
  const [graphData, setGraphData] = useState<any>(null)
  const [selectedNode, setSelectedNode] = useState<Node | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [type, setType] = useState<EntityType>('repo')
  const [findType, setFindType] = useState<EntityType>('repo')

  const handleSearch = async () => {
    setLoading(true)
    setError('')
    try {
      if (!searchTerm) {
        throw new Error('请输入搜索内容')
      }
      
      if (type === 'repo' && !searchTerm.includes('/')) {
        throw new Error('仓库格式应为: owner/repo')
      }

      const result = await fetchRecommendations(type, searchTerm, findType)
      
      if (!result.success || !result.data) {
        throw new Error(result.error || '获取数据失败')
      }
      
      setGraphData(result.data)
    } catch (error: any) {
      setError(error.message || '搜索失败')
      console.error('Search error:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleTypeChange = (value: string) => {
    setType(value as EntityType);
  };

  const handleFindTypeChange = (value: string) => {
    setFindType(value as EntityType);
  };

  return (
    <main className="min-h-screen bg-[#F3F4F6] relative">
      <div className="relative z-10">
        <div className="bg-white rounded-lg shadow-lg p-8 max-w-4xl mx-auto mt-8">
          <h1 className="text-2xl font-bold text-center mb-6">OpenChain</h1>
          
          <div className="flex flex-wrap gap-4">
            <strong className="self-center">GitHub</strong>

            <div className="flex gap-4">
              <Select value={type} onValueChange={handleTypeChange}>
                <SelectTrigger className="w-[120px]">
                  <SelectValue placeholder="主体类型" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="repo">仓库</SelectItem>
                  <SelectItem value="user">用户</SelectItem>
                </SelectContent>
              </Select>

              <Select value={findType} onValueChange={handleFindTypeChange}>
                <SelectTrigger className="w-[120px]">
                  <SelectValue placeholder="推荐类型" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="repo">推荐仓库</SelectItem>
                  <SelectItem value="user">推荐用户</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <Input
              type="text"
              placeholder={type === 'repo' ? "输入仓库 (例: owner/repo)" : "输入用户"}
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="flex-1"
            />

            <Button 
              onClick={handleSearch}
              className="bg-[#4285F4] hover:bg-[#3367D6] text-white px-8 rounded-full"
            >
              查找
            </Button>
          </div>

          {loading && (
            <div className="mt-4 text-center text-gray-600">
              <div className="animate-spin inline-block w-6 h-6 border-4 border-t-blue-500 border-blue-200 rounded-full mr-2"></div>
              正在分析中...
            </div>
          )}

          {error && (
            <div className="mt-4 text-center text-red-500">
              {error}
            </div>
          )}
        </div>

        {graphData && (
          <div className="w-full h-[600px] mt-8">
            <Graph
              data={graphData}
              onNodeClick={setSelectedNode}
              selectedNode={selectedNode}
              type={type}
            />
          </div>
        )}
      </div>
    </main>
  )
}
