import { NextRequest, NextResponse } from 'next/server';

// Get backend URL from environment or fallback to localhost dev port
const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';

async function handleProxy(
  req: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const resolvedParams = await params;
  const pathParts = resolvedParams.path;
  const pathStr = pathParts.join('/');
  
  const searchParams = req.nextUrl.search;
  const destinationUrl = `${BACKEND_URL}/${pathStr}${searchParams}`;
  
  const method = req.method;
  
  // Exclude bodies for GET and HEAD requests
  let body: any = null;
  if (!['GET', 'HEAD'].includes(method)) {
    body = req.body; // Pass the stream body directly to preserve performance/streaming uploads
  }

  // Copy and clean request headers
  const headers = new Headers();
  req.headers.forEach((value, key) => {
    const lowerKey = key.toLowerCase();
    // Skip headers that may conflict with destination server proxying
    if (['host', 'origin', 'content-length', 'connection'].includes(lowerKey)) {
      return;
    }
    headers.set(key, value);
  });

  try {
    const response = await fetch(destinationUrl, {
      method,
      headers,
      body,
      // @ts-ignore
      duplex: 'half', // Required for passing req.body stream
      cache: 'no-store'
    });

    // Copy backend headers to client response
    const resHeaders = new Headers();
    response.headers.forEach((value, key) => {
      resHeaders.set(key, value);
    });

    // Handle bodyless responses (e.g. 204 No Content, 304 Not Modified)
    if (response.status === 204 || response.status === 304) {
      return new NextResponse(null, {
        status: response.status,
        statusText: response.statusText,
        headers: resHeaders
      });
    }

    // If it's a streaming SSE chat response, stream it back directly
    const contentType = response.headers.get('content-type') || '';
    if (contentType.includes('text/event-stream') && response.body) {
      return new NextResponse(response.body, {
        status: response.status,
        headers: resHeaders
      });
    }

    // Otherwise return standard response body
    const responseData = await response.arrayBuffer();
    return new NextResponse(responseData, {
      status: response.status,
      statusText: response.statusText,
      headers: resHeaders
    });

  } catch (err: any) {
    console.error('Next.js API Proxy Error:', err);
    return NextResponse.json(
      { detail: `Proxy Connection Error: ${err.message}`, code: 'PROXY_ERROR' },
      { status: 502 }
    );
  }
}

export const GET = handleProxy;
export const POST = handleProxy;
export const PUT = handleProxy;
export const PATCH = handleProxy;
export const DELETE = handleProxy;
