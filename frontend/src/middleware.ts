import { NextResponse, type NextRequest } from "next/server";

// Redirection d'ergonomie seulement : la vraie vérification de session est faite par l'API.
export function middleware(request: NextRequest) {
  if (!request.cookies.has("boh_session")) {
    return NextResponse.redirect(new URL("/login", request.url));
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!login|api|_next|favicon.ico).*)"],
};
