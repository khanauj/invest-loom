import { NextRequest, NextResponse } from "next/server";

// ── Technical indicator helpers ─────────────────────────────────────────────

function ema(prices: number[], period: number): number[] {
  const k = 2 / (period + 1);
  const out: number[] = new Array(prices.length).fill(NaN);
  let seed = prices.slice(0, period).reduce((a, b) => a + b, 0) / period;
  out[period - 1] = seed;
  for (let i = period; i < prices.length; i++) {
    seed = prices[i] * k + seed * (1 - k);
    out[i] = seed;
  }
  return out;
}

function rsi14(closes: number[]): number {
  if (closes.length < 15) return 50;
  const changes = closes.slice(1).map((c, i) => c - closes[i]);
  const last14 = changes.slice(-14);
  const avgGain = last14.reduce((s, c) => s + Math.max(0, c), 0) / 14;
  const avgLoss = last14.reduce((s, c) => s + Math.abs(Math.min(0, c)), 0) / 14;
  if (avgLoss === 0) return 100;
  return Math.round(100 - 100 / (1 + avgGain / avgLoss));
}

function sma(prices: number[], period: number): number {
  const slice = prices.slice(-period);
  return slice.reduce((a, b) => a + b, 0) / slice.length;
}

// ── Main route ──────────────────────────────────────────────────────────────

export async function POST(req: NextRequest) {
  const body = await req.json().catch(() => ({}));
  const tickers: string[] = Array.isArray(body.tickers) ? body.tickers : [];

  if (tickers.length === 0) {
    return NextResponse.json({ stocks: [] });
  }

  const stocks = await Promise.all(tickers.map(fetchTicker));
  return NextResponse.json({ stocks });
}

