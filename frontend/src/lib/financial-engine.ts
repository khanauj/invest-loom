// ─── Types ─────────────────────────────────────────────────────────────────────

export interface UserInput {
  name: string;
  age: number;
  salary: number;
  monthlySavings: number;
  currentSIP: number;
  portfolioValue: number;
  equityPercent: number;
  stocksHeld: string[];
  mutualFundCount: number;
  dependents: number;
  emergencyFundMonths: number;
  debtToIncome: number;
  experience: "beginner" | "intermediate" | "expert";
  goals: Goal[];
}

export interface Goal {
  type: "house" | "retirement" | "education" | "car" | "wealth" | "emergency";
  label: string;
  targetAmount: number;
  years: number;
}

export interface RiskBreakdownItem {
  category: string;
  score: number;
  maxScore: number;
  reason: string;
}

export interface RiskScore {
  total: number;
  level: string;
  breakdown: RiskBreakdownItem[];
}

export interface ProfileMatch {
  name: string;
  score: number;
  isYou: boolean;
}

export interface InvestorProfile {
  segment: string;
  segmentScore: number;
  description: string;
  traits: string[];
  matches: ProfileMatch[];
  warnings: string[];
}

export interface AIRecommendation {
  action: string;
  confidence: number;
  reasoning: string;
  currentSIP: number;
  recommendedSIP: number;
  increase: number;
  opportunityCost: {
    years: number;
    currentGrowth: number;
    increasedGrowth: number;
    leftOnTable: number;
  };
}

export interface FundAllocation {
  fundName: string;
  amount: number;
  percentage: number;
  returns5yr: number;
  expenseRatio: number;
  purpose: string;
}

export interface CorpusProjection {
  finalCorpus: number;
  totalInvested: number;
  wealthGain: number;
}

export interface GoalAnalysis {
  targetAmount: number;
  flatCorpus: number;
  stepupCorpus: number;
  flatReaches: boolean;
  stepupReaches: boolean;
  flatShortfall: number;
  stepupShortfall: number;
  sipNeeded: number;
  extraSipNeeded: number;
  yearsAtCurrentSIP: number;
  extraMonths: number;
  verdict: string;
}

export interface SIPPlan {
  goalLabel: string;
  goalType: string;
  years: number;
  targetAmount: number;
  monthlySIP: number;
  blendedCAGR: number;
  existingCorpus: number;
  allocations: FundAllocation[];
  flatProjection: CorpusProjection;
  stepupProjection: CorpusProjection;
  goalAnalysis: GoalAnalysis;
}

export interface FundComparisonEntry {
  rank: number;
  fundName: string;
  category: string;
  returns5yr: number;
  expenseRatio: number;
  netCorpus: number;
  wealthGain: number;
  multiplier: number;
  hitsGoal: boolean;
  goalGap: number;
  risk: string;
  bestFor: string;
}

export interface FundComparison {
  monthlySIP: number;
  years: number;
  goalAmount: number;
  results: FundComparisonEntry[];
  winnerNotes: string[];
}

export interface TaxProfile {
  annualSalary: number;
  regime: string;
  effectiveRate: number;
  totalTax: number;
  remaining80C: number;
  remaining80D: number;
  marginalRate: number;
}

export interface StockEntry {
  ticker: string;
  price: number;
  changePct: number;
  signal: string;
  signalStrength: string;
  signalScore: number;
  totalScore: number;
  grade: string;
  recommendation: string;
  fundamental: number;
  technical: number;
  valuation: number;
  sentiment: number;
  indicators: string[];
}

export interface StockAnalysis {
  stocks: StockEntry[];
  ranking: StockEntry[];
}

export interface DriftItem {
  category: string;
  currentPct: number;
  targetPct: number;
  driftPct: number;
  action: string;
}

export interface RebalanceOrder {
  type: "SELL" | "BUY";
  ticker?: string;
  category?: string;
  quantity?: number;
  price?: number;
  amount: number;
  reason: string;
  suggestions?: string[];
}

export interface RebalancingPlan {
  portfolioValue: number;
  allocationSummary: string;
  needsRebalancing: boolean;
  driftAnalysis: DriftItem[];
  sellOrders: RebalanceOrder[];
  buyOrders: RebalanceOrder[];
  notes: string[];
}

export interface EmergencyFundAnalysis {
  monthlyInflow: number;
  monthlyOutflow: number;
  monthlySurplus: number;
  currentFund: number;
  survivalMonths: number;
  status: string;
  sipSustainability: string;
  recommendedFund: number;
  gap: number;
  monthsToFill: number;
}

