import { NextRequest, NextResponse } from "next/server";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();

    const query = body.query?.trim();

    if (!query) {
      return NextResponse.json(
        { error: "Query is required" },
        { status: 400 }
      );
    }

    const backendUrl = process.env.RAG_BACKEND_URL;

    if (!backendUrl) {
      throw new Error(
        "RAG_BACKEND_URL is not configured"
      );
    }

    const response = await fetch(
      `${backendUrl}/retrieve`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          query,
        }),
        cache: "no-store",
      }
    );

    if (!response.ok) {
      const errorText = await response.text();

      throw new Error(
        `RAG backend error ${response.status}: ${errorText}`
      );
    }

    const data = await response.json();

    return NextResponse.json(data);

  } catch (error) {
    console.error(
      "Retrieval API error:",
      error
    );

    return NextResponse.json(
      {
        error: "Retrieval failed",
      },
      {
        status: 500,
      }
    );
  }
}