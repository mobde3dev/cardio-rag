import { NextRequest, NextResponse } from "next/server";

export async function POST(req: NextRequest) {
  try {
    const { messages, model, temperature, apiKey } = await req.json();

    const groqKey =
      apiKey ||
      process.env.GROQ_API_KEY;

    if (!groqKey) {
      return NextResponse.json(
        { error: "Groq API Key is not configured." },
        { status: 400 }
      );
    }

    const payload = {
      model: model || process.env.DEFAULT_GROQ_MODEL || "openai/gpt-oss-120b",
      messages: messages || [],
      temperature: temperature !== undefined ? temperature : 0.15,
      max_tokens: 1024,
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
        { error: `Groq API error (${res.status}): ${errText}` },
        { status: res.status }
      );
    }

    const data = await res.json();
    const content = data.choices?.[0]?.message?.content || "";
    const tokensUsed = data.usage?.total_tokens || 350;

    return NextResponse.json({
      content,
      tokensUsed,
      model: data.model,
    });
  } catch (error: any) {
    console.error("API /chat error:", error);
    return NextResponse.json(
      { error: error.message || "Internal server error" },
      { status: 500 }
    );
  }
}