export interface SummaryItem {
  number: number;
  text: string;
  type: "action" | "warning" | "success" | "info";
}

export interface AnalysisResult {
  input: UserInput;
  riskScore: RiskScore;
  profile: InvestorProfile;
  recommendation: AIRecommendation;
  sipPlans: SIPPlan[];
  fundComparison: FundComparison;
  taxProfile: TaxProfile;
  stockAnalysis: StockAnalysis;
  rebalancing: RebalancingPlan;
  emergencyFund: EmergencyFundAnalysis;
  summary: SummaryItem[];
}

// ─── Calculation Helpers ───────────────────────────────────────────────────────

function projectCorpus(
  sip: number,
  years: number,
  cagr: number,
  stepUpPct: number = 0,
  existingCorpus: number = 0
): CorpusProjection {
  const monthlyRate = cagr / 100 / 12;
  let corpus = existingCorpus;
  let totalInvested = existingCorpus;
  let currentSip = sip;

  for (let year = 1; year <= years; year++) {
    for (let month = 1; month <= 12; month++) {
      corpus = (corpus + currentSip) * (1 + monthlyRate);
      totalInvested += currentSip;
    }
    currentSip *= 1 + stepUpPct / 100;
  }

  return {
    finalCorpus: Math.round(corpus),
    totalInvested: Math.round(totalInvested),
    wealthGain: Math.round(corpus - totalInvested),
  };
}

function sipNeededForGoal(
  target: number,
  years: number,
  cagr: number,
  existing: number = 0
): number {
  const monthlyRate = cagr / 100 / 12;
  const months = years * 12;
  const existingFV = existing * Math.pow(1 + monthlyRate, months);
  const remaining = target - existingFV;
  if (remaining <= 0) return 0;
  const factor =
    (Math.pow(1 + monthlyRate, months) - 1) / monthlyRate * (1 + monthlyRate);
  return Math.round(remaining / factor);
}

function monthsToGoal(
  target: number,
  sip: number,
  cagr: number,
  existing: number = 0
): number {
  const monthlyRate = cagr / 100 / 12;
  let corpus = existing;
  let months = 0;
  while (corpus < target && months < 600) {
    corpus = (corpus + sip) * (1 + monthlyRate);
    months++;
  }
  return months;
}

// Stock data is fetched live from /api/stocks — no mock data here.

// ─── Fund Database ─────────────────────────────────────────────────────────────

interface FundInfo {
  name: string; category: string; returns1yr: number; returns3yr: number;
  returns5yr: number; expenseRatio: number; risk: string; bestFor: string;
}

