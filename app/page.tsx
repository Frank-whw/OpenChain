'use client'

import { useState } from 'react'
import { Input } from '@/app/components/ui/input'
import { Button } from '@/app/components/ui/button'
import Graph from '@/app/components/Graph'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/app/components/ui/select"
import { fetchRecommendations } from '@/app/utils/api'
import type { Node } from '@/app/components/Graph'
import Documentation from '@/app/components/Documentation'

type EntityType = 'user' | 'repo';

export default function Home() {
  const [showDocs, setShowDocs] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')
  const [graphData, setGraphData] = useState<any>(null)
  const [selectedNode, setSelectedNode] = useState<Node | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [type, setType] = useState<EntityType>('user')
  const [findType, setFindType] = useState<EntityType>('repo')

  const handleTypeChange = (value: EntityType) => {
    setType(value)
    if (value === 'user') {
      setFindType('repo')
    } else {
      setFindType('user')
    }
  }

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
      
      setGraphData({
        ...result,
        timestamp: Date.now()
      })
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
        <div className="bg-white rounded-2xl shadow-lg p-6  mx-auto">
          {!showDocs ? (
            <>
              <div className="flex justify-between items-center mb-8">
                <h1 className="text-2xl font-bold text-center ml-[40vw]">OpenChain</h1>
                <Button
                  onClick={() => setShowDocs(true)}
                  variant="outline"
                  className="text-[#4285F4] border-[#4285F4] hover:bg-[#4285F4] hover:text-white"
                >
                  查看文档
                </Button>
              </div>
              
              <div className="flex flex-wrap items-center gap-4 max-w-4xl mx-auto">
                <span className="font-bold text-gray-700">GitHub</span>
                
                <div className="flex gap-3">
                  <Select value={type} onValueChange={handleTypeChange}>
                    <SelectTrigger className="w-[100px]">
                      <SelectValue placeholder="选择类型" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="user">用户</SelectItem>
                      <SelectItem value="repo">仓库</SelectItem>
                    </SelectContent>
                  </Select>

                  <Select value={findType} onValueChange={value => setFindType(value as EntityType)}>
                    <SelectTrigger className="w-[100px]">
                      <SelectValue placeholder="推荐类型" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="user">推荐用户</SelectItem>
                      <SelectItem value="repo">推荐仓库</SelectItem>
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
            </>
          ) : (
            <>
              <div className="flex justify-between items-center mb-8 max-w-4xl mx-auto">
                <h1 className="text-2xl font-bold ml-[20vw]">OpenChain 文档</h1>
                <Button
                  onClick={() => setShowDocs(false)}
                  variant="outline"
                  className="text-[#4285F4] border-[#4285F4] hover:bg-[#4285F4] hover:text-white"
                >
                  返回主页
                </Button>
              </div>
              <Documentation />
            </>
          )}
        </div>
      </div>
    </main>
  )
}
