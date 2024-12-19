import { NextResponse } from 'next/server'
<<<<<<< HEAD
import dns from 'dns'
=======
>>>>>>> 0fe51c7f31a84d94902f9f7a94cdd1f5a86f39ce

export const dynamic = 'force-dynamic'
export const runtime = 'nodejs'
export const revalidate = 0

<<<<<<< HEAD
// 强制使用 IPv4
dns.setDefaultResultOrder('ipv4first');

=======
>>>>>>> 0fe51c7f31a84d94902f9f7a94cdd1f5a86f39ce
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

<<<<<<< HEAD
    const baseUrl = 'http://127.0.0.1:8000/api'
=======
    const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api'
>>>>>>> 0fe51c7f31a84d94902f9f7a94cdd1f5a86f39ce
    const url = `${baseUrl}/analyze?node_a=${encodeURIComponent(node_a)}&node_b=${encodeURIComponent(node_b)}`
    
    console.log('Calling backend API:', url)

<<<<<<< HEAD
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
=======
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
      },
      cache: 'no-store'
    })

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
>>>>>>> 0fe51c7f31a84d94902f9f7a94cdd1f5a86f39ce
  } catch (error) {
    console.error('API Error:', error)
    return NextResponse.json(
      { 
        status: 'error', 
<<<<<<< HEAD
        message: error instanceof Error 
          ? `服务器错误: ${error.message}` 
          : '服务器错误'
=======
        message: error instanceof Error ? error.message : '服务器错误' 
>>>>>>> 0fe51c7f31a84d94902f9f7a94cdd1f5a86f39ce
      },
      { status: 500 }
    )
  }
} 