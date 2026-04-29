"use client";

import { useState } from "react";
import { motion, AnimatePresence, Variants } from "framer-motion";
import {
  Sparkles, ArrowLeft, Plus, Trash2, User, Briefcase,
  PiggyBank, BarChart3, ShieldCheck, Target, Loader2,
} from "lucide-react";
import Link from "next/link";
import { runAnalysis, type UserInput, type Goal, type AnalysisResult } from "@/lib/financial-engine";
import AnalysisResults from "@/components/AnalysisResults";

type Phase = "input" | "analyzing" | "results";

const GOAL_TYPES: { value: Goal["type"]; label: string }[] = [
  { value: "house", label: "🏠 House" },
  { value: "retirement", label: "🏖️ Retirement" },
  { value: "education", label: "🎓 Education" },
  { value: "car", label: "🚗 Car" },
  { value: "wealth", label: "💰 Wealth" },
  { value: "emergency", label: "🛡️ Emergency" },
];

const ANALYSIS_STEPS = [
  "Computing Risk Score...",
  "Matching Investor Profile...",
  "Generating AI Recommendation...",
  "Building SIP Plans...",
  "Comparing Funds...",
  "Calculating Tax Profile...",
  "Analyzing Live Stock Data...",
  "Computing Rebalancing Plan...",
  "Evaluating Emergency Buffer...",
  "Compiling Summary Report...",
];

const fadeIn: Variants = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0, transition: { duration: 0.4 } },
};

const stagger: Variants = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.08 } },
};

function InputCard({ title, icon: Icon, children }: { title: string; icon: React.ElementType; children: React.ReactNode }) {
  return (
    <motion.div variants={fadeIn} className="glass-card p-6">
      <div className="flex items-center gap-3 mb-5">
        <div className="w-9 h-9 rounded-xl bg-brand-500/20 border border-brand-400/30 flex items-center justify-center">
          <Icon className="w-5 h-5 text-brand-300" />
        </div>
        <h3 className="text-lg font-semibold text-white">{title}</h3>
      </div>
      {children}
    </motion.div>
  );
}

function Field({
  label, type = "text", value, onChange, suffix, placeholder, min, max, step,
}: {
  label: string; type?: string; value: string | number; onChange: (v: string) => void;
  suffix?: string; placeholder?: string; min?: number; max?: number; step?: number;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-xs font-medium text-brand-300">{label}</label>
      <div className="relative">
        <input
          type={type}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          min={min}
          max={max}
          step={step}
          className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white placeholder:text-brand-400/50 focus:outline-none focus:ring-2 focus:ring-brand-400/40 focus:border-brand-400/40 transition-all"
        />
        {suffix && <span className="absolute right-4 top-1/2 -translate-y-1/2 text-xs text-brand-400">{suffix}</span>}
      </div>
    </div>
  );
}

function Select({
  label, value, onChange, options,
}: {
  label: string; value: string; onChange: (v: string) => void;
  options: { value: string; label: string }[];
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-xs font-medium text-brand-300">{label}</label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:ring-2 focus:ring-brand-400/40 focus:border-brand-400/40 transition-all appearance-none"
      >
        {options.map((o) => (
          <option key={o.value} value={o.value} className="bg-brand-950 text-white">{o.label}</option>
        ))}
      </select>
    </div>
  );
}

