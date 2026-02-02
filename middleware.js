import { NextResponse } from 'next/server';

export function middleware(req) {
  const basicAuth = req.headers.get('authorization');
  const url = req.nextUrl;

  // Define your credentials here
  const validUsername = 'admin';
  const validPassword = 'SecurePass123!'; // Change this to your desired password

  if (basicAuth) {
    const authValue = basicAuth.split(' ')[1];
    const [user, pwd] = atob(authValue).split(':');

    if (user === validUsername && pwd === validPassword) {
      return NextResponse.next();
    }
  }

  // Send authentication challenge
  return new NextResponse('Authentication required', {
    status: 401,
    headers: {
      'WWW-Authenticate': 'Basic realm="Secure Area"',
    },
  });
}

// Apply to all routes except API routes if needed
export const config = {
  matcher: [
    '/((?!api/public).*)', // Protects everything except /api/public/*
  ],
};
