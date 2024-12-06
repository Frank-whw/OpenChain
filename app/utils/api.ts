export async function fetchGraphData(platform: string, what: string, name: string) {
  // 这里应该是实际的API调用
  // 为了演示，我们返回一些模拟数据
  return {
    center: { id: name, openrank: 100 },
    nodes: [
      { id: name, openrank: 100 },
      { id: "repo1", openrank: 50 },
      { id: "repo2", openrank: 30 },
      { id: "repo3", openrank: 70 },
      // ... 更多节点
    ],
    links: [
      { source: name, target: "repo1" },
      { source: name, target: "repo2" },
      { source: name, target: "repo3" },
      // ... 更多链接
    ]
  }
}

export async function fetchRelationshipAnalysis(centerId: string, nodeId: string) {
  // 这里应该是实际的API调用，可能包括调用OpenAI的接口
  // 为了演示，我们返回一些模拟数据
  return `这是 ${centerId} 和 ${nodeId} 之间关系的分析...`
}