export default function Dashboard() {
  const [phase, setPhase] = useState<Phase>("input");
  const [analysisStep, setAnalysisStep] = useState(0);
  const [result, setResult] = useState<AnalysisResult | null>(null);

  // Form state
  const [name, setName] = useState("Rahul");
  const [age, setAge] = useState("28");
  const [salary, setSalary] = useState("75000");
  const [monthlySavings, setMonthlySavings] = useState("20000");
  const [currentSIP, setCurrentSIP] = useState("8000");
  const [portfolioValue, setPortfolioValue] = useState("200000");
  const [equityPercent, setEquityPercent] = useState("75");
  const [stocks, setStocks] = useState("RELIANCE.NS, HDFCBANK.NS, TCS.NS");
  const [mfCount, setMfCount] = useState("3");
  const [dependents, setDependents] = useState("1");
  const [emergencyMonths, setEmergencyMonths] = useState("3");
  const [dtiRatio, setDtiRatio] = useState("20");
  const [experience, setExperience] = useState("intermediate");
  const [goals, setGoals] = useState<{ type: Goal["type"]; label: string; target: string; years: string }[]>([
    { type: "house", label: "House", target: "2000000", years: "5" },
    { type: "retirement", label: "Retirement", target: "50000000", years: "25" },
  ]);

  const addGoal = () => {
    setGoals([...goals, { type: "wealth", label: "Wealth Building", target: "1000000", years: "10" }]);
  };

  const removeGoal = (i: number) => {
    setGoals(goals.filter((_, idx) => idx !== i));
  };

  const updateGoal = (i: number, field: string, value: string) => {
    const updated = [...goals];
    if (field === "type") {
      const gt = GOAL_TYPES.find((g) => g.value === value);
      updated[i] = { ...updated[i], type: value as Goal["type"], label: gt?.label.slice(2).trim() || value };
    } else {
      (updated[i] as Record<string, string>)[field] = value;
    }
    setGoals(updated);
  };

  const handleAnalyze = () => {
    setPhase("analyzing");
    setAnalysisStep(0);

    // Animate through analysis steps
    ANALYSIS_STEPS.forEach((_, i) => {
      setTimeout(() => setAnalysisStep(i + 1), (i + 1) * 400);
    });

    // Run actual analysis after animation
    setTimeout(() => {
      const input: UserInput = {
        name,
        age: parseInt(age) || 28,
        salary: parseInt(salary) || 50000,
        monthlySavings: parseInt(monthlySavings) || 10000,
        currentSIP: parseInt(currentSIP) || 5000,
        portfolioValue: parseInt(portfolioValue) || 0,
        equityPercent: parseInt(equityPercent) || 50,
        stocksHeld: stocks.split(",").map((s) => s.trim()).filter(Boolean),
        mutualFundCount: parseInt(mfCount) || 0,
        dependents: parseInt(dependents) || 0,
        emergencyFundMonths: parseInt(emergencyMonths) || 0,
        debtToIncome: parseInt(dtiRatio) || 0,
        experience: experience as UserInput["experience"],
        goals: goals.map((g) => ({
          type: g.type,
          label: g.label,
          targetAmount: parseInt(g.target) || 0,
          years: parseInt(g.years) || 10,
        })),
      };

      const analysisResult = runAnalysis(input);
      setResult(analysisResult);
      setPhase("results");
    }, ANALYSIS_STEPS.length * 400 + 800);
  };

  return (
    <div className="relative min-h-screen text-foreground overflow-hidden bg-brand-950">
      {/* Background */}
      <div className="absolute inset-0 z-0 pointer-events-none">
        <div className="absolute inset-0 math-grid opacity-[0.2]" style={{ maskImage: "linear-gradient(to bottom, black 0%, transparent 100%)", WebkitMaskImage: "linear-gradient(to bottom, black 0%, transparent 100%)" }} />
        <div className="absolute top-[-10%] right-[-5%] w-[50vw] h-[50vw] max-w-[600px] max-h-[600px] bg-brand-400/15 rounded-full blur-[140px] mix-blend-screen" />
        <div className="absolute bottom-[-10%] left-[-5%] w-[50vw] h-[50vw] max-w-[600px] max-h-[600px] bg-accent/10 rounded-full blur-[160px] mix-blend-screen" />
      </div>

      {/* Top Nav */}
      <nav className="relative z-20 w-full px-6 md:px-10 py-5 flex items-center justify-between border-b border-white/5 bg-black/20 backdrop-blur-xl">
        <Link href="/" className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-brand-400 to-brand-600 flex items-center justify-center">
            <Sparkles className="w-4 h-4 text-white" />
          </div>
          <span className="font-semibold text-lg text-white">InvestAI</span>
        </Link>
        {phase === "results" && (
          <button
            onClick={() => { setPhase("input"); setResult(null); }}
            className="flex items-center gap-2 text-sm text-brand-300 hover:text-white transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            New Analysis
          </button>
        )}
      </nav>

      {/* Main Content */}
      <main className="relative z-10 max-w-5xl mx-auto px-4 py-10">
        <AnimatePresence mode="wait">

          {/* ─── INPUT PHASE ──────────────────────────────────────────────── */}
          {phase === "input" && (
            <motion.div key="input" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0, x: -50 }} transition={{ duration: 0.3 }}>
              <motion.div variants={stagger} initial="hidden" animate="show">
                {/* Header */}
                <motion.div variants={fadeIn} className="text-center mb-10">
                  <h1 className="text-3xl md:text-4xl font-bold text-white mb-3">
                    Financial Health <span className="text-platinum-gradient">Analysis</span>
                  </h1>
                  <p className="text-brand-300 text-sm max-w-lg mx-auto">
                    Fill in your financial details below and let our AI engine analyze your complete financial picture — from risk profile to SIP plans, stock signals, and rebalancing.
                  </p>
                </motion.div>

                <div className="space-y-6">
                  {/* Personal Info */}
                  <InputCard title="Personal Information" icon={User}>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <Field label="Full Name" value={name} onChange={setName} placeholder="e.g. Rahul" />
                      <Field label="Age" type="number" value={age} onChange={setAge} suffix="years" min={18} max={100} />
                    </div>
                  </InputCard>

                  {/* Income & Savings */}
                  <InputCard title="Income & Savings" icon={Briefcase}>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      <Field label="Monthly Salary" type="number" value={salary} onChange={setSalary} suffix="INR/mo" />
                      <Field label="Monthly Savings" type="number" value={monthlySavings} onChange={setMonthlySavings} suffix="INR/mo" />
                      <Field label="Current SIP" type="number" value={currentSIP} onChange={setCurrentSIP} suffix="INR/mo" />
                    </div>
                  </InputCard>

                  {/* Portfolio */}
                  <InputCard title="Portfolio" icon={PiggyBank}>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                      <Field label="Total Portfolio Value" type="number" value={portfolioValue} onChange={setPortfolioValue} suffix="INR" />
                      <Field label="Equity Percentage" type="number" value={equityPercent} onChange={setEquityPercent} suffix="%" min={0} max={100} />
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <Field label="Stocks Held (comma separated)" value={stocks} onChange={setStocks} placeholder="RELIANCE.NS, TCS.NS" />
                      <Field label="Mutual Fund Count" type="number" value={mfCount} onChange={setMfCount} min={0} />
                    </div>
                  </InputCard>

                  {/* Risk Factors */}
                  <InputCard title="Risk Factors" icon={ShieldCheck}>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                      <Field label="Dependents" type="number" value={dependents} onChange={setDependents} min={0} />
                      <Field label="Emergency Fund" type="number" value={emergencyMonths} onChange={setEmergencyMonths} suffix="months" min={0} />
                      <Field label="Debt-to-Income" type="number" value={dtiRatio} onChange={setDtiRatio} suffix="%" min={0} max={100} />
                      <Select
                        label="Experience Level"
                        value={experience}
                        onChange={setExperience}
                        options={[
                          { value: "beginner", label: "Beginner" },
                          { value: "intermediate", label: "Intermediate" },
                          { value: "expert", label: "Expert" },
                        ]}
                      />
                    </div>
                  </InputCard>

                  {/* Financial Goals */}
                  <InputCard title="Financial Goals" icon={Target}>
                    <div className="space-y-4">
                      {goals.map((goal, i) => (
                        <div key={i} className="p-4 rounded-xl bg-white/5 border border-white/5 relative group">
                          {goals.length > 1 && (
                            <button
                              onClick={() => removeGoal(i)}
                              className="absolute top-3 right-3 p-1.5 rounded-lg bg-red-500/10 text-red-400 opacity-0 group-hover:opacity-100 transition-opacity hover:bg-red-500/20"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          )}
                          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                            <Select
                              label="Goal Type"
                              value={goal.type}
                              onChange={(v) => updateGoal(i, "type", v)}
                              options={GOAL_TYPES.map((g) => ({ value: g.value, label: g.label }))}
                            />
                            <Field label="Goal Name" value={goal.label} onChange={(v) => updateGoal(i, "label", v)} />
                            <Field label="Target Amount" type="number" value={goal.target} onChange={(v) => updateGoal(i, "target", v)} suffix="INR" />
                            <Field label="Time Horizon" type="number" value={goal.years} onChange={(v) => updateGoal(i, "years", v)} suffix="years" min={1} max={50} />
                          </div>
                        </div>
                      ))}
                      <button
                        onClick={addGoal}
                        className="w-full p-3 rounded-xl border-2 border-dashed border-white/10 text-brand-300 text-sm flex items-center justify-center gap-2 hover:border-brand-400/40 hover:text-white transition-all"
                      >
                        <Plus className="w-4 h-4" />
                        Add Another Goal
                      </button>
                    </div>
                  </InputCard>

                  {/* Analyze Button */}
                  <motion.div variants={fadeIn} className="flex justify-center pt-4 pb-8">
                    <button
                      onClick={handleAnalyze}
                      className="group relative px-12 py-5 rounded-2xl bg-gradient-to-r from-brand-600 to-brand-400 text-white font-bold text-lg shadow-2xl shadow-brand-500/30 hover:shadow-brand-500/50 hover:scale-[1.02] transition-all duration-300 flex items-center gap-3 border border-brand-400/30"
                    >
                      <Sparkles className="w-6 h-6 group-hover:rotate-12 transition-transform" />
                      AI Analyze
                      <div className="absolute inset-0 rounded-2xl bg-white/10 opacity-0 group-hover:opacity-100 transition-opacity" />
                    </button>
                  </motion.div>
                </div>
              </motion.div>
            </motion.div>
          )}

          {/* ─── ANALYZING PHASE ──────────────────────────────────────────── */}
          {phase === "analyzing" && (
            <motion.div
              key="analyzing"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="flex flex-col items-center justify-center min-h-[60vh]"
            >
              <div className="glass-card p-10 max-w-lg w-full text-center">
                <div className="relative w-20 h-20 mx-auto mb-8">
                  <Loader2 className="w-20 h-20 text-brand-400 animate-spin" />
                  <div className="absolute inset-0 flex items-center justify-center">
                    <Sparkles className="w-8 h-8 text-brand-300" />
                  </div>
                </div>
                <h2 className="text-2xl font-bold text-white mb-2">Analyzing Your Finances</h2>
                <p className="text-brand-300 text-sm mb-8">Our AI engine is processing your financial data...</p>
                <div className="space-y-3 text-left">
                  {ANALYSIS_STEPS.map((step, i) => (
                    <div key={i} className={`flex items-center gap-3 text-sm transition-all duration-300 ${i < analysisStep ? "opacity-100" : "opacity-20"}`}>
                      <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold shrink-0 ${
                        i < analysisStep ? "bg-emerald-500/20 text-emerald-300" : "bg-white/5 text-brand-400"
                      }`}>
                        {i < analysisStep ? "✓" : i + 1}
                      </div>
                      <span className={i < analysisStep ? "text-brand-200" : "text-brand-400"}>{step}</span>
                    </div>
                  ))}
                </div>
              </div>
            </motion.div>
          )}

          {/* ─── RESULTS PHASE ────────────────────────────────────────────── */}
          {phase === "results" && result && (
            <motion.div
              key="results"
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5 }}
            >
              <div className="text-center mb-10">
                <h1 className="text-3xl font-bold text-white mb-2">
                  Analysis Complete for <span className="text-platinum-gradient">{result.input.name}</span>
                </h1>
                <p className="text-brand-300 text-sm">
                  {result.input.age} years · ₹{result.input.salary.toLocaleString("en-IN")}/mo salary · {result.input.goals.length} goal(s)
                </p>
              </div>
              <AnalysisResults result={result} />
            </motion.div>
          )}

        </AnimatePresence>
      </main>
    </div>
  );
}
