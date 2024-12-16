import { NextResponse } from 'next/server'

export const dynamic = 'force-dynamic'
export const runtime = 'nodejs'
export const revalidate = 0

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

    const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api'
    const url = `${baseUrl}/analyze?node_a=${encodeURIComponent(node_a)}&node_b=${encodeURIComponent(node_b)}`
    
    console.log('Calling backend API:', url)

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
  } catch (error) {
    console.error('API Error:', error)
    return NextResponse.json(
      { 
        status: 'error', 
        message: error instanceof Error ? error.message : '服务器错误' 
      },
      { status: 500 }
    )
  }
} 