async function fetchTicker(ticker: string) {
  const t = ticker.trim().toUpperCase();

  try {
    // ── 1. Price history (6 months daily) ──────────────────────────────────
    const chartUrl =
      `https://query1.finance.yahoo.com/v8/finance/chart/${t}` +
      `?interval=1d&range=6mo`;

    const chartRes = await fetch(chartUrl, {
      headers: { "User-Agent": "Mozilla/5.0" },
      next: { revalidate: 300 }, // cache 5 min
    });

    if (!chartRes.ok) throw new Error(`Chart HTTP ${chartRes.status}`);

    const chartJson = await chartRes.json();
    const yResult = chartJson?.chart?.result?.[0];
    if (!yResult) throw new Error("No chart result");

    const rawCloses: (number | null)[] = yResult.indicators.quote[0].close ?? [];
    const closes = rawCloses.filter((c): c is number => c != null);
    if (closes.length < 5) throw new Error("Too few data points");

    const meta = yResult.meta;
    const currentPrice: number = meta.regularMarketPrice ?? closes[closes.length - 1];
    const prevClose: number = meta.previousClose ?? meta.chartPreviousClose ?? closes[closes.length - 2];
    const changePct = prevClose ? ((currentPrice - prevClose) / prevClose) * 100 : 0;

    // ── 2. Technical signals ────────────────────────────────────────────────
    const rsiVal = rsi14(closes);
    const ma50 = sma(closes, Math.min(50, closes.length));
    const ma200 = sma(closes, Math.min(200, closes.length));
    const ema12 = ema(closes, Math.min(12, closes.length));
    const ema26 = ema(closes, Math.min(26, closes.length));
    const macdArr = ema12.map((v, i) => (isNaN(v) || isNaN(ema26[i]) ? NaN : v - ema26[i]));
    const validMacd = macdArr.filter((v) => !isNaN(v));
    const macdNow = validMacd[validMacd.length - 1] ?? 0;
    const macdPrev = validMacd[validMacd.length - 2] ?? 0;

    let technicalScore = 50;
    const indicators: string[] = [];

    // RSI
    if (rsiVal < 30) {
      technicalScore += 15;
      indicators.push(`RSI: ${rsiVal} (oversold — buy signal)`);
    } else if (rsiVal < 45) {
      technicalScore += 5;
      indicators.push(`RSI: ${rsiVal} (weak)`);
    } else if (rsiVal <= 65) {
      indicators.push(`RSI: ${rsiVal} (neutral)`);
    } else if (rsiVal <= 80) {
      technicalScore -= 5;
      indicators.push(`RSI: ${rsiVal} (strong)`);
    } else {
      technicalScore -= 15;
      indicators.push(`RSI: ${rsiVal} (overbought — caution)`);
    }

    // MA crossover
    if (currentPrice > ma50 && ma50 > ma200) {
      technicalScore += 15;
      indicators.push("Above 50 & 200 MA (bullish trend)");
    } else if (currentPrice > ma50) {
      technicalScore += 8;
      indicators.push("Above 50 MA");
    } else if (currentPrice < ma200) {
      technicalScore -= 12;
      indicators.push("Below 200 MA (bearish)");
    } else {
      indicators.push("Between 50 & 200 MA");
    }

    // MACD
    if (macdNow > 0 && macdNow > macdPrev) {
      technicalScore += 8;
      indicators.push("MACD: bullish crossover");
    } else if (macdNow > 0) {
      technicalScore += 4;
      indicators.push("MACD: bullish");
    } else if (macdNow < 0 && macdNow < macdPrev) {
      technicalScore -= 8;
      indicators.push("MACD: bearish crossover");
    } else {
      technicalScore -= 2;
      indicators.push("MACD: flat / bearish");
    }

    technicalScore = Math.max(0, Math.min(100, technicalScore));

    // ── 3. Fundamentals (best-effort) ──────────────────────────────────────
    let fundamentalScore = 50;
    let valuationScore = 50;

    try {
      const fundUrl =
        `https://query1.finance.yahoo.com/v10/finance/quoteSummary/${t}` +
        `?modules=defaultKeyStatistics,financialData`;

      const fundRes = await fetch(fundUrl, {
        headers: { "User-Agent": "Mozilla/5.0" },
        next: { revalidate: 3600 },
      });

      if (fundRes.ok) {
        const fundJson = await fundRes.json();
        const stats = fundJson?.quoteSummary?.result?.[0]?.defaultKeyStatistics;
        const fin = fundJson?.quoteSummary?.result?.[0]?.financialData;

        const roe: number | undefined = fin?.returnOnEquity?.raw;
        const revenueGrowth: number | undefined = fin?.revenueGrowth?.raw;
        const pe: number | undefined = stats?.forwardPE?.raw;

        if (typeof roe === "number") {
          fundamentalScore = Math.min(100, Math.max(0, 50 + roe * 200));
        }
        if (typeof revenueGrowth === "number") {
          fundamentalScore = Math.min(100, fundamentalScore + revenueGrowth * 80);
        }
        if (typeof pe === "number") {
          valuationScore = pe < 15 ? 85 : pe < 25 ? 70 : pe < 40 ? 50 : 30;
        }
      }
    } catch {
      // fundamentals are best-effort; fall back to defaults
    }

    const sentimentScore = Math.min(100, Math.max(0, 50 + changePct * 5));

    const totalScore =
      fundamentalScore * 0.3 +
      technicalScore * 0.4 +
      valuationScore * 0.2 +
      sentimentScore * 0.1;

    let grade: string;
    let recommendation: string;
    let signal: string;
    let signalStrength: string;

    if (totalScore >= 75) {
      grade = "A"; recommendation = "STRONG BUY"; signal = "BUY"; signalStrength = "STRONG";
    } else if (totalScore >= 60) {
      grade = "B"; recommendation = "BUY"; signal = "BUY"; signalStrength = "MODERATE";
    } else if (totalScore >= 45) {
      grade = "C"; recommendation = "HOLD"; signal = "HOLD"; signalStrength = "NEUTRAL";
    } else if (totalScore >= 30) {
      grade = "D"; recommendation = "SELL"; signal = "SELL"; signalStrength = "MODERATE";
    } else {
      grade = "F"; recommendation = "STRONG SELL"; signal = "SELL"; signalStrength = "STRONG";
    }

    return {
      ticker: t,
      price: Math.round(currentPrice * 100) / 100,
      changePct: Math.round(changePct * 100) / 100,
      signal,
      signalStrength,
      signalScore: Math.round(((technicalScore - 50) / 50) * 1000) / 1000,
      totalScore: Math.round(totalScore * 10) / 10,
      grade,
      recommendation,
      fundamental: Math.round(fundamentalScore),
      technical: Math.round(technicalScore),
      valuation: Math.round(valuationScore),
      sentiment: Math.round(sentimentScore),
      indicators,
    };
  } catch (err) {
    const msg = err instanceof Error ? err.message : "Unknown error";
    return {
      ticker: t,
      error: `Could not fetch data: ${msg}`,
      price: 0,
      changePct: 0,
      signal: "N/A",
      signalStrength: "N/A",
      signalScore: 0,
      totalScore: 0,
      grade: "N/A",
      recommendation: "N/A",
      fundamental: 0,
      technical: 0,
      valuation: 0,
      sentiment: 0,
      indicators: ["Live data unavailable for this ticker"],
    };
  }
}
