import { NextRequest, NextResponse } from "next/server";

export async function POST(req: NextRequest) {
  try {
    const { query, model, apiKey } = await req.json();

    if (!query) {
      return NextResponse.json(
        { error: "Query parameter is required" },
        { status: 400 }
      );
    }

    const groqKey =
      apiKey ||
      process.env.GROQ_API_KEY;

    const payload = {
      model: model || process.env.DEFAULT_TRANSLATION_MODEL || "openai/gpt-oss-20b",
      messages: [
        {
          role: "system",
          content:
            "You are a professional clinical translator. Translate the given Arabic clinical question into clear, precise medical English optimized for vector embedding semantic search across NICE and WHO guidelines. Output ONLY the translated English query with no extra commentary.",
        },
        {
          role: "user",
          content: query,
        },
      ],
      temperature: 0.1,
      max_tokens: 150,
    };

    const res = await fetch("https://api.groq.com/openai/v1/chat/completions", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${groqKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const errText = await res.text();
      return NextResponse.json(
        { error: `Translation error (${res.status}): ${errText}` },
        { status: res.status }
      );
    }

    const data = await res.json();
    const translatedQuery =
      data.choices?.[0]?.message?.content?.trim() || query;

    return NextResponse.json({
      originalQuery: query,
      translatedQuery,
      model: data.model,
    });
  } catch (error: any) {
    console.error("API /translate error:", error);
    return NextResponse.json(
      { error: error.message || "Internal server error" },
      { status: 500 }
    );
  }
}
