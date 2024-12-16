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
  const [type, setType] = useState<EntityType>('user')
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
      setSelectedNode(null)
    } catch (error: any) {
      setError(error.message || '搜索失败')
      console.error('Search error:', error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="min-h-screen bg-[#F3F4F6]">
      <div className="mx-auto py-8 px-4">
        <div className="bg-white rounded-2xl shadow-lg p-6 max-w-4xl mx-auto">
          <h1 className="text-2xl font-bold text-center mb-8">OpenChain</h1>
          
          <div className="flex flex-wrap items-center gap-4">
            <span className="font-bold text-gray-700">GitHub</span>
            
            <div className="flex gap-3">
              <Select value={type} onValueChange={value => setType(value as EntityType)}>
                <SelectTrigger className="w-[100px]">
                  <SelectValue placeholder="用户" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="user">用户</SelectItem>
                  <SelectItem value="repo">仓库</SelectItem>
                </SelectContent>
              </Select>

              <Select value={findType} onValueChange={value => setFindType(value as EntityType)}>
                <SelectTrigger className="w-[100px]">
                  <SelectValue placeholder="推荐仓库" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="repo">推荐仓库</SelectItem>
                  <SelectItem value="user">推荐用户</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <Input
              type="text"
              placeholder={type === 'repo' ? "输入仓库 (例: owner/repo)" : "输入用户名"}
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="flex-1"
            />

            <Button 
              onClick={handleSearch}
              className="bg-[#4285F4] hover:bg-[#3367D6] text-white px-8 rounded-full"
              disabled={loading}
            >
              {loading ? '查找中...' : '查找'}
            </Button>
          </div>

          {error && (
            <div className="mt-4 text-center text-red-500">
              {error}
            </div>
          )}
        </div>

        {graphData && (
          <div className="mt-8 bg-white rounded-2xl shadow-lg p-6 h-[300xl] w-full">
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
