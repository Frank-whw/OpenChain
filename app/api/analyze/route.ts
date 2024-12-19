import { NextResponse } from 'next/server'
import dns from 'dns'

export const dynamic = 'force-dynamic'
export const runtime = 'nodejs'
export const revalidate = 0

// 强制使用 IPv4
dns.setDefaultResultOrder('ipv4first');

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url)
    const node_a = searchParams.get('node_a')
    const node_b = searchParams.get('node_b')

    console.log('Analyze API Route hit:', { node_a, node_b });

    if (!node_a || !node_b) {
      console.error('Missing parameters:', { node_a, node_b });
      return NextResponse.json(
        { status: 'error', message: '缺少必要参数' },
        { status: 400 }
      )
    }

    const baseUrl = 'http://127.0.0.1:8000/api'
    const url = `${baseUrl}/analyze?node_a=${encodeURIComponent(node_a)}&node_b=${encodeURIComponent(node_b)}`
    
    console.log('Calling backend API:', url)

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 30000); // 30 秒超时

    try {
      const response = await fetch(url, {
        method: 'GET',
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json',
        },
        signal: controller.signal,
        cache: 'no-store'
      }).finally(() => {
        clearTimeout(timeoutId);
      });

      const data = await response.json()
      console.log('Backend response:', data)

      if (!response.ok) {
        console.error('Backend error:', response.status, data)
        return NextResponse.json(
          { 
            status: 'error', 
            message: data.detail || '后端服务错误' 
          },
          { status: response.status }
        )
      }

      return NextResponse.json({
        status: 'success',
        analysis: data.analysis
      })
    } catch (fetchError: unknown) {
      console.error('Fetch error:', fetchError)
      const errorMessage = fetchError instanceof Error ? fetchError.message : '未知错误'
      throw new Error(`请求失败: ${errorMessage}`)
    }
  } catch (error) {
    console.error('API Error:', error)
    return NextResponse.json(
      { 
        status: 'error', 
        message: error instanceof Error 
          ? `服务器错误: ${error.message}` 
          : '服务器错误'
      },
      { status: 500 }
    )
  }
} 