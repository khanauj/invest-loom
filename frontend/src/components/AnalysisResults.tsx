"use client";

import { useState, useEffect } from "react";
import { motion, Variants } from "framer-motion";
import {
  AreaChart, Area, PieChart, Pie, Cell, BarChart, Bar,
  XAxis, YAxis, Tooltip, ResponsiveContainer, Legend,
} from "recharts";
import {
  AlertTriangle, CheckCircle, Info, TrendingUp,
  ShieldAlert, Target, ArrowUpRight, ArrowDownRight, Zap,
  Building, Landmark, ChevronRight, Loader2,
} from "lucide-react";
import type { StockEntry } from "@/lib/financial-engine";
import type { AnalysisResult } from "@/lib/financial-engine";

const CHART_COLORS = ["#8274dd", "#2B8A3E", "#ebcb8b", "#bf616a", "#b48ead", "#40c057", "#d08770"];

const fadeIn: Variants = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0, transition: { duration: 0.5 } },
};

const stagger: Variants = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.15 } },
};

function formatINR(n: number): string {
  if (n >= 10000000) return `₹${(n / 10000000).toFixed(2)} Cr`;
  if (n >= 100000) return `₹${(n / 100000).toFixed(1)}L`;
  return `₹${n.toLocaleString("en-IN")}`;
}

function SectionTitle({ step, title, icon: Icon }: { step: number; title: string; icon: React.ElementType }) {
  return (
    <div className="flex items-center gap-4 mb-6">
      <div className="w-10 h-10 rounded-xl bg-brand-500/20 border border-brand-400/30 flex items-center justify-center text-brand-300 font-bold text-sm shrink-0">
        {step}
      </div>
      <div className="flex items-center gap-2">
        <Icon className="w-5 h-5 text-brand-300" />
        <h2 className="text-xl font-bold text-white">{title}</h2>
      </div>
    </div>
  );
}

// ─── Live Stock Section ──────────────────────────────────────────────────────

