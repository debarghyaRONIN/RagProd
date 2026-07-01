import { NextResponse } from 'next/server';

export async function POST() {
  const response = NextResponse.json({ success: true });
  
  // Clear the access_token cookie by setting maxAge to 0
  response.cookies.set('access_token', '', {
    path: '/',
    maxAge: 0,
    expires: new Date(0),
    httpOnly: true,
    sameSite: 'strict',
    secure: true,
  });
  
  return response;
}
