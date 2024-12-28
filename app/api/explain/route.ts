import { NextResponse } from 'next/server'
import dns from 'dns'

export const dynamic = 'force-dynamic'
export const runtime = 'nodejs'
export const revalidate = 0

dns.setDefaultResultOrder('ipv4first');

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url)
    const type = searchParams.get('type')
    const mode = searchParams.get('mode') // 用于区分不同的推荐模式

    if (!type) {
      return NextResponse.json(
        { status: 'error', message: '缺少必要参数' },
        { status: 400 }
      )
    }

    const baseUrl = 'http://127.0.0.1:8000/api'
    const url = `${baseUrl}/explain?type=${encodeURIComponent(type)}&mode=${encodeURIComponent(mode || '')}`
    
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 30000);

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

      if (!response.ok) {
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
        explanation: data.explanation
      })
    } catch (fetchError: unknown) {
      const errorMessage = fetchError instanceof Error ? fetchError.message : '未知错误'
      throw new Error(`请求失败: ${errorMessage}`)
    }
  } catch (error) {
    return NextResponse.json(
      { 
        status: 'error', 
        message: error instanceof Error ? `服务器错误: ${error.message}` : '服务器错误'
      },
      { status: 500 }
    )
  }
} 