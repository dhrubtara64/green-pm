import { NextRequest, NextResponse } from "next/server";

const BACKEND = process.env.BACKEND_URL || "http://localhost:8000";

type Ctx = { params: { path: string[] } };

async function proxy(req: NextRequest, { params }: Ctx, method: string) {
  const path = params.path.join("/");
  const search = req.nextUrl.search;
  const url = `${BACKEND}/${path}${search}`;

  const headers: Record<string, string> = {};
  const ct = req.headers.get("content-type");
  if (ct) headers["content-type"] = ct;

  const body = method !== "GET" && method !== "HEAD" ? await req.text() : undefined;

  try {
    const res = await fetch(url, { method, headers, body });
    const text = await res.text();
    let data: unknown;
    try { data = JSON.parse(text); } catch { data = text; }
    return NextResponse.json(data, { status: res.status });
  } catch (err) {
    return NextResponse.json({ error: String(err) }, { status: 502 });
  }
}

export async function GET(req: NextRequest, ctx: Ctx) { return proxy(req, ctx, "GET"); }
export async function POST(req: NextRequest, ctx: Ctx) { return proxy(req, ctx, "POST"); }
export async function PATCH(req: NextRequest, ctx: Ctx) { return proxy(req, ctx, "PATCH"); }
export async function PUT(req: NextRequest, ctx: Ctx) { return proxy(req, ctx, "PUT"); }
export async function DELETE(req: NextRequest, ctx: Ctx) { return proxy(req, ctx, "DELETE"); }
