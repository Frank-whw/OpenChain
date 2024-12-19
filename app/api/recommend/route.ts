import { NextResponse } from 'next/server'

export const dynamic = 'force-dynamic'
export const runtime = 'nodejs'

export async function GET(request: Request) {
  console.log('Recommend API Route hit:', request.url);
  const { searchParams } = new URL(request.url)
  const type = searchParams.get('type')
  const name = searchParams.get('name')
  const find = searchParams.get('find')
  const count = searchParams.get('count')

  // 参数验证
  if (!type || !name || !find) {
    return NextResponse.json(
      { message: '缺少必要参数' },
      { status: 400 }
    )
  }

  // 验证参数值
  if (!['user', 'repo'].includes(type)) {
    return NextResponse.json(
      { message: 'type 参数必须是 user 或 repo' },
      { status: 400 }
    )
  }

  if (!['user', 'repo'].includes(find)) {
    return NextResponse.json(
      { message: 'find 参数必须是 user 或 repo' },
      { status: 400 }
    )
  }

  if (type === 'repo' && !name.includes('/')) {
    return NextResponse.json(
      { message: '仓库名称格式错误，应为: owner/repo' },
      { status: 400 }
    )
  }

  try {
    const baseUrl = 'http://127.0.0.1:8000/api'
    const countParam = count ? `&count=${encodeURIComponent(count)}` : ''
    const url = `${baseUrl}/recommend?type=${encodeURIComponent(type)}&name=${encodeURIComponent(name)}&find=${encodeURIComponent(find)}${countParam}`

    console.log('Calling backend API:', url);

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 30000); // 30 秒超时

    const response = await fetch(url, {
      headers: {
        'Accept': 'application/json',
      },
      signal: controller.signal,
      // 显式禁用 IPv6
      agent: function(_parsedURL: URL) {
        return null;  // 使用默认的 agent，但会优先使用 IPv4
      }
    }).finally(() => {
      clearTimeout(timeoutId);
    });
    
    if (!response.ok) {
      const errorText = await response.text()
      console.error('Backend error:', response.status, errorText)
      try {
        const errorJson = JSON.parse(errorText)
        return NextResponse.json(
          { message: errorJson.detail || '后端服务错误' },
          { status: response.status }
        )
      } catch {
        return NextResponse.json(
          { message: '后端服务错误' },
          { status: response.status }
        )
      }
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error('API Error:', error)
    // 更详细的错误信息
    const errorMessage = error instanceof Error 
      ? `服务器错误: ${error.message}`
      : '服务器错误'
    
    return NextResponse.json(
      { message: errorMessage },
      { status: 500 }
    )
  }
} 