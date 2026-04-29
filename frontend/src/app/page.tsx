"use client";

import { motion, useScroll, useTransform, useSpring } from "framer-motion";
import { ArrowRight, BarChart3, TrendingUp, Shield, Activity, Sparkles, Server, Zap, Database, Terminal, Code } from "lucide-react";
import Link from "next/link";
import { useRef } from "react";

export default function Home() {
  const containerRef = useRef<HTMLDivElement>(null);
  
  // Smooth scroll progress
  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ["start start", "end end"]
  });

  const smoothProgress = useSpring(scrollYProgress, {
    stiffness: 100,
    damping: 30,
    restDelta: 0.001
  });

  // Hero Section Transforms
  const heroScale = useTransform(smoothProgress, [0, 0.2], [1, 0.8]);
  const heroRotateX = useTransform(smoothProgress, [0, 0.2], [0, 25]);
  const heroOpacity = useTransform(smoothProgress, [0, 0.15], [1, 0]);
  const heroY = useTransform(smoothProgress, [0, 0.2], [0, -100]);

  // Features Section Transforms
  const featuresScale = useTransform(smoothProgress, [0.1, 0.3, 0.5], [0.8, 1, 0.8]);
  const featuresRotateX = useTransform(smoothProgress, [0.1, 0.3, 0.5], [-25, 0, 25]);
  const featuresOpacity = useTransform(smoothProgress, [0.1, 0.2, 0.4, 0.5], [0, 1, 1, 0]);
  const featuresY = useTransform(smoothProgress, [0.1, 0.3, 0.5], [100, 0, -100]);

  // Backend/Engine Section Transforms
  const engineScale = useTransform(smoothProgress, [0.4, 0.6, 0.8], [0.8, 1, 0.8]);
  const engineRotateX = useTransform(smoothProgress, [0.4, 0.6, 0.8], [-25, 0, 25]);
  const engineOpacity = useTransform(smoothProgress, [0.4, 0.5, 0.7, 0.8], [0, 1, 1, 0]);
  const engineY = useTransform(smoothProgress, [0.4, 0.6, 0.8], [100, 0, -100]);

  // CTA Section Transforms
  const ctaScale = useTransform(smoothProgress, [0.7, 0.9], [0.8, 1]);
  const ctaRotateX = useTransform(smoothProgress, [0.7, 0.9], [-25, 0]);
  const ctaOpacity = useTransform(smoothProgress, [0.7, 0.8], [0, 1]);
  const ctaY = useTransform(smoothProgress, [0.7, 0.9], [100, 0]);

  // Background Parallax
  const bgY = useTransform(smoothProgress, [0, 1], ["0%", "50%"]);

  return (
    <div ref={containerRef} className="relative h-[400vh] bg-[#0c0c16] text-white">
      {/* Navbar - Fixed */}
      <nav className="fixed top-0 w-full z-50 px-6 md:px-12 py-6 flex items-center justify-between border-b border-white/5 bg-[#0c0c16]/50 backdrop-blur-xl">
        <div className="flex items-center gap-2">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-brand-400 to-brand-600 flex items-center justify-center shadow-lg shadow-brand-500/20 border border-brand-400/30">
            <Sparkles className="w-5 h-5 text-white" />
          </div>
          <span className="font-semibold text-xl tracking-tight text-white ml-1">InvestAI</span>
        </div>
        <div className="hidden md:flex items-center gap-8 text-sm font-medium text-brand-200">
          <span className="cursor-pointer hover:text-white transition-colors">Platform</span>
          <span className="cursor-pointer hover:text-white transition-colors">Engine</span>
          <span className="cursor-pointer hover:text-white transition-colors">API</span>
        </div>
        <div className="flex items-center gap-4">
          <Link href="/dashboard" className="glass-button-primary text-sm py-2 px-6">Launch App</Link>
        </div>
      </nav>

      {/* Global Animated Background */}
      <motion.div style={{ y: bgY }} className="fixed inset-0 z-0 pointer-events-none">
        <div className="absolute inset-0 math-grid opacity-[0.2]" style={{ maskImage: 'linear-gradient(to bottom, black 0%, transparent 100%)', WebkitMaskImage: 'linear-gradient(to bottom, black 0%, transparent 100%)' }}></div>
        <div className="absolute top-[20%] left-[10%] w-[40vw] h-[40vw] bg-brand-500/20 rounded-full blur-[120px] mix-blend-screen" />
        <div className="absolute top-[60%] right-[10%] w-[50vw] h-[50vw] bg-accent/15 rounded-full blur-[150px] mix-blend-screen" />
      </motion.div>

      {/* 3D Sticky Container */}
      <div className="sticky top-0 h-screen w-full overflow-hidden flex items-center justify-center perspective-[1200px]">
        
        {/* SECTION 1: HERO */}
        <motion.div 
          style={{ scale: heroScale, rotateX: heroRotateX, opacity: heroOpacity, y: heroY }}
          className="absolute w-full max-w-5xl px-6 flex flex-col items-center text-center [transform-style:preserve-3d] origin-bottom"
        >
          <div className="inline-flex items-center gap-3 px-4 py-2 rounded-full border border-white/10 bg-white/5 backdrop-blur-md mb-8 shadow-2xl">
            <span className="w-2 h-2 rounded-full bg-brand-400 animate-pulse"></span>
            <span className="text-sm font-medium text-brand-200">System Online • Python Engine v4.0</span>
          </div>
          
          <h1 className="text-6xl md:text-8xl font-bold tracking-tighter mb-8 leading-[1.1] drop-shadow-2xl">
            Financial decisions, <br className="hidden md:block"/>
            <span className="text-platinum-gradient">computed in 3D.</span>
          </h1>
          
          <p className="text-xl text-brand-200 mb-10 max-w-2xl font-light">
            Scroll to dive into the architecture. Front-end elegance meets back-end processing power for predictive wealth management.
          </p>

          <div className="flex items-center gap-4">
            <div className="animate-bounce mt-12 p-4 rounded-full bg-white/5 border border-white/10 backdrop-blur-sm">
              <ArrowRight className="w-6 h-6 rotate-90" />
            </div>
          </div>
        </motion.div>

        {/* SECTION 2: FRONT-END FEATURES */}
        <motion.div 
          style={{ scale: featuresScale, rotateX: featuresRotateX, opacity: featuresOpacity, y: featuresY }}
          className="absolute w-full max-w-6xl px-6 flex flex-col items-center [transform-style:preserve-3d] origin-center pointer-events-none"
        >
          <div className="text-center mb-16">
            <h2 className="text-4xl md:text-6xl font-bold mb-4">Interactive <span className="text-brand-400">Dashboards</span></h2>
            <p className="text-xl text-brand-200">React + Next.js rendering real-time portfolio insights.</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 w-full pointer-events-auto">
            <div className="glass-card p-8 group translate-z-50 shadow-2xl shadow-brand-900/50">
              <div className="w-14 h-14 rounded-2xl bg-brand-500/20 border border-brand-400/30 flex items-center justify-center mb-6">
                 <TrendingUp className="w-7 h-7 text-brand-300" />
              </div>
              <h3 className="text-2xl font-semibold mb-3">Live Tracking</h3>
              <p className="text-brand-200 font-light leading-relaxed">
                Watch your assets grow with real-time websocket connections and smooth 60fps chart rendering.
              </p>
            </div>
            
            <div className="glass-card p-8 group translate-z-50 shadow-2xl shadow-brand-900/50">
              <div className="w-14 h-14 rounded-2xl bg-brand-500/20 border border-brand-400/30 flex items-center justify-center mb-6">
                 <Shield className="w-7 h-7 text-brand-300" />
              </div>
              <h3 className="text-2xl font-semibold mb-3">Risk UI</h3>
              <p className="text-brand-200 font-light leading-relaxed">
                Visual drift analysis and immediate alert notifications pushed directly to your interface.
              </p>
            </div>

            <div className="glass-card p-8 group translate-z-50 shadow-2xl shadow-brand-900/50">
              <div className="w-14 h-14 rounded-2xl bg-brand-500/20 border border-brand-400/30 flex items-center justify-center mb-6">
                 <BarChart3 className="w-7 h-7 text-brand-300" />
              </div>
              <h3 className="text-2xl font-semibold mb-3">Rebalancing</h3>
              <p className="text-brand-200 font-light leading-relaxed">
                One-click portfolio restructuring with visual diffs of your current vs target allocations.
              </p>
            </div>
          </div>
        </motion.div>

        {/* SECTION 3: BACK-END / ENGINE */}
        <motion.div 
          style={{ scale: engineScale, rotateX: engineRotateX, opacity: engineOpacity, y: engineY }}
          className="absolute w-full max-w-6xl px-6 flex flex-col md:flex-row items-center gap-12 [transform-style:preserve-3d] origin-center pointer-events-none"
        >
          <div className="flex-1 pointer-events-auto">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-md bg-accent/20 text-accent-light border border-accent/30 text-sm font-mono mb-6">
              <Terminal className="w-4 h-4" /> main.py api --port 8000
            </div>
            <h2 className="text-4xl md:text-6xl font-bold mb-6">Powered by a <br/><span className="text-accent-light">Python Core</span></h2>
            <p className="text-xl text-brand-200 font-light mb-8">
              Underneath the beautiful UI lies a robust FastAPI backend. It processes ML models, SIP calculations, and technical signals in milliseconds.
            </p>
            
            <ul className="space-y-4">
              <li className="flex items-center gap-3 text-lg bg-white/5 p-4 rounded-xl border border-white/5">
                <Database className="w-6 h-6 text-brand-400" />
                <span><strong className="text-white">Fund Database:</strong> Instant access to thousands of mutual funds.</span>
              </li>
              <li className="flex items-center gap-3 text-lg bg-white/5 p-4 rounded-xl border border-white/5">
                <Zap className="w-6 h-6 text-brand-400" />
                <span><strong className="text-white">ML Signals:</strong> Buy/sell indicators calculated in real-time.</span>
              </li>
              <li className="flex items-center gap-3 text-lg bg-white/5 p-4 rounded-xl border border-white/5">
                <Server className="w-6 h-6 text-brand-400" />
                <span><strong className="text-white">Watchdog:</strong> 24/7 background process for portfolio monitoring.</span>
              </li>
            </ul>
          </div>
          
          <div className="flex-1 w-full pointer-events-auto relative">
            <div className="absolute inset-0 bg-gradient-to-tr from-accent/20 to-brand-500/20 blur-3xl rounded-full"></div>
            <div className="glass-card p-6 font-mono text-sm md:text-base leading-relaxed relative z-10 border-brand-500/30">
              <div className="flex gap-2 mb-4 border-b border-white/10 pb-4">
                <div className="w-3 h-3 rounded-full bg-red-500"></div>
                <div className="w-3 h-3 rounded-full bg-yellow-500"></div>
                <div className="w-3 h-3 rounded-full bg-green-500"></div>
              </div>
              <div className="text-brand-300">
                <span className="text-pink-400">@app.get</span>(<span className="text-green-300">"/api/v1/score/{'{ticker}'}"</span>)<br/>
                <span className="text-blue-400">def</span> <span className="text-yellow-200">get_stock_score</span>(ticker: <span className="text-teal-300">str</span>):<br/>
                &nbsp;&nbsp;&nbsp;&nbsp;result = score_stock(ticker)<br/>
                &nbsp;&nbsp;&nbsp;&nbsp;<span className="text-pink-400">return</span> {'{'}<br/>
                &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span className="text-green-300">"status"</span>: <span className="text-green-300">"success"</span>,<br/>
                &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span className="text-green-300">"score"</span>: result[<span className="text-green-300">'score'</span>],<br/>
                &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span className="text-green-300">"grade"</span>: result[<span className="text-green-300">'grade'</span>],<br/>
                &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span className="text-green-300">"action"</span>: result[<span className="text-green-300">'recommendation'</span>]<br/>
                &nbsp;&nbsp;&nbsp;&nbsp;{'}'}
              </div>
            </div>
          </div>
        </motion.div>

        {/* SECTION 4: CTA */}
        <motion.div 
          style={{ scale: ctaScale, rotateX: ctaRotateX, opacity: ctaOpacity, y: ctaY }}
          className="absolute w-full max-w-4xl px-6 flex flex-col items-center text-center [transform-style:preserve-3d] origin-bottom pointer-events-none"
        >
          <div className="w-20 h-20 bg-gradient-to-br from-brand-400 to-brand-600 rounded-2xl flex items-center justify-center mb-8 shadow-[0_0_50px_rgba(109,92,208,0.5)] border border-white/20">
            <Code className="w-10 h-10 text-white" />
          </div>
          <h2 className="text-5xl md:text-7xl font-bold mb-6">Ready to run?</h2>
          <p className="text-xl text-brand-200 mb-10 max-w-2xl font-light">
            Start both the Next.js frontend and FastAPI backend using the included Makefile or run script.
          </p>
          <div className="flex items-center gap-4 pointer-events-auto">
            <Link href="/dashboard" className="glass-button-primary text-lg px-8 py-4 flex items-center gap-2 group">
              Access Dashboard <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
            </Link>
          </div>
          <div className="mt-8 font-mono text-sm text-brand-300/70 bg-black/50 py-2 px-6 rounded-full border border-white/5">
            make dev
          </div>
        </motion.div>

      </div>
    </div>
  );
}
