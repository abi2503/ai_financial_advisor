'use client'
import { useState } from 'react'
import Navbar from '@/components/Navbar'
import { Calculator, Brain, TrendingUp, Loader2, AlertCircle, CheckCircle } from 'lucide-react'
import axios from 'axios'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import {
  PieChart, Pie, Cell, Tooltip,
  ResponsiveContainer, Legend
} from 'recharts'

interface RetirementResult {
  projectedTotal:  number
  annualIncome:    number
  monthlyIncome:   number
  years:           number
  onTrack:         boolean
  gapPct:          number
  allocation:      { stocks: number, bonds: number, cash: number, description: string }
  aiAdvice:        string
}

const ALLOCATION_COLORS = ['#3b82f6', '#8b5cf6', '#6b7280']

export default function RetirementPage() {
  const [currentAge,           setCurrentAge]           = useState('30')
  const [retirementAge,        setRetirementAge]        = useState('65')
  const [currentSavings,       setCurrentSavings]       = useState('50000')
  const [monthlyContribution,  setMonthlyContribution]  = useState('1000')
  const [expectedReturn,       setExpectedReturn]       = useState('7')
  const [riskTolerance,        setRiskTolerance]        = useState('moderate')
  const [retirementGoal,       setRetirementGoal]       = useState('')
  const [loading,              setLoading]              = useState(false)
  const [result,               setResult]               = useState<RetirementResult | null>(null)
  const [error,                setError]                = useState('')

  async function handleCalculate() {
    setLoading(true)
    setError('')
    try {
      const res = await axios.post('/api/retirement', {
        currentAge:          parseInt(currentAge),
        retirementAge:       parseInt(retirementAge),
        currentSavings:      parseFloat(currentSavings),
        monthlyContribution: parseFloat(monthlyContribution),
        expectedReturn:      parseFloat(expectedReturn),
        riskTolerance,
        retirementGoal:      retirementGoal ? parseFloat(retirementGoal) : null,
      })
      setResult(res.data)
    } catch (err: any) {
      setError('Failed to calculate. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const allocationData = result ? [
    { name: 'Stocks', value: result.allocation.stocks },
    { name: 'Bonds',  value: result.allocation.bonds },
    { name: 'Cash',   value: result.allocation.cash },
  ] : []

  return (
    <div className="min-h-screen bg-gray-950">
      <Navbar />
      <main className="max-w-6xl mx-auto px-6 py-8">

        <div className="mb-8">
          <h1 className="text-2xl font-bold text-white">Retirement Planner</h1>
          <p className="text-gray-400 mt-1">
            Plan your retirement with AI-powered projections and personalized advice
          </p>
        </div>

        <div className="grid grid-cols-2 gap-8">

          {/* Left — Calculator Form */}
          <div className="space-y-6">
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
              <div className="flex items-center gap-2 mb-5">
                <Calculator className="text-blue-400" size={20} />
                <h2 className="font-semibold text-white">Your Details</h2>
              </div>

              <div className="space-y-4">
                {/* Age inputs */}
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-xs text-gray-500 mb-1.5 block">
                      Current Age
                    </label>
                    <input
                      type="number"
                      value={currentAge}
                      onChange={e => setCurrentAge(e.target.value)}
                      min="18" max="80"
                      className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 text-white text-sm focus:outline-none focus:border-blue-500"
                    />
                  </div>
                  <div>
                    <label className="text-xs text-gray-500 mb-1.5 block">
                      Retirement Age
                    </label>
                    <input
                      type="number"
                      value={retirementAge}
                      onChange={e => setRetirementAge(e.target.value)}
                      min="40" max="90"
                      className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 text-white text-sm focus:outline-none focus:border-blue-500"
                    />
                  </div>
                </div>

                {/* Savings */}
                <div>
                  <label className="text-xs text-gray-500 mb-1.5 block">
                    Current Savings ($)
                  </label>
                  <input
                    type="number"
                    value={currentSavings}
                    onChange={e => setCurrentSavings(e.target.value)}
                    min="0"
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 text-white text-sm focus:outline-none focus:border-blue-500"
                  />
                </div>

                {/* Monthly contribution */}
                <div>
                  <label className="text-xs text-gray-500 mb-1.5 block">
                    Monthly Contribution ($)
                  </label>
                  <input
                    type="number"
                    value={monthlyContribution}
                    onChange={e => setMonthlyContribution(e.target.value)}
                    min="0"
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 text-white text-sm focus:outline-none focus:border-blue-500"
                  />
                </div>

                {/* Expected return */}
                <div>
                  <label className="text-xs text-gray-500 mb-1.5 block">
                    Expected Annual Return (%) — S&P 500 avg: 7%
                  </label>
                  <input
                    type="number"
                    value={expectedReturn}
                    onChange={e => setExpectedReturn(e.target.value)}
                    min="1" max="20" step="0.5"
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 text-white text-sm focus:outline-none focus:border-blue-500"
                  />
                </div>

                {/* Risk tolerance */}
                <div>
                  <label className="text-xs text-gray-500 mb-1.5 block">
                    Risk Tolerance
                  </label>
                  <div className="grid grid-cols-3 gap-2">
                    {['conservative', 'moderate', 'aggressive'].map(risk => (
                      <button
                        key={risk}
                        onClick={() => setRiskTolerance(risk)}
                        className={`py-2.5 rounded-lg text-xs font-medium transition capitalize ${
                          riskTolerance === risk
                            ? risk === 'conservative'
                              ? 'bg-green-600 text-white'
                              : risk === 'moderate'
                                ? 'bg-blue-600 text-white'
                                : 'bg-red-600 text-white'
                            : 'bg-gray-800 text-gray-400 hover:text-white'
                        }`}
                      >
                        {risk}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Retirement goal (optional) */}
                <div>
                  <label className="text-xs text-gray-500 mb-1.5 block">
                    Retirement Goal ($) — optional
                  </label>
                  <input
                    type="number"
                    value={retirementGoal}
                    onChange={e => setRetirementGoal(e.target.value)}
                    placeholder="e.g. 2000000"
                    min="0"
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 text-white text-sm placeholder-gray-600 focus:outline-none focus:border-blue-500"
                  />
                </div>

                {error && (
                  <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-sm">
                    {error}
                  </div>
                )}

                <button
                  onClick={handleCalculate}
                  disabled={loading}
                  className="w-full py-3 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 rounded-lg text-white text-sm font-medium transition flex items-center justify-center gap-2"
                >
                  {loading ? (
                    <>
                      <Loader2 size={16} className="animate-spin" />
                      Alex is analyzing... (30-60 seconds)
                    </>
                  ) : (
                    <>
                      <Brain size={16} />
                      Calculate + Get AI Advice
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>

          {/* Right — Results */}
          <div className="space-y-6">
            {!result && !loading && (
              <div className="bg-gray-900 border border-gray-800 rounded-xl p-8 flex items-center justify-center h-full">
                <div className="text-center">
                  <TrendingUp size={32} className="mx-auto mb-3 text-gray-600" />
                  <p className="text-gray-500 text-sm">
                    Fill in your details and click Calculate
                  </p>
                  <p className="text-gray-600 text-xs mt-1">
                    Alex will project your retirement savings and provide personalized advice
                  </p>
                </div>
              </div>
            )}

            {loading && (
              <div className="bg-gray-900 border border-gray-800 rounded-xl p-8 flex items-center justify-center">
                <div className="text-center">
                  <Loader2 size={32} className="animate-spin text-blue-400 mx-auto mb-3" />
                  <p className="text-gray-400 text-sm">
                    Calculating projections...
                  </p>
                  <p className="text-gray-600 text-xs mt-1">
                    Alex is generating personalized advice
                  </p>
                </div>
              </div>
            )}

            {result && !loading && (
              <>
                {/* Projection Summary */}
                <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
                  <div className="flex items-center justify-between mb-4">
                    <h2 className="font-semibold text-white">
                      Retirement Projection
                    </h2>
                    {result.onTrack ? (
                      <div className="flex items-center gap-1 text-green-400 text-xs">
                        <CheckCircle size={14} />
                        On Track
                      </div>
                    ) : (
                      <div className="flex items-center gap-1 text-yellow-400 text-xs">
                        <AlertCircle size={14} />
                        Needs Attention
                      </div>
                    )}
                  </div>

                  <div className="grid grid-cols-2 gap-4 mb-4">
                    <div className="bg-gray-800 rounded-xl p-4">
                      <div className="text-gray-500 text-xs mb-1">
                        Projected at {result.inputs?.retirementAge}
                      </div>
                      <div className="text-2xl font-bold text-white">
                        ${result.projectedTotal.toLocaleString('en-US')}
                      </div>
                      <div className="text-gray-500 text-xs mt-1">
                        in {result.years} years
                      </div>
                    </div>
                    <div className="bg-gray-800 rounded-xl p-4">
                      <div className="text-gray-500 text-xs mb-1">
                        Monthly Income (4% rule)
                      </div>
                      <div className="text-2xl font-bold text-green-400">
                        ${result.monthlyIncome.toLocaleString('en-US')}
                      </div>
                      <div className="text-gray-500 text-xs mt-1">
                        ${result.annualIncome.toLocaleString('en-US')}/year
                      </div>
                    </div>
                  </div>

                  {result.gapPct !== 0 && retirementGoal && (
                    <div className={`p-3 rounded-lg text-xs ${
                      result.onTrack
                        ? 'bg-green-500/10 border border-green-500/20 text-green-400'
                        : 'bg-yellow-500/10 border border-yellow-500/20 text-yellow-400'
                    }`}>
                      {result.onTrack
                        ? `You are ${Math.abs(result.gapPct)}% above your retirement goal`
                        : `You are ${Math.abs(result.gapPct)}% below your retirement goal`
                      }
                    </div>
                  )}
                </div>

                {/* Asset Allocation */}
                <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
                  <h2 className="font-semibold text-white mb-1">
                    Recommended Allocation
                  </h2>
                  <p className="text-gray-500 text-xs mb-4 capitalize">
                    {riskTolerance} — {result.allocation.description}
                  </p>
                  <div className="flex items-center gap-6">
                    <ResponsiveContainer width={140} height={140}>
                      <PieChart>
                        <Pie
                          data={allocationData}
                          cx="50%"
                          cy="50%"
                          innerRadius={40}
                          outerRadius={65}
                          paddingAngle={3}
                          dataKey="value"
                        >
                          {allocationData.map((entry, index) => (
                            <Cell
                              key={entry.name}
                              fill={ALLOCATION_COLORS[index]}
                            />
                          ))}
                        </Pie>
                        <Tooltip
                          formatter={(value: any) => [`${value}%`, '']}
                        />
                      </PieChart>
                    </ResponsiveContainer>
                    <div className="space-y-2 flex-1">
                      {allocationData.map((item, i) => (
                        <div key={item.name} className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <div
                              className="w-3 h-3 rounded-full"
                              style={{ backgroundColor: ALLOCATION_COLORS[i] }}
                            />
                            <span className="text-gray-300 text-sm">{item.name}</span>
                          </div>
                          <span className="text-white font-medium text-sm">
                            {item.value}%
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>

                {/* AI Advice */}
                {result.aiAdvice && (
                  <div className="bg-gray-900 border border-blue-500/20 rounded-xl p-6">
                    <div className="flex items-center gap-2 mb-4">
                      <Brain className="text-blue-400" size={18} />
                      <h2 className="font-semibold text-white">
                        Alex's Personalized Advice
                      </h2>
                    </div>
                    <div className="text-sm text-gray-300 leading-relaxed">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {result.aiAdvice}
                      </ReactMarkdown>
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        </div>

      </main>
    </div>
  )
}