const FUNDS: Record<string, FundInfo[]> = {
  house: [
    { name: "SBI Gilt Fund", category: "debt_funds", returns1yr: 7.2, returns3yr: 7.8, returns5yr: 8.0, expenseRatio: 0.46, risk: "low", bestFor: "Safety + moderate returns" },
    { name: "Mirae Asset Large Cap Fund", category: "large_cap_equity", returns1yr: 14.2, returns3yr: 14.8, returns5yr: 15.1, expenseRatio: 1.05, risk: "moderate", bestFor: "Equity stability" },
    { name: "HDFC Balanced Advantage Fund", category: "hybrid", returns1yr: 13.5, returns3yr: 14.0, returns5yr: 14.5, expenseRatio: 1.36, risk: "moderate", bestFor: "Dynamic asset allocation" },
    { name: "Nippon India Gold ETF", category: "gold", returns1yr: 11.5, returns3yr: 12.0, returns5yr: 12.8, expenseRatio: 0.20, risk: "moderate", bestFor: "Inflation hedge" },
  ],
  retirement: [
    { name: "Mirae Asset Large Cap Fund", category: "large_cap_equity", returns1yr: 14.2, returns3yr: 14.8, returns5yr: 15.1, expenseRatio: 1.05, risk: "moderate", bestFor: "Core equity" },
    { name: "Axis Midcap Fund", category: "mid_cap_equity", returns1yr: 20.5, returns3yr: 21.5, returns5yr: 22.3, expenseRatio: 1.72, risk: "high", bestFor: "Aggressive growth" },
    { name: "Mirae Asset Tax Saver (ELSS)", category: "elss", returns1yr: 18.5, returns3yr: 19.2, returns5yr: 20.1, expenseRatio: 1.18, risk: "moderate-high", bestFor: "80C tax saving" },
    { name: "Nippon India Small Cap Fund", category: "small_cap_equity", returns1yr: 25.0, returns3yr: 27.0, returns5yr: 28.1, expenseRatio: 1.55, risk: "very high", bestFor: "High growth" },
    { name: "Motilal Nasdaq 100 FOF", category: "international", returns1yr: 20.0, returns3yr: 21.0, returns5yr: 22.8, expenseRatio: 0.50, risk: "high", bestFor: "US tech exposure" },
    { name: "Nippon India Gold ETF", category: "gold", returns1yr: 11.5, returns3yr: 12.0, returns5yr: 12.8, expenseRatio: 0.20, risk: "moderate", bestFor: "Inflation hedge" },
    { name: "SBI Gilt Fund", category: "debt_funds", returns1yr: 7.2, returns3yr: 7.8, returns5yr: 8.0, expenseRatio: 0.46, risk: "low", bestFor: "Safety net" },
  ],
  education: [
    { name: "HDFC Mid-Cap Opportunities Fund", category: "mid_cap_equity", returns1yr: 18.0, returns3yr: 19.5, returns5yr: 20.8, expenseRatio: 1.42, risk: "high", bestFor: "Mid-term growth" },
    { name: "Axis Bluechip Fund", category: "large_cap_equity", returns1yr: 12.8, returns3yr: 13.5, returns5yr: 14.2, expenseRatio: 1.25, risk: "moderate", bestFor: "Stable equity" },
    { name: "HDFC Short Duration Fund", category: "debt_funds", returns1yr: 7.0, returns3yr: 7.5, returns5yr: 7.8, expenseRatio: 0.38, risk: "low", bestFor: "Debt stability" },
  ],
  wealth: [
    { name: "Parag Parikh Flexi Cap Fund", category: "flexi_cap", returns1yr: 17.5, returns3yr: 18.8, returns5yr: 19.8, expenseRatio: 1.32, risk: "moderate", bestFor: "All-weather growth" },
    { name: "Axis Midcap Fund", category: "mid_cap_equity", returns1yr: 20.5, returns3yr: 21.5, returns5yr: 22.3, expenseRatio: 1.72, risk: "high", bestFor: "Aggressive growth" },
    { name: "UTI Nifty 50 Index Fund", category: "index", returns1yr: 12.0, returns3yr: 13.0, returns5yr: 13.8, expenseRatio: 0.10, risk: "moderate", bestFor: "Low cost" },
    { name: "Nippon India Gold ETF", category: "gold", returns1yr: 11.5, returns3yr: 12.0, returns5yr: 12.8, expenseRatio: 0.20, risk: "moderate", bestFor: "Diversification" },
  ],
  car: [
    { name: "ICICI Pru Balanced Advantage Fund", category: "hybrid", returns1yr: 12.5, returns3yr: 13.0, returns5yr: 13.8, expenseRatio: 1.20, risk: "moderate", bestFor: "Balanced growth" },
    { name: "Kotak Bond Short Term Fund", category: "debt_funds", returns1yr: 7.5, returns3yr: 7.8, returns5yr: 8.2, expenseRatio: 0.40, risk: "low", bestFor: "Safety" },
  ],
  emergency: [
    { name: "ICICI Pru Liquid Fund", category: "liquid", returns1yr: 6.8, returns3yr: 6.5, returns5yr: 6.2, expenseRatio: 0.20, risk: "very low", bestFor: "Instant liquidity" },
    { name: "Axis Liquid Fund", category: "liquid", returns1yr: 6.9, returns3yr: 6.6, returns5yr: 6.3, expenseRatio: 0.15, risk: "very low", bestFor: "Ultra-safe parking" },
  ],
};

const FUND_ALLOCATIONS: Record<string, number[]> = {
  house: [40, 30, 20, 10],
  retirement: [25, 20, 20, 10, 10, 10, 5],
  education: [40, 35, 25],
  wealth: [35, 30, 20, 15],
  car: [60, 40],
  emergency: [50, 50],
};

// ─── Main Analysis Function ────────────────────────────────────────────────────