function StockCard({ s }: { s: StockEntry & { error?: string } }) {
  if (s.error) {
    return (
      <div className="p-4 rounded-xl bg-white/5 border border-white/5">
        <p className="font-bold text-white mb-1">{s.ticker}</p>
        <p className="text-xs text-red-400">{s.error}</p>
      </div>
    );
  }
  return (
    <div className="p-4 rounded-xl bg-white/5 border border-white/5">
      <div className="flex items-center justify-between mb-2">
        <span className="font-bold text-white">{s.ticker}</span>
        <span className={`text-xs px-2 py-1 rounded-full font-semibold ${
          s.signal === "BUY" ? "bg-emerald-500/20 text-emerald-300" :
          s.signal === "SELL" ? "bg-red-500/20 text-red-300" : "bg-brand-500/20 text-brand-300"
        }`}>{s.signal} {s.signalStrength}</span>
      </div>
      <div className="flex items-baseline gap-2 mb-3">
        <span className="text-lg text-white font-medium">₹{s.price.toFixed(2)}</span>
        <span className={`text-sm flex items-center ${s.changePct >= 0 ? "text-emerald-400" : "text-red-400"}`}>
          {s.changePct >= 0 ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
          {Math.abs(s.changePct).toFixed(2)}%
        </span>
      </div>
      <div className="flex items-center gap-2 mb-3">
        <span className="text-2xl font-bold text-white">{s.totalScore.toFixed(1)}</span>
        <span className={`text-sm font-bold px-2 py-0.5 rounded ${
          s.grade === "A" || s.grade === "B" ? "bg-emerald-500/20 text-emerald-300" :
          s.grade === "D" || s.grade === "F" ? "bg-red-500/20 text-red-300" : "bg-brand-500/20 text-brand-300"
        }`}>{s.grade}</span>
        <span className={`text-xs font-semibold ${
          s.recommendation === "STRONG BUY" || s.recommendation === "BUY" ? "text-emerald-400" :
          s.recommendation === "SELL" || s.recommendation === "STRONG SELL" ? "text-red-400" : "text-brand-300"
        }`}>{s.recommendation}</span>
      </div>
      <div className="grid grid-cols-2 gap-1.5 text-xs mb-3">
        <div><span className="text-brand-400">Fund:</span> <span className="text-white">{s.fundamental}</span></div>
        <div><span className="text-brand-400">Tech:</span> <span className="text-white">{s.technical}</span></div>
        <div><span className="text-brand-400">Val:</span> <span className="text-white">{s.valuation}</span></div>
        <div><span className="text-brand-400">Sent:</span> <span className="text-white">{s.sentiment}</span></div>
      </div>
      {s.indicators.length > 0 && (
        <ul className="space-y-0.5">
          {s.indicators.map((ind, i) => (
            <li key={i} className="text-xs text-brand-300">• {ind}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

const RECOMMENDED_TICKERS = [
  "HDFCBANK.NS", "TCS.NS", "RELIANCE.NS", "INFY.NS",
  "ICICIBANK.NS", "HCLTECH.NS", "KOTAKBANK.NS", "AXISBANK.NS",
];

function LiveStockSection({ step, tickers }: { step: number; tickers: string[] }) {
  const [stocks, setStocks] = useState<(StockEntry & { error?: string })[]>([]);
  const [loading, setLoading] = useState(false);
  const [fetchError, setFetchError] = useState<string | null>(null);

  const validTickers = tickers.map((t) => t.trim()).filter(Boolean);
  const isRecommendationMode = validTickers.length === 0;
  const fetchList = isRecommendationMode ? RECOMMENDED_TICKERS : validTickers;

  useEffect(() => {
    setLoading(true);
    setFetchError(null);
    fetch("/api/stocks", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ tickers: fetchList }),
    })
      .then((r) => r.json())
      .then((data) => {
        const all: (StockEntry & { error?: string })[] = data.stocks ?? [];
        if (isRecommendationMode) {
          all.sort((a, b) => (b.totalScore ?? 0) - (a.totalScore ?? 0));
        }
        setStocks(all);
      })
      .catch(() => setFetchError("Could not reach /api/stocks. Make sure the Next.js server is running."))
      .finally(() => setLoading(false));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tickers.join(",")]);

  return (
    <motion.section variants={fadeIn} className="glass-card p-8">
      <SectionTitle step={step} title="Stock Analysis" icon={TrendingUp} />

      {loading ? (
        <div className="flex items-center justify-center gap-3 py-10 text-brand-300">
          <Loader2 className="w-5 h-5 animate-spin" />
          <span className="text-sm">
            {isRecommendationMode
              ? "Finding the best blue chips right now…"
              : `Fetching live data for ${validTickers.join(", ")}…`}
          </span>
        </div>
      ) : fetchError ? (
        <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-300 text-sm">{fetchError}</div>
      ) : (
        <>
          {isRecommendationMode && (
            <div className="mb-5 p-3 rounded-xl bg-brand-500/10 border border-brand-400/20 text-xs text-brand-300">
              You have no stocks in your portfolio — here are the top-ranked NSE blue chips today, sorted by live score.
              Add tickers on the input form for personalised analysis.
            </div>
          )}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-4">
            {stocks.filter((s) => !s.error).map((s, i) => (
              <div key={s.ticker} className="relative">
                {isRecommendationMode && i === 0 && (
                  <span className="absolute -top-2 -right-2 z-10 text-xs bg-emerald-500 text-white px-2 py-0.5 rounded-full font-bold shadow">
                    #1 Pick
                  </span>
                )}
                {isRecommendationMode && i === 1 && (
                  <span className="absolute -top-2 -right-2 z-10 text-xs bg-brand-500 text-white px-2 py-0.5 rounded-full font-bold shadow">
                    #2 Pick
                  </span>
                )}
                <StockCard s={s} />
              </div>
            ))}
          </div>
          <p className="text-xs text-brand-500 mt-2">
            Prices & signals from Yahoo Finance · refreshed on page load · not financial advice
          </p>
        </>
      )}
    </motion.section>
  );
}

// ─── Risk Score Gauge ────────────────────────────────────────────────────────

function RiskGauge({ score, level }: { score: number; level: string }) {
  const pct = score / 100;
  const radius = 70;
  const circumference = Math.PI * radius;
  const offset = circumference * (1 - pct);
  const color = score <= 30 ? "#2B8A3E" : score <= 55 ? "#ebcb8b" : "#bf616a";

  return (
    <div className="flex flex-col items-center">
      <svg width="180" height="110" viewBox="0 0 180 110">
        <path d="M 10 100 A 70 70 0 0 1 170 100" fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth="12" strokeLinecap="round" />
        <path d="M 10 100 A 70 70 0 0 1 170 100" fill="none" stroke={color} strokeWidth="12" strokeLinecap="round"
          strokeDasharray={circumference} strokeDashoffset={offset}
          style={{ transition: "stroke-dashoffset 1.5s ease-out" }} />
        <text x="90" y="80" textAnchor="middle" fill="white" fontSize="28" fontWeight="bold">{score}</text>
        <text x="90" y="98" textAnchor="middle" fill={color} fontSize="11" fontWeight="600">{level}</text>
      </svg>
    </div>
  );
}

// ─── Main Results Component ──────────────────────────────────────────────────

export default function AnalysisResults({ result }: { result: AnalysisResult }) {
  const { riskScore, profile, recommendation, sipPlans, fundComparison, taxProfile, stockAnalysis, rebalancing, emergencyFund, summary } = result;

  return (
    <motion.div className="space-y-8" variants={stagger} initial="hidden" animate="show">

      {/* ── STEP 1: Risk Score ─────────────────────────────────────────────── */}
      <motion.section variants={fadeIn} className="glass-card p-8">
        <SectionTitle step={1} title="Risk Score" icon={ShieldAlert} />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          <RiskGauge score={riskScore.total} level={riskScore.level} />
          <div className="space-y-3">
            {riskScore.breakdown.map((b) => (
              <div key={b.category}>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-brand-200">{b.category}</span>
                  <span className="text-white font-medium">{b.score}/{b.maxScore}</span>
                </div>
                <div className="h-2 bg-white/5 rounded-full overflow-hidden">
                  <div className="h-full rounded-full transition-all duration-1000"
                    style={{ width: `${(b.score / b.maxScore) * 100}%`, backgroundColor: b.score > 12 ? "#bf616a" : b.score > 7 ? "#ebcb8b" : "#2B8A3E" }} />
                </div>
                <p className="text-xs text-brand-400 mt-0.5">{b.reason}</p>
              </div>
            ))}
          </div>
        </div>
      </motion.section>

      {/* ── STEP 2: Investor Profile ──────────────────────────────────────── */}
      <motion.section variants={fadeIn} className="glass-card p-8">
        <SectionTitle step={2} title="Investor Profile" icon={Target} />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          <div>
            <div className="text-2xl font-bold text-white mb-1">{profile.segment}</div>
            <div className="text-sm text-brand-300 mb-4">(score {profile.segmentScore}/100)</div>
            <p className="text-brand-200 mb-4 text-sm leading-relaxed">{profile.description}</p>
            <div className="flex flex-wrap gap-2 mb-4">
              {profile.traits.map((t) => (
                <span key={t} className="px-3 py-1 rounded-full bg-brand-500/20 border border-brand-400/20 text-xs text-brand-200">{t}</span>
              ))}
            </div>
            {profile.warnings.length > 0 && (
              <div className="mt-4 p-4 rounded-xl bg-amber-500/10 border border-amber-500/20">
                <p className="text-amber-300 text-xs font-semibold mb-2">⚠ Warnings</p>
                {profile.warnings.map((w, i) => (
                  <p key={i} className="text-amber-200/80 text-xs mb-1">• {w}</p>
                ))}
              </div>
            )}
          </div>
          <div className="space-y-2">
            <p className="text-xs text-brand-400 font-semibold mb-2">Match Scores</p>
            {profile.matches.map((m) => (
              <div key={m.name} className={`flex items-center gap-3 ${m.isYou ? "" : "opacity-60"}`}>
                <span className="text-xs text-brand-200 w-40 truncate">{m.name}</span>
                <div className="flex-1 h-3 bg-white/5 rounded-full overflow-hidden">
                  <div className="h-full rounded-full" style={{ width: `${m.score}%`, backgroundColor: m.isYou ? "#8274dd" : "rgba(255,255,255,0.15)" }} />
                </div>
                <span className={`text-xs font-medium w-8 text-right ${m.isYou ? "text-brand-300" : "text-brand-400"}`}>{m.score}</span>
                {m.isYou && <span className="text-xs text-brand-400">← YOU</span>}
              </div>
            ))}
          </div>
        </div>
      </motion.section>

      {/* ── STEP 3: AI Recommendation ─────────────────────────────────────── */}
      <motion.section variants={fadeIn} className="glass-card p-8 relative overflow-hidden">
        <div className="absolute top-0 right-0 w-40 h-40 bg-brand-400/10 rounded-full blur-[80px]" />
        <SectionTitle step={3} title="AI Recommendation" icon={Zap} />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 relative z-10">
          <div>
            <div className={`inline-block px-4 py-2 rounded-lg font-bold mb-4 ${
              recommendation.action === "START_SIP"
                ? "bg-brand-500/20 border border-brand-400/30 text-brand-200"
                : "bg-emerald-500/20 border border-emerald-500/30 text-emerald-300"
            }`}>
              {recommendation.action.replace(/_/g, " ")}
              <span className="opacity-70 font-normal ml-2">(confidence {recommendation.confidence}%)</span>
            </div>
            <p className="text-brand-200 text-sm leading-relaxed mb-6">{recommendation.reasoning}</p>
            {recommendation.action === "START_SIP" ? (
              <div className="flex items-center gap-4 p-4 rounded-xl bg-brand-500/10 border border-brand-400/20">
                <div className="text-center">
                  <p className="text-xs text-brand-400">Current SIP</p>
                  <p className="text-lg font-bold text-brand-300">None</p>
                </div>
                <ChevronRight className="w-5 h-5 text-brand-400" />
                <div className="text-center">
                  <p className="text-xs text-emerald-400">Recommended Start</p>
                  <p className="text-lg font-bold text-emerald-300">₹{recommendation.recommendedSIP.toLocaleString("en-IN")}/mo</p>
                </div>
              </div>
            ) : recommendation.increase > 0 ? (
              <div className="flex items-center gap-4 p-4 rounded-xl bg-white/5 border border-white/10">
                <div className="text-center">
                  <p className="text-xs text-brand-400">Current</p>
                  <p className="text-lg font-bold text-white">₹{recommendation.currentSIP.toLocaleString("en-IN")}</p>
                </div>
                <ChevronRight className="w-5 h-5 text-brand-400" />
                <div className="text-center">
                  <p className="text-xs text-emerald-400">Recommended</p>
                  <p className="text-lg font-bold text-emerald-300">₹{recommendation.recommendedSIP.toLocaleString("en-IN")}</p>
                </div>
                <div className="text-center ml-auto">
                  <p className="text-xs text-brand-400">Increase</p>
                  <p className="text-lg font-bold text-amber-300">+₹{recommendation.increase.toLocaleString("en-IN")}</p>
                </div>
              </div>
            ) : null}
          </div>
          <div className="p-5 rounded-xl bg-red-500/5 border border-red-500/15">
            <p className="text-xs text-red-300 font-semibold mb-3">
              💰 {recommendation.action === "START_SIP" ? "Cost of Not Starting" : "Opportunity Cost"} ({recommendation.opportunityCost.years}yr)
            </p>
            <div className="space-y-3">
              <div className="flex justify-between text-sm">
                <span className="text-brand-300">{recommendation.action === "START_SIP" ? "Without SIP" : "Current SIP Growth"}</span>
                <span className="text-white font-medium">{formatINR(recommendation.opportunityCost.currentGrowth)}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-brand-300">{recommendation.action === "START_SIP" ? "Starting SIP Now" : "With Increased SIP"}</span>
                <span className="text-emerald-300 font-medium">{formatINR(recommendation.opportunityCost.increasedGrowth)}</span>
              </div>
              <hr className="border-white/5" />
              <div className="flex justify-between text-sm">
                <span className="text-red-300 font-semibold">{recommendation.action === "START_SIP" ? "You're Missing Out On" : "You Leave on the Table"}</span>
                <span className="text-red-300 font-bold">{formatINR(recommendation.opportunityCost.leftOnTable)}</span>
              </div>
            </div>
          </div>
        </div>
      </motion.section>

      {/* ── STEP 4+5: SIP Plans per Goal ──────────────────────────────────── */}
      {sipPlans.map((plan, pi) => (
        <motion.section key={pi} variants={fadeIn} className="glass-card p-8">
          <SectionTitle step={4 + pi} title={`SIP Plan: ${plan.goalLabel}`} icon={pi === 0 ? Building : Landmark} />
          <div className="mb-4 flex flex-wrap gap-4 text-sm text-brand-300">
            <span>SIP: ₹{plan.monthlySIP.toLocaleString("en-IN")}/mo</span>
            <span>CAGR: {plan.blendedCAGR}%</span>
            <span>Horizon: {plan.years} years</span>
            <span>Target: {formatINR(plan.targetAmount)}</span>
          </div>

          {/* Fund Allocation */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
            <div className="lg:col-span-2">
              <p className="text-xs text-brand-400 font-semibold mb-3">Fund Allocation</p>
              <div className="space-y-2">
                {plan.allocations.map((a, i) => (
                  <div key={i} className="flex items-center gap-3 p-3 rounded-lg bg-white/5 border border-white/5">
                    <div className="w-3 h-3 rounded-full shrink-0" style={{ backgroundColor: CHART_COLORS[i % CHART_COLORS.length] }} />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-white truncate">{a.fundName}</p>
                      <p className="text-xs text-brand-400">{a.purpose}</p>
                    </div>
                    <div className="text-right shrink-0">
                      <p className="text-sm text-white font-medium">₹{a.amount.toLocaleString("en-IN")}/mo</p>
                      <p className="text-xs text-brand-400">{a.percentage}% · {a.returns5yr}% pa</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
            <div>
              <p className="text-xs text-brand-400 font-semibold mb-3">Allocation Split</p>
              <ResponsiveContainer width="100%" height={200}>
                <PieChart>
                  <Pie data={plan.allocations.map((a) => ({ name: a.fundName.split(" ")[0], value: a.percentage }))}
                    cx="50%" cy="50%" innerRadius={50} outerRadius={80} paddingAngle={3} dataKey="value"
                    stroke="none">
                    {plan.allocations.map((_, i) => <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />)}
                  </Pie>
                  <Tooltip contentStyle={{ backgroundColor: "rgba(26,26,46,0.95)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "8px", fontSize: "12px", color: "#fff" }} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Corpus Projection */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
            <div className="p-4 rounded-xl bg-white/5 border border-white/5">
              <p className="text-xs text-brand-400 font-semibold mb-2">Flat SIP Projection</p>
              <p className="text-2xl font-bold text-white">{formatINR(plan.flatProjection.finalCorpus)}</p>
              <p className="text-xs text-brand-300 mt-1">Invested {formatINR(plan.flatProjection.totalInvested)} · Gain {formatINR(plan.flatProjection.wealthGain)}</p>
            </div>
            <div className="p-4 rounded-xl bg-emerald-500/5 border border-emerald-500/15">
              <p className="text-xs text-emerald-400 font-semibold mb-2">Step-up 10%/yr Projection</p>
              <p className="text-2xl font-bold text-emerald-300">{formatINR(plan.stepupProjection.finalCorpus)}</p>
              <p className="text-xs text-brand-300 mt-1">Invested {formatINR(plan.stepupProjection.totalInvested)} · Gain {formatINR(plan.stepupProjection.wealthGain)}</p>
            </div>
          </div>

          {/* Goal Analysis */}
          <div className={`p-4 rounded-xl border ${plan.goalAnalysis.flatReaches ? "bg-emerald-500/5 border-emerald-500/15" : "bg-amber-500/5 border-amber-500/15"}`}>
            <p className={`text-xs font-semibold mb-2 ${plan.goalAnalysis.flatReaches ? "text-emerald-400" : "text-amber-400"}`}>
              {plan.goalAnalysis.flatReaches ? "✅ Goal Analysis" : "⚠️ Goal Analysis"}
            </p>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div>
                <p className="text-brand-400 text-xs">Target</p>
                <p className="text-white font-medium">{formatINR(plan.goalAnalysis.targetAmount)}</p>
              </div>
              <div>
                <p className="text-brand-400 text-xs">Status</p>
                <p className={`font-medium ${plan.goalAnalysis.flatReaches ? "text-emerald-300" : "text-amber-300"}`}>
                  {plan.goalAnalysis.flatReaches ? "REACHED" : `Short by ${formatINR(plan.goalAnalysis.flatShortfall)}`}
                </p>
              </div>
              <div>
                <p className="text-brand-400 text-xs">SIP Needed</p>
                <p className="text-white font-medium">₹{plan.goalAnalysis.sipNeeded.toLocaleString("en-IN")}/mo</p>
              </div>
              <div>
                <p className="text-brand-400 text-xs">At Current SIP</p>
                <p className="text-white font-medium">{plan.goalAnalysis.yearsAtCurrentSIP}yr {plan.goalAnalysis.extraMonths}mo</p>
              </div>
            </div>
            <p className="text-xs text-brand-200 mt-3">Verdict: {plan.goalAnalysis.verdict}</p>
          </div>
        </motion.section>
      ))}

      {/* ── STEP 6: Fund Comparison ───────────────────────────────────────── */}
      <motion.section variants={fadeIn} className="glass-card p-8">
        <SectionTitle step={4 + sipPlans.length} title="Fund Comparison" icon={TrendingUp} />
        <p className="text-sm text-brand-300 mb-4">₹{fundComparison.monthlySIP.toLocaleString("en-IN")}/mo for {fundComparison.years}yr · Target {formatINR(fundComparison.goalAmount)}</p>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-brand-400 text-xs border-b border-white/5">
                <th className="text-left py-3 px-2">Rank</th>
                <th className="text-left py-3 px-2">Fund</th>
                <th className="text-right py-3 px-2">5yr%</th>
                <th className="text-right py-3 px-2">ER%</th>
                <th className="text-right py-3 px-2">Net Corpus</th>
                <th className="text-right py-3 px-2">Mult</th>
                <th className="text-center py-3 px-2">Goal</th>
              </tr>
            </thead>
            <tbody>
              {fundComparison.results.map((f) => (
                <tr key={f.rank} className="border-b border-white/5 hover:bg-white/5 transition-colors">
                  <td className="py-3 px-2 font-bold text-brand-300">#{f.rank}</td>
                  <td className="py-3 px-2 text-white">{f.fundName}</td>
                  <td className="py-3 px-2 text-right text-brand-200">{f.returns5yr}%</td>
                  <td className="py-3 px-2 text-right text-brand-400">{f.expenseRatio}%</td>
                  <td className="py-3 px-2 text-right text-white font-medium">{formatINR(f.netCorpus)}</td>
                  <td className="py-3 px-2 text-right text-emerald-300 font-bold">{f.multiplier}x</td>
                  <td className="py-3 px-2 text-center">
                    {f.hitsGoal
                      ? <span className="px-2 py-1 rounded-full bg-emerald-500/20 text-emerald-300 text-xs">YES</span>
                      : <span className="px-2 py-1 rounded-full bg-red-500/20 text-red-300 text-xs">Gap {formatINR(f.goalGap)}</span>
                    }
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {fundComparison.winnerNotes.length > 0 && (
          <div className="mt-4 space-y-1">
            {fundComparison.winnerNotes.map((n, i) => (
              <p key={i} className="text-xs text-brand-300">💡 {n}</p>
            ))}
          </div>
        )}
      </motion.section>

      {/* ── STEP 7: Tax Profile ───────────────────────────────────────────── */}
      <motion.section variants={fadeIn} className="glass-card p-8">
        <SectionTitle step={5 + sipPlans.length} title="Tax Profile" icon={Landmark} />
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { label: "Annual Salary", value: formatINR(taxProfile.annualSalary), sub: taxProfile.regime + " Regime" },
            { label: "Effective Rate", value: `${taxProfile.effectiveRate}%`, sub: `Marginal ${taxProfile.marginalRate}%` },
            { label: "Total Tax/yr", value: formatINR(taxProfile.totalTax), sub: `₹${Math.round(taxProfile.totalTax / 12).toLocaleString("en-IN")}/mo` },
            { label: "80D Available", value: formatINR(taxProfile.remaining80D), sub: "Health insurance" },
          ].map((c) => (
            <div key={c.label} className="p-4 rounded-xl bg-white/5 border border-white/5">
              <p className="text-xs text-brand-400 mb-1">{c.label}</p>
              <p className="text-xl font-bold text-white">{c.value}</p>
              <p className="text-xs text-brand-400 mt-1">{c.sub}</p>
            </div>
          ))}
        </div>
      </motion.section>

      {/* ── STEP 8: Stock Analysis ────────────────────────────────────────── */}
      <LiveStockSection
        step={6 + sipPlans.length}
        tickers={result.input.stocksHeld}
      />

      {/* ── STEP 9: Portfolio Rebalancing ──────────────────────────────────── */}
      <motion.section variants={fadeIn} className="glass-card p-8">
        <SectionTitle step={7 + sipPlans.length} title="Portfolio Rebalancing" icon={ShieldAlert} />
        <div className="flex flex-wrap gap-4 text-sm text-brand-300 mb-6">
          <span>Portfolio Value: {formatINR(rebalancing.portfolioValue)}</span>
          <span>Current: {rebalancing.allocationSummary}</span>
          <span className={`font-bold ${rebalancing.needsRebalancing ? "text-amber-300" : "text-emerald-300"}`}>
            {rebalancing.needsRebalancing ? "⚠ REBALANCING NEEDED" : "✅ BALANCED"}
          </span>
        </div>

        {/* Drift Analysis */}
        <p className="text-xs text-brand-400 font-semibold mb-3">Current vs Target Allocation</p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
          <div>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={rebalancing.driftAnalysis.map(d => ({ name: d.category.substring(0, 10), current: d.currentPct, target: d.targetPct }))}>
                <XAxis dataKey="name" tick={{ fill: "#9cb1c5", fontSize: 10 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: "#9cb1c5", fontSize: 10 }} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={{ backgroundColor: "rgba(26,26,46,0.95)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "8px", fontSize: "12px", color: "#fff" }} />
                <Legend wrapperStyle={{ fontSize: "11px", color: "#cbc4f1" }} />
                <Bar dataKey="current" fill="#bf616a" name="Current %" radius={[4, 4, 0, 0]} />
                <Bar dataKey="target" fill="#2B8A3E" name="Target %" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="space-y-2">
            {rebalancing.driftAnalysis.map((d) => (
              <div key={d.category} className="flex items-center justify-between p-2 rounded-lg bg-white/5 text-xs">
                <span className="text-brand-200 w-28 truncate capitalize">{d.category}</span>
                <span className="text-white">{d.currentPct}%</span>
                <span className="text-brand-400">→</span>
                <span className="text-white">{d.targetPct}%</span>
                <span className={`font-bold ${d.action === "SELL" ? "text-red-300" : d.action === "BUY" ? "text-emerald-300" : "text-brand-400"}`}>
                  {d.action}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Orders */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {rebalancing.sellOrders.length > 0 && (
            <div>
              <p className="text-xs text-red-400 font-semibold mb-2">SELL ORDERS</p>
              {rebalancing.sellOrders.map((o, i) => (
                <div key={i} className="flex justify-between items-center p-3 rounded-lg bg-red-500/5 border border-red-500/10 mb-2 text-sm">
                  <span className="text-white">SELL {formatINR(o.amount)} of {o.ticker}</span>
                  <span className="text-red-300 font-medium">{formatINR(o.amount)}</span>
                </div>
              ))}
            </div>
          )}
          {rebalancing.buyOrders.length > 0 && (
            <div>
              <p className="text-xs text-emerald-400 font-semibold mb-2">BUY ORDERS</p>
              {rebalancing.buyOrders.map((o, i) => (
                <div key={i} className="p-3 rounded-lg bg-emerald-500/5 border border-emerald-500/10 mb-2 text-sm">
                  <div className="flex justify-between items-center">
                    <span className="text-white">BUY → {o.category}</span>
                    <span className="text-emerald-300 font-medium">{formatINR(o.amount)}</span>
                  </div>
                  {o.suggestions && <p className="text-xs text-brand-400 mt-1">{o.suggestions.join(", ")}</p>}
                </div>
              ))}
            </div>
          )}
        </div>
        <div className="mt-4 p-3 rounded-lg bg-white/5 border border-white/5">
          {rebalancing.notes.map((n, i) => <p key={i} className="text-xs text-brand-300 mb-1">• {n}</p>)}
        </div>
      </motion.section>

      {/* ── STEP 10: Emergency Fund ───────────────────────────────────────── */}
      <motion.section variants={fadeIn} className="glass-card p-8">
        <SectionTitle step={8 + sipPlans.length} title="Emergency Fund Buffer" icon={ShieldAlert} />
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          {[
            { label: "Monthly Inflow", value: formatINR(emergencyFund.monthlyInflow) },
            { label: "Monthly Outflow", value: formatINR(emergencyFund.monthlyOutflow) },
            { label: "Surplus", value: formatINR(emergencyFund.monthlySurplus) },
            { label: "Survival Runway", value: `${emergencyFund.survivalMonths} months`, color: emergencyFund.survivalMonths >= 6 ? "text-emerald-300" : emergencyFund.survivalMonths >= 3 ? "text-amber-300" : "text-red-300" },
          ].map((c) => (
            <div key={c.label} className="p-4 rounded-xl bg-white/5 border border-white/5">
              <p className="text-xs text-brand-400 mb-1">{c.label}</p>
              <p className={`text-xl font-bold ${"color" in c && c.color ? c.color : "text-white"}`}>{c.value}</p>
            </div>
          ))}
        </div>
        <div className="p-4 rounded-xl bg-white/5 border border-white/5">
          <div className="flex justify-between text-sm mb-2">
            <span className="text-brand-300">Emergency Fund Progress</span>
            <span className="text-white font-medium">{formatINR(emergencyFund.currentFund)} / {formatINR(emergencyFund.recommendedFund)}</span>
          </div>
          <div className="h-4 bg-white/5 rounded-full overflow-hidden">
            <div className="h-full rounded-full transition-all duration-1000"
              style={{ width: `${Math.min(100, (emergencyFund.currentFund / emergencyFund.recommendedFund) * 100)}%`,
                       background: "linear-gradient(90deg, #8274dd, #2B8A3E)" }} />
          </div>
          {emergencyFund.gap > 0 && (
            <p className="text-xs text-brand-400 mt-2">Gap: {formatINR(emergencyFund.gap)} · ~{emergencyFund.monthsToFill} months to fill</p>
          )}
        </div>
      </motion.section>

      {/* ── SUMMARY ───────────────────────────────────────────────────────── */}
      <motion.section variants={fadeIn} className="glass-card p-8 relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-brand-500/5 to-transparent" />
        <div className="relative z-10">
          <SectionTitle step={9 + sipPlans.length} title={`What The System Tells ${result.input.name}`} icon={Zap} />
          <div className="space-y-3">
            {summary.map((s) => {
              const colors: Record<string, string> = {
                success: "bg-emerald-500/10 border-emerald-500/20 text-emerald-300",
                warning: "bg-amber-500/10 border-amber-500/20 text-amber-300",
                action: "bg-brand-500/10 border-brand-400/20 text-brand-200",
                info: "bg-white/5 border-white/10 text-brand-200",
              };
              const iconClass = "w-4 h-4 mt-0.5 shrink-0 opacity-70";
              const renderIcon = () => {
                switch (s.type) {
                  case "success": return <CheckCircle className={iconClass} />;
                  case "warning": return <AlertTriangle className={iconClass} />;
                  case "action": return <ArrowUpRight className={iconClass} />;
                  default: return <Info className={iconClass} />;
                }
              };
              return (
                <div key={s.number} className={`flex items-start gap-4 p-4 rounded-xl border ${colors[s.type] || colors.info}`}>
                  <div className="w-8 h-8 rounded-full bg-white/10 flex items-center justify-center shrink-0 text-sm font-bold">
                    {s.number}
                  </div>
                  <div className="flex items-start gap-2 flex-1">
                    {renderIcon()}
                    <p className="text-sm leading-relaxed">{s.text}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </motion.section>

    </motion.div>
  );
}
