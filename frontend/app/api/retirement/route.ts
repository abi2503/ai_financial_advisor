import { auth } from '@clerk/nextjs/server'
import { NextRequest, NextResponse } from 'next/server'
import { getEcsUrl } from '@/lib/config'

export async function POST(req: NextRequest) {
  try {
    const { userId } = await auth()
    if (!userId) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const {
      currentAge,
      retirementAge,
      currentSavings,
      monthlyContribution,
      expectedReturn,
      riskTolerance,
      retirementGoal,
      currentPortfolioValue
    } = await req.json()

    // Calculate projections server-side
    const years         = retirementAge - currentAge
    const monthlyReturn = expectedReturn / 100 / 12
    const months        = years * 12

    // Future value formula
    const fvSavings      = currentSavings * Math.pow(1 + monthlyReturn, months)
    const fvContributions = monthlyContribution *
      ((Math.pow(1 + monthlyReturn, months) - 1) / monthlyReturn)
    const projectedTotal  = fvSavings + fvContributions

    // Safe withdrawal rate (4% rule)
    const annualIncome    = projectedTotal * 0.04
    const monthlyIncome   = annualIncome / 12

    // Gap analysis
    const goal     = retirementGoal || projectedTotal
    const onTrack  = projectedTotal >= goal
    const gapPct   = ((projectedTotal - goal) / goal * 100)

    // Asset allocation by risk
    const allocations: Record<string, any> = {
      conservative: {
        stocks: 30, bonds: 60, cash: 10,
        description: 'Capital preservation focus'
      },
      moderate: {
        stocks: 60, bonds: 30, cash: 10,
        description: 'Balanced growth and stability'
      },
      aggressive: {
        stocks: 80, bonds: 15, cash: 5,
        description: 'Maximum long-term growth'
      }
    }

    const allocation = allocations[riskTolerance] || allocations.moderate

    // Call Nova Pro for personalized advice
    const ECS_URL = await getEcsUrl()
    let aiAdvice  = ''

    if (ECS_URL) {
      try {
        const prompt = `You are Alex, a retirement planning advisor. 
Analyze this retirement profile and give structured advice.

PROFILE:
- Current age: ${currentAge} years old
- Target retirement: age ${retirementAge} (${years} years away)
- Current savings: $${Number(currentSavings).toLocaleString('en-US')}
- Monthly contribution: $${Number(monthlyContribution).toLocaleString('en-US')}
- Expected annual return: ${expectedReturn}%
- Risk tolerance: ${riskTolerance}
- Projected retirement savings: $${Math.round(projectedTotal).toLocaleString('en-US')}
- Projected monthly income: $${Math.round(monthlyIncome).toLocaleString('en-US')}/month
- Status: ${onTrack ? 'On track' : 'Below target'}
${retirementGoal ? `- Personal goal: $${Number(retirementGoal).toLocaleString('en-US')}` : ''}

Respond EXACTLY in this format:

**Retirement Assessment**
[2 sentence summary of their trajectory]

**What You're Doing Well**
- [specific positive point with numbers]
- [specific positive point with numbers]

**Top 3 Recommendations**
1. [Specific actionable recommendation with numbers]
2. [Specific actionable recommendation with numbers]  
3. [Specific actionable recommendation with numbers]

**Asset Allocation for ${riskTolerance} Risk**
- Stocks: [%] — [why this % for their age/risk]
- Bonds: [%] — [why this % for stability]
- Cash: [%] — [emergency fund rationale]

**Key Risk to Watch**
[One specific risk relevant to their profile with mitigation strategy]

---
⚠️ This is educational content not financial advice. Consult a certified financial planner.`
        const res = await fetch(`${ECS_URL}/research`, {
          method:  'POST',
          headers: { 'Content-Type': 'application/json' },
          body:    JSON.stringify({ topic: prompt }),
          signal:  AbortSignal.timeout(60000)
        })

        if (res.ok) {
          const data = await res.json()
          aiAdvice   = data.result || ''
        }
      } catch (err) {
        console.error('AI advice error:', err)
        aiAdvice = ''
      }
    }

    return NextResponse.json({
      projectedTotal:    Math.round(projectedTotal),
      annualIncome:      Math.round(annualIncome),
      monthlyIncome:     Math.round(monthlyIncome),
      years,
      onTrack,
      gapPct:            parseFloat(gapPct.toFixed(1)),
      allocation,
      aiAdvice,
      inputs: {
        currentAge, retirementAge, currentSavings,
        monthlyContribution, expectedReturn, riskTolerance
      }
    })

  } catch (error: any) {
    console.error('Retirement error:', error)
    return NextResponse.json({ error: error.message }, { status: 500 })
  }
}