export function runAnalysis(input: UserInput): AnalysisResult {
  const savingsRate = (input.monthlySavings / input.salary) * 100;
  const annualSalary = input.salary * 12;
  const instruments = input.stocksHeld.length + input.mutualFundCount;
  const debtPercent = 100 - input.equityPercent;
  const shortestGoalYears = Math.min(...input.goals.map((g) => g.years), 30);

  // ── STEP 1: Risk Score ─────────────────────────────────────────────────────
  const incomeStab = Math.max(0, Math.round(Math.min(20, (1 - savingsRate / 40) * 10)));
  const depBurden = Math.min(20, Math.round(input.dependents * 7 + input.debtToIncome * 0.1 * 20));
  const safetyNet = Math.min(20, Math.round(Math.max(0, (6 - input.emergencyFundMonths) * 3.33)));
  const portVolat = Math.min(20, Math.round(input.equityPercent * 0.16 + Math.max(0, (8 - instruments)) * 0.8));
  const timeHoriz = Math.min(20, Math.round(
    (input.experience === "beginner" ? 10 : input.experience === "intermediate" ? 5 : 2)
    + Math.max(0, (10 - shortestGoalYears)) * 0.5
  ));

  const riskTotal = incomeStab + depBurden + safetyNet + portVolat + timeHoriz;
  const riskLevel = riskTotal <= 30 ? "LOW RISK" : riskTotal <= 55 ? "MODERATE RISK" : "HIGH RISK";

  const riskScore: RiskScore = {
    total: riskTotal,
    level: riskLevel,
    breakdown: [
      { category: "Income Stability", score: incomeStab, maxScore: 20, reason: `Salaried, ${savingsRate.toFixed(1)}% savings ratio` },
      { category: "Dependency Burden", score: depBurden, maxScore: 20, reason: `${input.dependents} dependent(s), ${input.debtToIncome}% DTI` },
      { category: "Safety Net", score: safetyNet, maxScore: 20, reason: `${input.emergencyFundMonths} months emergency fund` },
      { category: "Portfolio Volatility", score: portVolat, maxScore: 20, reason: `${input.equityPercent}% equity, ${instruments} instruments` },
      { category: "Time Horizon", score: timeHoriz, maxScore: 20, reason: `${shortestGoalYears}yr goal, ${input.experience}` },
    ],
  };

  // ── STEP 2: Investor Profile ───────────────────────────────────────────────
  const hasSIP = input.currentSIP > 0;
  const profiles: { name: string; score: number }[] = [
    { name: "BALANCED_PLANNER", score: Math.round(50 + (savingsRate > 20 ? 15 : 0) + (hasSIP ? 10 : 0) + (instruments > 3 ? 5 : 0) - (riskTotal > 50 ? 20 : 0)) },
    { name: "YOUNG_ACCUMULATOR", score: Math.round(40 + (input.age < 30 ? 20 : 0) + (hasSIP ? 10 : 0) - (input.dependents > 1 ? 10 : 0)) },
    { name: "AGGRESSIVE_INVESTOR", score: Math.round(30 + (input.equityPercent > 70 ? 20 : 0) + (riskTotal > 50 ? 10 : 0) + (input.experience === "expert" ? 10 : 0)) },
    { name: "PASSIVE_HOLDER", score: Math.round(60 - (hasSIP ? 20 : 0) - (savingsRate > 15 ? 10 : 0) - (instruments > 4 ? 5 : 0)) },
    { name: "GOAL_CHASER", score: Math.round(20 + input.goals.length * 15 - (instruments > 3 ? 5 : 0)) },
    { name: "HIGH_RISK_BEGINNER", score: Math.round(20 + (input.experience === "beginner" ? 25 : 0) + (input.equityPercent > 80 ? 15 : 0) - (savingsRate > 25 ? 10 : 0)) },
    { name: "CONSERVATIVE_SAVER", score: Math.round(10 + (debtPercent > 60 ? 25 : 0) + (riskTotal < 25 ? 15 : 0) - (input.equityPercent > 50 ? 20 : 0)) },
    { name: "DEBT_HEAVY_STRUGGLER", score: Math.round(Math.max(0, input.debtToIncome * 2 - 20 + (input.emergencyFundMonths < 2 ? 15 : 0))) },
  ].sort((a, b) => b.score - a.score);

  const topProfile = profiles[0];
  const segmentDescriptions: Record<string, { desc: string; traits: string[] }> = {
    BALANCED_PLANNER: { desc: "Well-diversified, disciplined SIP investor. Good savings habits with moderate risk appetite.", traits: ["moderate risk", "diversified portfolio", "active SIP", "disciplined"] },
    YOUNG_ACCUMULATOR: { desc: "Early-stage investor building wealth through consistent contributions and equity exposure.", traits: ["growth-focused", "long horizon", "tech-savvy", "learning"] },
    AGGRESSIVE_INVESTOR: { desc: "High conviction equity investor willing to accept significant volatility for superior returns.", traits: ["high risk", "concentrated positions", "momentum trader", "confident"] },
    PASSIVE_HOLDER: { desc: "Set-and-forget investor with minimal portfolio activity. May need more active management.", traits: ["passive", "infrequent review", "buy and hold", "minimal SIP"] },
    GOAL_CHASER: { desc: "Multiple financial goals with dedicated plans. Needs careful allocation across targets.", traits: ["goal-oriented", "multiple targets", "structured", "deadline-driven"] },
    HIGH_RISK_BEGINNER: { desc: "New investor with heavy equity tilt. Education and risk management are priorities.", traits: ["high equity", "low experience", "potential for overtrading", "needs guidance"] },
    CONSERVATIVE_SAVER: { desc: "Safety-first approach with heavy debt allocation. Could benefit from more equity exposure.", traits: ["low risk", "debt-heavy", "capital preservation", "income-focused"] },
    DEBT_HEAVY_STRUGGLER: { desc: "High debt-to-income ratio limiting investment capacity. Priority: reduce debt.", traits: ["high DTI", "limited savings", "debt reduction priority", "constrained"] },
  };

  const profileInfo = segmentDescriptions[topProfile.name] || segmentDescriptions["BALANCED_PLANNER"];

  const profileWarnings: string[] = [];
  if (savingsRate < 20) profileWarnings.push("Aim to increase savings rate to at least 20%");
  if (!hasSIP) profileWarnings.push("Start a systematic investment plan (SIP)");
  if (input.emergencyFundMonths < 6) profileWarnings.push("Build emergency fund to 6 months of expenses");
  if (input.equityPercent > 80 && input.experience === "beginner") profileWarnings.push("Consider reducing equity exposure until you gain more experience");
  profileWarnings.push("Periodically review asset allocation");
  if (hasSIP) profileWarnings.push("Increase SIP with salary growth");

  const investorProfile: InvestorProfile = {
    segment: topProfile.name.replace(/_/g, " "),
    segmentScore: Math.min(100, topProfile.score),
    description: profileInfo.desc,
    traits: profileInfo.traits,
    matches: profiles.map((p, i) => ({
      name: p.name.replace(/_/g, " "),
      score: Math.max(0, Math.min(100, p.score)),
      isYou: i === 0,
    })),
    warnings: profileWarnings,
  };

  // ── STEP 3: AI Recommendation ──────────────────────────────────────────────
  const recommendedSIP = Math.round(input.monthlySavings * 0.7 / 1000) * 1000;
  const sipIncrease = Math.max(0, recommendedSIP - input.currentSIP);
  const confidence = Math.min(95, Math.round(50 + savingsRate * 0.8 + (hasSIP ? 10 : 0)));

  const currentGrowth10yr = projectCorpus(input.currentSIP, 10, 12).finalCorpus;
  const increasedGrowth10yr = projectCorpus(recommendedSIP, 10, 12).finalCorpus;

  const action =
    input.currentSIP === 0 ? "START_SIP" :
    sipIncrease > 0       ? "INCREASE_SIP" :
                            "MAINTAIN_SIP";

  const reasoning =
    input.currentSIP === 0
      ? `You have no SIP yet. Starting one is the highest-impact move you can make right now. Based on your savings of INR ${input.monthlySavings.toLocaleString("en-IN")}/mo, you can comfortably begin with INR ${recommendedSIP.toLocaleString("en-IN")}/mo.`
      : sipIncrease > 0
        ? `Strong savings ratio (${savingsRate.toFixed(1)}%) supports higher contributions. INR ${input.currentSIP.toLocaleString("en-IN")} → INR ${recommendedSIP.toLocaleString("en-IN")}/mo (+INR ${sipIncrease.toLocaleString("en-IN")})`
        : `Current SIP of INR ${input.currentSIP.toLocaleString("en-IN")}/mo is well-calibrated to your income and goals.`;

  const recommendation: AIRecommendation = {
    action,
    confidence,
    reasoning,
    currentSIP: input.currentSIP,
    recommendedSIP,
    increase: sipIncrease,
    opportunityCost: {
      years: 10,
      currentGrowth: currentGrowth10yr,
      increasedGrowth: increasedGrowth10yr,
      leftOnTable: increasedGrowth10yr - currentGrowth10yr,
    },
  };

  // ── STEP 4+5: SIP Plans per Goal ──────────────────────────────────────────
  const sipPlans: SIPPlan[] = input.goals.map((goal) => {
    const goalFunds = FUNDS[goal.type] || FUNDS["wealth"];
    const allocPcts = FUND_ALLOCATIONS[goal.type] || [40, 30, 20, 10];
    const allocations: FundAllocation[] = goalFunds.map((f, i) => ({
      fundName: f.name,
      amount: Math.round((recommendedSIP * (allocPcts[i] || 10)) / 100),
      percentage: allocPcts[i] || 10,
      returns5yr: f.returns5yr,
      expenseRatio: f.expenseRatio,
      purpose: f.bestFor,
    }));

    const blendedCAGR = allocations.reduce((sum, a) => sum + a.returns5yr * a.percentage, 0) / 100;

    const flatProj = projectCorpus(recommendedSIP, goal.years, blendedCAGR, 0, input.portfolioValue);
    const stepupProj = projectCorpus(recommendedSIP, goal.years, blendedCAGR, 10, input.portfolioValue);

    const sipNeeded = sipNeededForGoal(goal.targetAmount, goal.years, blendedCAGR, input.portfolioValue);
    const monthsNeeded = monthsToGoal(goal.targetAmount, recommendedSIP, blendedCAGR, input.portfolioValue);
    const yrsNeeded = Math.floor(monthsNeeded / 12);
    const extraMo = monthsNeeded % 12;

    return {
      goalLabel: goal.label,
      goalType: goal.type,
      years: goal.years,
      targetAmount: goal.targetAmount,
      monthlySIP: recommendedSIP,
      blendedCAGR: Math.round(blendedCAGR * 100) / 100,
      existingCorpus: input.portfolioValue,
      allocations,
      flatProjection: flatProj,
      stepupProjection: stepupProj,
      goalAnalysis: {
        targetAmount: goal.targetAmount,
        flatCorpus: flatProj.finalCorpus,
        stepupCorpus: stepupProj.finalCorpus,
        flatReaches: flatProj.finalCorpus >= goal.targetAmount,
        stepupReaches: stepupProj.finalCorpus >= goal.targetAmount,
        flatShortfall: Math.max(0, goal.targetAmount - flatProj.finalCorpus),
        stepupShortfall: Math.max(0, goal.targetAmount - stepupProj.finalCorpus),
        sipNeeded,
        extraSipNeeded: Math.max(0, sipNeeded - recommendedSIP),
        yearsAtCurrentSIP: yrsNeeded,
        extraMonths: extraMo,
        verdict: flatProj.finalCorpus >= goal.targetAmount
          ? "Goal reached with flat SIP"
          : `Increase SIP by INR ${Math.max(0, sipNeeded - recommendedSIP).toLocaleString("en-IN")}/mo to hit goal on time`,
      },
    };
  });

  // ── STEP 6: Fund Comparison ────────────────────────────────────────────────
  const compFunds: FundInfo[] = [
    { name: "Axis Midcap Fund", category: "mid_cap_equity", returns1yr: 20.5, returns3yr: 21.5, returns5yr: 22.3, expenseRatio: 1.72, risk: "high", bestFor: "Aggressive growth" },
    { name: "Parag Parikh Flexi Cap Fund", category: "flexi_cap", returns1yr: 17.5, returns3yr: 18.8, returns5yr: 19.8, expenseRatio: 1.32, risk: "moderate", bestFor: "All-weather + 15% int'l exposure" },
    { name: "UTI Nifty 50 Index Fund", category: "index", returns1yr: 12.0, returns3yr: 13.0, returns5yr: 13.8, expenseRatio: 0.10, risk: "moderate", bestFor: "Low cost passive" },
  ];

  const longestGoal = input.goals.reduce((a, b) => (a.years > b.years ? a : b), input.goals[0]);
  const compResults: FundComparisonEntry[] = compFunds
    .map((f, i) => {
      const proj = projectCorpus(recommendedSIP, longestGoal.years, f.returns5yr, 0, 0);
      const expenseDrag = Math.round(proj.finalCorpus * f.expenseRatio * longestGoal.years / 100);
      const netCorpus = proj.finalCorpus - expenseDrag;
      return {
        rank: i + 1,
        fundName: f.name,
        category: f.category,
        returns5yr: f.returns5yr,
        expenseRatio: f.expenseRatio,
        netCorpus,
        wealthGain: netCorpus - proj.totalInvested,
        multiplier: Math.round((netCorpus / proj.totalInvested) * 100) / 100,
        hitsGoal: netCorpus >= longestGoal.targetAmount,
        goalGap: Math.max(0, longestGoal.targetAmount - netCorpus),
        risk: f.risk,
        bestFor: f.bestFor,
      };
    })
    .sort((a, b) => b.netCorpus - a.netCorpus)
    .map((r, i) => ({ ...r, rank: i + 1 }));

  const fundComparison: FundComparison = {
    monthlySIP: recommendedSIP,
    years: longestGoal.years,
    goalAmount: longestGoal.targetAmount,
    results: compResults,
    winnerNotes: [
      `${compResults[0].fundName} → ${compResults[0].multiplier}x your money, but ${compResults[0].risk} risk`,
      compResults.length > 1 ? `Safe choice: ${compResults[1].fundName} → ${compResults[1].multiplier}x, ${compResults[1].bestFor}` : "",
    ].filter(Boolean),
  };

  // ── STEP 7: Tax Profile ────────────────────────────────────────────────────
  let totalTax = 0;
  if (annualSalary <= 300000) totalTax = 0;
  else if (annualSalary <= 700000) totalTax = (annualSalary - 300000) * 0.05;
  else if (annualSalary <= 1000000) totalTax = 20000 + (annualSalary - 700000) * 0.1;
  else if (annualSalary <= 1200000) totalTax = 50000 + (annualSalary - 1000000) * 0.15;
  else if (annualSalary <= 1500000) totalTax = 80000 + (annualSalary - 1200000) * 0.2;
  else totalTax = 140000 + (annualSalary - 1500000) * 0.3;

  totalTax = Math.round(totalTax + totalTax * 0.04);
  const effectiveRate = annualSalary > 0 ? Math.round((totalTax / annualSalary) * 10000) / 100 : 0;
  const marginalRate = annualSalary <= 300000 ? 0 : annualSalary <= 700000 ? 5 : annualSalary <= 1000000 ? 10 : 15;

  const taxProfile: TaxProfile = {
    annualSalary,
    regime: "New",
    effectiveRate,
    totalTax,
    remaining80C: 0,
    remaining80D: 25000,
    marginalRate,
  };

  // ── STEP 8: Stock Analysis ─────────────────────────────────────────────────
  // Live data is fetched client-side by AnalysisResults via /api/stocks.
  // runAnalysis stays synchronous; the component handles async fetching.
  const stockAnalysis: StockAnalysis = { stocks: [], ranking: [] };

  // ── STEP 9: Portfolio Rebalancing ──────────────────────────────────────────
  const totalHoldingValue = input.portfolioValue;

  const targetAlloc: Record<string, number> = {
    large_cap_equity: 35, debt_funds: 25, mid_cap_equity: 15,
    liquid_funds: 10, international: 5, small_cap_equity: 5, gold: 5,
  };

  // Approximate current allocation: user-supplied equity% is treated as large-cap equity
  const currentCategories: DriftItem[] = Object.entries(targetAlloc).map(([cat, target]) => {
    const current = cat === "large_cap_equity" ? input.equityPercent : 0;
    return {
      category: cat.replace(/_/g, " "),
      currentPct: current,
      targetPct: target,
      driftPct: current - target,
      action: current > target + 5 ? "SELL" : current < target - 5 ? "BUY" : "OK",
    };
  });

  // Sell orders by INR amount — no fake share quantities
  const overweightEquityPct = Math.max(0, input.equityPercent - 35);
  const overweightValue = Math.round((overweightEquityPct / 100) * totalHoldingValue);
  const sellOrders: RebalanceOrder[] = input.stocksHeld.length > 0 && overweightValue >= 1000
    ? input.stocksHeld.slice(0, 5).map((t, _, arr) => ({
        type: "SELL" as const,
        ticker: t.trim().toUpperCase(),
        amount: Math.round(overweightValue / arr.length),
        reason: `Reduce equity overweight (${overweightEquityPct.toFixed(0)}% above 35% target)`,
      }))
    : [];

  const sellAmount = sellOrders.reduce((s, o) => s + o.amount, 0) || totalHoldingValue * 0.2;

  const buyCategories = [
    { cat: "Debt Funds", pct: 25, suggestions: ["HDFC Short Duration", "Kotak Bond"] },
    { cat: "Midcap", pct: 15, suggestions: ["Nifty Midcap 150", "Kotak Emerging"] },
    { cat: "Liquid Funds", pct: 10, suggestions: ["ICICI Pru Liquid", "Axis Liquid"] },
    { cat: "International", pct: 5, suggestions: ["Nasdaq 100 FOF", "Parag Parikh"] },
    { cat: "Small Cap", pct: 5, suggestions: ["Nifty Smallcap 250", "SBI Small Cap"] },
    { cat: "Gold", pct: 5, suggestions: ["SGB", "Nippon Gold ETF"] },
  ];

  const buyOrders: RebalanceOrder[] = buyCategories.map((b) => ({
    type: "BUY" as const, category: b.cat,
    amount: Math.round(sellAmount * b.pct / 65), reason: `Target ${b.pct}% allocation`,
    suggestions: b.suggestions,
  }));

  const rebalancing: RebalancingPlan = {
    portfolioValue: totalHoldingValue,
    allocationSummary: `${input.equityPercent}% Equity, ${100 - input.equityPercent}% Debt`,
    needsRebalancing: true,
    driftAnalysis: currentCategories,
    sellOrders, buyOrders,
    notes: [
      "Execute sells first before buying",
      "LTCG (12.5%) applies before STCG (20%)",
      "Review after 3 months for drift",
    ],
  };

  // ── STEP 10: Emergency Fund ────────────────────────────────────────────────
  const monthlyExpenses = input.salary - input.monthlySavings;
  const currentEmergencyFund = monthlyExpenses * input.emergencyFundMonths;
  const recommendedFund = monthlyExpenses * 6;
  const gap = Math.max(0, recommendedFund - currentEmergencyFund);
  const survivalMonths = input.monthlySavings > 0 ? currentEmergencyFund / monthlyExpenses : input.emergencyFundMonths;

  const emergencyFund: EmergencyFundAnalysis = {
    monthlyInflow: input.salary,
    monthlyOutflow: monthlyExpenses,
    monthlySurplus: input.monthlySavings,
    currentFund: currentEmergencyFund,
    survivalMonths: Math.round(survivalMonths * 10) / 10,
    status: survivalMonths >= 6 ? "STRONG" : survivalMonths >= 3 ? "ADEQUATE" : "WEAK",
    sipSustainability: input.monthlySavings >= input.currentSIP * 1.5 ? "COMFORTABLE" : "TIGHT",
    recommendedFund,
    gap,
    monthsToFill: gap > 0 && input.monthlySavings > 0 ? Math.ceil(gap / (input.monthlySavings * 0.3)) : 0,
  };

  // ── SUMMARY ────────────────────────────────────────────────────────────────
  const summary: SummaryItem[] = [
    { number: 1, text: `You are a ${investorProfile.segment} (risk score ${riskTotal}/100)`, type: "info" },
    { number: 2, text: sipIncrease > 0
      ? `INCREASE SIP from INR ${input.currentSIP.toLocaleString("en-IN")} to INR ${recommendedSIP.toLocaleString("en-IN")}/mo (not doing so costs ₹${(increasedGrowth10yr - currentGrowth10yr).toLocaleString("en-IN")} over 10 years)`
      : `MAINTAIN current SIP of INR ${input.currentSIP.toLocaleString("en-IN")}/mo`, type: sipIncrease > 0 ? "action" : "success" },
  ];

  sipPlans.forEach((plan, i) => {
    const ga = plan.goalAnalysis;
    summary.push({
      number: summary.length + 1,
      text: `${plan.goalLabel} (${plan.years}yr, ₹${(plan.targetAmount / 100000).toFixed(0)}L): ${ga.flatReaches ? "EASILY REACHED" : `Short by ₹${ga.flatShortfall.toLocaleString("en-IN")}`}`,
      type: ga.flatReaches ? "success" : "warning",
    });
  });

  summary.push(
    { number: summary.length + 1, text: `Best fund: ${compResults[0].fundName} (${compResults[0].multiplier}x in ${longestGoal.years}yr)`, type: "info" },
    { number: summary.length + 2, text: "REBALANCE: diversify into debt + midcap + gold", type: "action" },
    { number: summary.length + 5, text: gap > 0 ? `Top up emergency fund by ₹${gap.toLocaleString("en-IN")} (need 6 months)` : "Emergency fund is adequate", type: gap > 0 ? "warning" : "success" },
    { number: summary.length + 6, text: `Tax: use ELSS to maximize 80C deduction`, type: "info" },
  );

  // Re-number
  summary.forEach((s, i) => (s.number = i + 1));

  return {
    input,
    riskScore,
    profile: investorProfile,
    recommendation,
    sipPlans,
    fundComparison,
    taxProfile,
    stockAnalysis,
    rebalancing,
    emergencyFund,
    summary,
  };
}
