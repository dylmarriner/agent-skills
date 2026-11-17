---
name: gtm-strategy
description: Complete go-to-market strategy framework from product launch to enterprise scale. Use when defining market positioning, building GTM motions, launching products, onboarding enterprises, or developing investor/board communication. Includes all GTM patterns and frameworks.
license: MIT
---

# GTM Strategy Library

Complete go-to-market strategy framework spanning the full journey from 0-to-1 product launch through enterprise onboarding and investor communication. These are the patterns that actually drive revenue — not theory about positioning or "growth hacks."

## When to Use

**Triggers:**
- "How do we position this product for market?"
- "Should we build PLG or sales-led motions?"
- "How do we launch and get first customers?"
- "Customer went live but adoption is weak"
- "Board meeting prep and investor updates"
- "Developer ecosystem strategy"

**Context:**
- All B2B products from seed to growth stage
- New product launches and feature releases
- Enterprise customer acquisitions
- Investor relations and board communication
- Developer platform ecosystems

---

## Table of Contents

### Part 1: Positioning & Market Strategy
- [Positioning Strategy](#positioning-strategy) — Find defensible market position
- [AI Product GTM](#ai-product-gtm) — Positioning, pricing, trust for AI products
- [Competitor Analysis](#competitor-analysis) — Market mapping and wedge identification

### Part 2: Motion & Launch
- [0-to-1 Launch](#0-to-1-launch) — First 10 customers and launch discipline
- [Product-Led Growth](#product-led-growth) — Self-serve and hybrid motions
- [Developer Ecosystem](#developer-ecosystem) — Community and platform strategies

### Part 3: Enterprise Motion
- [Enterprise Account Planning](#enterprise-account-planning) — Pre-sale deal strategy
- [Enterprise Onboarding](#enterprise-onboarding) — 4-phase framework from contract to value

### Part 4: Operating & Communications
- [Operating Cadence](#operating-cadence) — Internal meeting rhythms and health metrics
- [Board & Investor Communication](#board-and-investor-communication) — Updates, decks, bad news

### Part 5: Partnerships
- [Partnership Architecture](#partnership-architecture) — Deal structures and co-marketing
- [Technical Product Pricing](#technical-product-pricing) — Pricing strategy and models

> **Note:** Full content for each section available in individual skills that have been consolidated into this umbrella view.

---

## Part 1: Positioning & Market Strategy

### Positioning Strategy

**Core Frameworks:**

#### The One Word that Changed Everything
Early enterprise conversations positioned as "autonomous AI agent." Developers said "cool but scary." Managers thought "will this replace our team?" Deal progression: slow.

**The Change:** One word: "autonomous" → "AI teammate"

Same product. Same capabilities. Different framing.

**Result:** Developers: "This helps me." Managers: "This makes my team more productive." Deal progression measurably faster.

**Positioning Word Choice:**

**Words that scare enterprises:**
- ❌ Autonomous (implies: no control)
- ❌ Replaces (threatens: job security)
- ❌ Fully automated (removes: human judgment)

**Words that convert:**
- ✅ Teammate (implies: collaboration)
- ✅ Augments (helps: makes humans better)
- ✅ You stay in control (reassures: human oversight)

#### Crawl-Walk-Run Positioning Rollout

Crawl Phase (1-2 weeks): **Validation**
- A/B test website headlines
- Run two outbound email sequences (different angles)
- Ask existing customers: "If we described ourselves as [X], would you still recognize us?"
- Go/no-go: One variant outperforms incumbent by 20%+ on reply rate

Walk Phase (2-3 weeks): **Alignment**
- Rewrite website copy
- Create sales enablement: pitch deck, scripts, email templates
- Update documentation
- Go/no-go: Sales team says messaging is easier to use, CTR metrics improve

Run Phase (2-3 weeks+): **Scale**
- Launch dedicated landing pages
- Outbound campaigns per angle
- Full rebranding
- Announce repositioning (if appropriate)

**Why This Matters:**
Positioning changes create risk. De-risk through phased rollout. Don't commit product/org resources until testing validates.

#### Testing Positioning Claims

**Test 1: Outbound Email A/B**
- 100 prospects Version A vs 100 prospects Version B
- Measure: Reply rate, meeting booked rate
- Signal strength: HIGH (real buyer intent)

**Test 2: Website A/B**
- Version A: Current homepage
- Version B: New positioning angle
- Measure: CTR on key CTAs
- Duration: 1-2 weeks minimum
- Signal strength: MODERATE (interest without commitment)

**Test 3: Sales Call Scripts**
- Half AEs use positioning A, half use positioning B
- Measure: Demo-to-trial conversion
- Signal strength: HIGH (real sales cycle)

**Common Mistake:**
Changing positioning based on internal consensus, not customer feedback. Your team isn't the buyer.

#### Positioning Defensibility Assessment

Principle: A positioning is only valuable if competitors can't easily copy it.

**Defensibility Hierarchy:**

**1. Structural Advantage (Strongest)**
- Hard to copy: unique data ownership, deployment flexibility, pricing model, network effects
- Example: "Built for regulated industries with on-prem deployment" (can't copy without rebuilding architecture)

**2. Market Position (Strong if First)**
- Defensible if you own it first and scale
- Example: "First AI platform for [specific workflow]" (copycats look derivative)

**3. Product Feature (Weak)**
- Easy to copy: UX, specific capability
- Example: "Faster API calls" (competitor ships speed improvement in 6 weeks)

**How to Assess:**
For every positioning claim, ask:
1. Can competitor copy this with single product sprint? (Yes = not defensible)
2. Do we have structural advantage? (No = temporary positioning)
3. Is this credible given current product? (No = don't claim it yet)
4. Can we own this position before competitors react? (No = too slow)

**Common Mistake:**
Positioning on features competitors can easily match. This creates positioning treadmill — you're always defending, never owning.

---

### AI Product GTM

**When to Use:**
- How to position an AI product
- Handling "who's responsible when it breaks" objections
- Pricing variable-cost AI
- Choosing copilot/agent/teammate framing
- Selling autonomous tools into enterprises

#### The Real Enterprise AI Objection

Three months selling AI agents to enterprises: security reviews passed fast. Then the pattern: security approved, **operations rejected us**.

The objection wasn't "will the AI break production?" — they *assumed* it would break eventually. The real question:

**"Who's responsible when the agent does something wrong?"**

Not "do we trust the agent?" — "do we trust our *team* to handle this?"

**Before deploying AI agents, enterprises need clear answers:**
1. **L1 Response**: Who monitors the agent? (24/7 ops team, or dev team?)
2. **L2 Escalation**: When agent action fails, who debugs? (Agent team, or product team?)
3. **L3 Ownership**: When something breaks badly, who owns customer communication?

If you can't answer all three, **they won't buy**. Doesn't matter how good your AI is.

**The Qualification Question:**
"Walk me through what happens when the agent takes an action that breaks a workflow. Who gets alerted? Who investigates? Who decides whether to roll back or fix forward?"

If they can't answer, they're not ready. Pause the deal — help them build the process first.

#### Copilot vs Agent vs Teamte (Three Different Motions)

**1. Copilot (Safest, Lowest Value)**
- AI suggests, human decides every time
- Buyer psychology: Safe, non-threatening
- GTM motion: Developer adoption, bottoms-up
- Example: Code completion, writing assistance

**2. Agent (Scariest, Highest Value)**
- AI acts autonomously, human reviews periodically
- Buyer psychology: Scary, implies replacing humans
- GTM motion: Enterprise sales, top-down
- Example: Batch processing, automated workflows

**3. Teammate (Sweet Spot)**
- AI and human collaborate, split the work
- Buyer psychology: Partnership, not replacement
- GTM motion: Hybrid (dev adoption + manager approval)
- Example: Most AI agent platforms

**Decision Criteria:**
- Does your AI act autonomously (no approval per action)?
  - Yes → How selling?
    - Developers → "Agent" framing (they want autonomy)
    - Enterprises → "Teammate" framing (they want control)
  - No → "Copilot" framing (augmentation, not automation)

#### AI Pricing Problem (When Usage Varies 10x)

Every AI company faces this: Customer A uses 1,000 API calls/month. Customer B uses 10,000. Do you charge Customer B 10x more?

**The Three Models:**

**1. Seat-Based ($X per user/month)**
- Works when AI augments human work predictably
- Problem: Doesn't capture AI value scaling
- Real risk: High-usage customers subsidize low-usage ones

**2. Usage-Based ($X per API call/prediction/hour)**
- Works when AI does variable work, customers understand the unit
- Problem: Sticker shock for high-usage customers
- Real risk: Customers optimize to use *less*

**3. Outcome-Based ($X per outcome achieved)**
- Works when you can measure outcomes reliably
- Problem: Hard to measure, easy to game
- Real risk: You bear all risk if AI doesn't perform

**What Actually Works (Hybrid):**
Base fee (covers fixed costs) + variable fee (scales with value).

**Example structure:**
- Base: $X/month per team
- Variable: $Y per successful action/outcome
- Why: Base covers infra/support. Variable aligns with customer value. High-usage customers aren't punished.

**Pricing Rule:**
Your variable cost should be **20-30% of customer's alternative cost**. High enough to capture value, low enough they'll use liberally.

#### The AI Trust Ladder (From Someone Who Climbed It)

You can't sell AI by saying "trust us, it works." Build trust in stages.

**First: Transparency (Before First Demo)**
Send these three docs before they ask:
- Model card (what model, trained on what, accuracy on benchmarks)
- Security whitepaper (where data goes, how processed)
- Explainability doc (how to interpret AI decisions)

**Second: Control (In the Demo)**
Show them the safety mechanisms:
- How users approve/reject AI suggestions
- Kill switches and rollback mechanisms  
- Confidence scores and when AI says "I'm not sure"

**Third: Performance (Week 4-8)**
Prove it works:
- Benchmarks vs baseline (human or previous tool)
- Case study from similar company
- Live demo on their data (if possible)

**Fourth: Scale (When Serious)**
Show enterprise readiness:
- Enterprise deployment examples
- Performance at scale (latency, throughput, error rates)
- Compliance docs (SOC 2, GDPR, etc.)

**Decision Criteria:**
If buyers ask "how does this work?" before you've demoed, you skipped transparency. Back up and send the docs.

#### The Enterprise AI Demo (Show Failure, Not Success)

Canned demo where AI magically solves everything. Buyers think "this won't work on our messy data."

**Demo Structure That Works:**

**1. The Problem (30 seconds)**
"Your engineers spend hours on [specific task]. Here's what that looks like."
- Show: Current manual workflow
- Quantify: Time × Engineers × Weeks = Total cost

**2. The AI Attempt (60 seconds)**
"Here's the AI handling the same task."
- Show: AI analyzing, taking action
- **Key move**: Have AI encounter error or uncertainty
- Show: AI re-analyzing, recovering, or asking for help
- Narrate: "Notice it didn't get it perfect first time. It handles uncertainty like a human would."

**3. The Human Review (30 seconds)**
"Here's where the engineer reviews and approves."
- Show: Engineer examining AI's work
- **Key move**: Show engineer overriding or adjusting something
- Narrate: "Human stays in control. AI handles repetitive work, human handles judgment calls."

**4. The Outcome (30 seconds)**
"[X hours] → [Y minutes]. Engineer still owns the outcome, AI accelerates execution."
- Quantify: Time reduction, cost savings, capacity freed

**The Pattern:**
Demos with perfect AI → Buyers skeptical
Demos with imperfect AI that recovers → Buyers engaged

Show mistakes + recovery. Builds more trust than fake perfection.

#### The AI Positioning Trap (Fighting Asymmetric Wars)

You're competing in the AI agent space. Every competitor's homepage says "Automate [workflow] with AI."

**How to Diagnose:**
1. Collect homepage messaging from 5-7 direct competitors
2. Identify shared claims (these are commoditized)
3. Map where you have structural advantage (not just product features)
4. Find position competitors can't easily copy

**Structural advantages that work for AI positioning:**
- Unique data or workflow ownership
- Deployment flexibility (on-prem, private cloud, customer-controlled)
- Pricing model innovation
- Community or ecosystem (network effects)

**Feature advantages that don't last:**
- "Better accuracy" (catch up in one sprint)
- "Faster inference" (infrastructure commoditizes)
- "More integrations" (easy to copy)

**The Test:**
For every positioning claim: Can a competitor copy this with a single product sprint? If yes, it's not defensible. Don't build your GTM on it.

#### Ceiling Moment Qualification

Highest-intent enterprise buyers are people who've already adopted a comparable tool and hit its limits.

**Prospects have:**
- Used a copilot/assistant tool for 6+ months
- Hit its limitations (can't handle complex tasks, doesn't work with their stack)
- Low switching costs (mental model transfers)
- Clear business case

**How to Target:**
1. Identify incumberbent tools your product complements or displaces
2. Build target lists of companies known to use those tools
3. Craft outreach around the limitation, not your features:
   - "Teams using [incumbent] often hit a ceiling when they need [capability your product provides]"
   - Acknowledge the incumbent has value (don't trash-talk)
   - Position as "next level," not replacement

**Conversion Rate:**
Ceiling-moment conversations convert 3-5x vs cold outreach.

**The Qualification Question:**
"What's the most complex task you've tried to automate with your current tool, and where did it break down?"

If they have specific answer with specific pain, they're ceiling-moment buyer. If they say "it works fine," they're not ready.

---

### Competitor Analysis

**Purpose:** Systematic competitor intelligence for positioning and wedge strategy.

**Data Collection Framework:**

**Step 1: Competitor Messaging Audit**
- Collect homepage headlines from 5-7 direct competitors
- Identify shared claims (these are commoditized — you can't win here)
- Map where competitors claim unique value

**Example:**
If everyone says "fastest," "most reliable," "easiest to use" — these are table stakes, not differentiation.

**Step 2: Assess Your Actual Strengths**
- What can you do that competitors can't, without massive R&D?
- What do your best customers choose you for? (Ask them)
- What structural advantages do you have? (Deployment model, data ownership, pricing, network effects, etc.)

**Step 3: Find Under-Served Position**
- Where do existing solutions fail users?
- What problem is everyone ignoring?
- What buyer segment is under-served?

**Step 4: Stake a Clear Claim**

Must be:
- Something you can own now (not future roadmap)
- Something competitors can't easily copy (structural advantage)
- Resonant with your best customer segments

**Common Mistakes:**
- Claiming you're "better" at what everyone does (unbelievable)
- Positioning on features competitors already have
- Multiple positions simultaneously (choose one)
- Waiting for perfect product before positioning shift

---

## Part 2: Motion & Launch

### 0-to-1 Launch

**When to Use:**
- Launching products, finding early adopters
- Building launch week playbooks
- Diagnosing why adoption stalls
- Press coverage does not equal growth

#### Press ≠ Growth (The Launch That Got 12 Signups)

Coordinated feature launch with full press tour. TechCrunch, VentureBeat, product blogs. Big announcement day.

**Result:**
- 50K impressions
- 12 signups
- 2 conversions

**Why It Failed:**
Optimized for media buzz, not user value. The feature wasn't ready for self-serve. It needed education, context, hand-holding. Press gives you eyeballs. But eyeballs without activation = vanity.

**What Works Better:**
Email 50 target customers directly. "We built [feature] because teams like yours struggle with [problem]. Want early access?" Walk them through setup personally. Get feedback, iterate.

**Result:** 50 emails → 15 replies (30%) → 8 trials → 4 conversions (50%).

**The Lesson:**
Early customers come from direct outreach, not press coverage. Press matters later (Series A announcement, major milestone). For 0-to-1, it's distraction.

#### The Three-Layer Diagnosis (Why Launches Stall)

**Layer 1: Positioning Problem**
Symptoms: Messaging sounds like competitors, differentiation requires complex details, buyers see you as interchangeable.

Fix: Test new messaging before changing product. Stake claim you can own structurally.

**Layer 2: Experience Problem**
Symptoms: Strong awareness but weak activation, users sign up but don't complete first workflow, multiple entry points creating decision paralysis.

Fix: Identify 2-3 "undeniable use cases" that deliver immediate value. Restrict onboarding to those specific use cases. Gate advanced features behind mastery path.

**Layer 3: Alignment Problem**
Symptoms: Team reports being "out of bandwidth," different functions optimize for different metrics, no clear north star.

Fix: Define single shared north star. Use it as tiebreaker for every decision. Cut activities that don't ladder up to it.

**How to Use This:**
When launch stalls, diagnose which layer is broken. Fixing experience when problem is positioning wastes engineering. Fixing positioning when problem is internal alignment wastes marketing.

#### The First 10 Customers Framework

First 10 customers are **not for revenue**. They're for **learning**.

**What You're Learning:**
1. Does product actually solve the problem?
2. What's the activation flow? (How do they get value?)
3. What objections come up? (Price, features, integrations?)
4. Who's real buyer? (Title, role, budget authority?)
5. What's sales cycle? (Days, weeks, months?)

**Channel 1: Personal Network (first 2-3)**
- "I'm building [X], can I get your feedback?"
- Convert to paying customers (don't give away for free — free users give different feedback than paying ones)

**Channel 2: Direct Outreach (customers 3-20)**
- Build list of 100 target accounts
- Personalize to their specific pain
- Test messaging variants — which angle gets replies?

**Channel 3: Ceiling Moment Targeting (highest-intent)**
- Highest-intent prospects already adopted comparable solution and hit its limits
- Craft outreach around limitation: "We see teams that outgrow [incumbent] when they need [capability]. That's what we built."
- These convert 3-5x better than cold outreach

**Channel 4: Community (developer products)**
- "Built [X] to solve [problem], looking for early users"
- Offer white-glove onboarding
- Best for products where users congregate in Slack/Discord/forums

#### The 2-Week Experiment Cycle

**Principle:**
Speed in early stages matters more than perfection. Constraint is not whether you're right — it's how quickly you test assumptions and iterate.

**How to Execute:**
- Frame test with clear success criteria before starting
- Test one variable per experiment (messaging, channel, pricing, feature)
- Run for 2 weeks maximum — if it's not showing signal by then, it won't
- If it works, allocate 3x resources within a week
- If it doesn't, kill it and move to next test
- Document what you learned regardless of outcome

**The Playbook Rule:**
Every successful experiment must become a playbook before scaling. Structure: Goal → Steps → Expected output → Metrics → Risks. If someone unfamiliar can't execute, it's not documented well enough.

**Common Mistake:**
Over-planning before testing. Waiting for "perfect" conditions before launching. Staying with failing experiments too long. Make decisions with 70% information.

#### PMF Validation Checklist

Product-market fit is when customers pull you forward, not when you push them.

**Retention:**
- [ ] 40%+ of Week 1 users return Week 4
- [ ] Usage increasing over time
- [ ] Customers renewing without sales push

**Organic Growth:**
- [ ] Word-of-mouth referrals happening
- [ ] Customers asking "can I add my team?"
- [ ] Inbound interest without paid marketing

**Sales Velocity:**
- [ ] Sales cycles shortening
- [ ] Win rates >30% of trials
- [ ] Customers saying "we need this now"

**Qualitative:**
- [ ] >40% very disappointed if product went away (Sean Ellis test)
- [ ] Customers can articulate what it's for (clear use case)
- [ ] Customers advocating publicly

**If you don't have these, you don't have PMF yet. Don't scale marketing/sales.**

#### Partner-Led Market Entry

Rather than entering new markets through direct sales alone, use partnerships with established players to accelerate.

**How to Execute:**
1. Identify market leaders in your target segment
2. Approach with customer problem, not partnership pitch — "What if your users could access [capability]?" shifts from your need to their need
3. Start small: Help them solve one specific problem (narrow integration, not full partnership)
4. Prove value with 3-6 month pilot before asking for broader commitment
5. Build reference customers together — reduces their risk
6. Leverage their GTM: once integrated, they market to their base

**The Supernode Pattern:**
Position yourself as integration hub that other tools naturally connect through. You own critical data or workflows that other platforms need. This compounds — each new partner makes you more valuable to next.

**Category Sequencing:**
Don't pursue partnerships everywhere. Dominate 2-3 categories per quarter:
1. Lead with genuine use cases: "Our users ask for [partner] integration 50x per month"
2. After partnering with top player, competitors feel urgency to work with you too
3. After 2-3 successful partnerships in category, create joint customer stories

---

### Product-Led Growth

**When to Use:**
- Deciding PLG vs sales-led motion
- Optimizing activation
- Driving freemium conversion
- Building growth equations
- Recognizing when product complexity demands human touch

#### The PLG Reality Check (Test Before Commit)

Classic startup debate. PLG camp: "Developers want self-serve." Sales camp: "Enterprises need hand-holding." Instead of arguing, test both for 6 months. Same product, two GTM motions, tracked everything.

**The Results:**
PLG: High volume, low ACV (~$5K), fast time-to-revenue, higher churn.
Sales-led: Lower volume, high ACV (~$50K), slower time-to-revenue, lower churn.
**Sales won 10x on dollars despite 10x less volume.**

**Why:** Product complexity + buyer seniority = sales-led wins. The product required integration with existing infrastructure, change management across teams, and multi-stakeholder alignment. Developers loved self-serve. But they weren't the economic buyer.

**PLG works when:**
- Value is obvious in first 5 minutes
- Implementation is trivial
- Individual user gets value without team buy-in
- No procurement/legal hurdles
- Buyer = user

**Sales-led works when:**
- Product requires integration/setup
- Multiple stakeholders need alignment
- Buyer ≠ user
- Deal size justifies human touch
- Customer needs education to see value

**Before building PLG, test your motion. Don't assume PLG is better because it's trendy. PLG is efficient at volume, but sales-led can be more profitable with complexity.**

#### The Growth Equation (Map Inputs to Outputs)

Growth compunds when you systematize relationship between activities and user acquisition. Not "do more marketing" — map specific inputs to measurable outputs.

**For each channel, define:** Activity (input) → Traffic (output) → Conversions.

- **Organic Search:** 1 quality blog post → 400 users/month → 5% conversion = 20 new users
- **Paid Ads:** $1K spend at 8% conversion on 100K impressions = 8K clicks → conversions at X%
- **Community Events:** 1 event → 60 attendees → 35% conversion = 21 users
- **Referral:** 1 integration partner → N referred users → conversions at Y%

**Why This Matters:**
Once you validate the equation, scaling becomes math. "I need 200 more users next month" → "I need 10 more blog posts" or "$5K more ad spend." Without the equation, you're guessing.

**Testing the Equation:**
1. Start with hypothesis: "If I create X, it drives Y conversion"
2. Test with small sample: 1 blog post, measure actual conversion
3. Validate: Does reality match hypothesis?
4. Scale with confidence: If yes, increase input
5. Kill if not: 4 weeks of data is enough to decide

#### Channel Economics (Kill Losers, Double Down on Winners)

Every channel has economics. Without tracking, you over-invest in losers and under-invest in winners.

**Track Per Channel:**
1. **CAC:** Total spend / new users
2. **Conversion rate:** Signups → paying
3. **Retention:** 30-day, 90-day by source
4. **LTV:** Revenue over customer lifetime, by channel
5. **Payback period:** How long to recoup CAC

**The Decision Framework:**
- CAC < (LTV × margin) → Scale aggressively
- CAC ≈ (LTV × margin) → Optimize, don't scale
- CAC > (LTV × margin) → Kill within 4 weeks

**Monthly channel review:** Which channels are profitable? Which are drains? Quarterly reallocation: 3x budget to winners, kill losers.

**Critical Insight: Channel Quality Varies**
Cheap CAC doesn't mean good CAC. Organic search might deliver users at $0 CAC with 85% 30-day retention. Paid search might deliver users at $12 CAC with 45% 30-day retention. The "free" channel is 10x more valuable when you factor in retention and LTV.

#### Time to First Value (The Only Activation Metric)

Users decide product value in first 5-10 minutes. If they don't reach the aha moment fast, they abandon.

**The Activation Audit:**
1. Sign up for your own product as new user
2. Time how long to first value
3. Count steps to aha moment
4. Where did you get stuck?

**If TTFV > 10 minutes, you have an activation problem.**

**Before:** Sign up → confirm email → fill profile → configure settings → read docs → first action

**After:** Sign up → pre-loaded sample data → first action (immediate aha moment)

**Specific Fixes:**
1. **Pre-load sample data.** Users want to see value, not set up. Give them working example immediately.
2. **Skip non-essential setup.** Email confirmation, profile, settings — all can wait until after aha moment.
3. **Progressive disclosure.** Don't show all features upfront. Start with one core workflow. Reveal complexity gradually.
4. **Show, don't tell.** Interactive tutorial > video > text docs. Let them click through a workflow.

#### The $5K → $50K Inflection (When PLG Breaks)

PLG works for $1K-$10K ARR. Between $20K-$50K, motion breaks because organizational friction kicks in: procurement, legal, security, multi-stakeholder buy-in.

**The Hybrid Approach:**

**PLG ($0-$10K):** Self-serve sign-up → free tier → paid tier → credit card checkout → automated onboarding

**Sales-Assisted ($10K-$50K):** Self-serve discovery → sales engages on usage signals → human-negotiated contract → dedicated onboarding

**Enterprise ($50K+):** Outbound or inbound lead → demo → POC → proposal → legal/security review → executive sponsor

**PQL Signals (When to Trigger Sales):**
- **Usage depth:** Daily active, core features used, approaching limits
- **Expansion signals:** Multiple users from same company, team features, integrations
- **Buying signals:** Requests for SSO/compliance/SLAs, asks about team pricing

**The Handoff:**
Bad: "Hey, I saw you signed up." (Cold, generic, kills trust)
Good: "Your team is using [specific feature] across 12 repos. We can help you [specific value]. Want 15 minutes?" (Warm, specific, offers value)

Common Mistake: Sales engaging too early on <$5K deals. Kills PLG motion, scares users. Let them self-serve until they need help.

#### Growth Forecasting (Plan for Uncertainty)

Forecasts are always wrong. Plans are still valuable because they force thinking and create accountability.

**Model Three Scenarios:**

**Baseline (current trajectory continues):**
- Organic search: 35% growth → 40K new users
- Paid: Flat → 2K new users
- Community: 10% growth → 400 new users
- Total: 42.4K

**Upside (if all growth initiatives execute):**
- Organic: 50% growth (3x content) → 48K
- Paid: 2x spend, same efficiency → 4K
- New initiative (partnerships): ramp → 3K
- Total: 55K

**Downside (if key channels fail):**
- Organic: 0% growth → 26K
- Paid: CPA doubles → 1K
- Total: 27K

**Use This For:**
- Setting baseline targets (baseline scenario)
- Stretch goals (upside scenario)
- Escalation triggers (if hit downside, something needs to change)
- Resource allocation (what inputs change to hit upside?)

**Monthly Update:** Compare forecast to actual. Adjust model. Don't forecast-and-forget.

---

### Developer Ecosystem

**When to Use:**
- Building developer communities
- API platform adoption strategy
- Deciding open vs curated ecosystems
- Scaling platform adoption
- Designing student program pipelines

#### Open vs Curated Ecosystem (The Marketplace Decision)

Running ecosystem at developer platform. Leadership debate: Open marketplace to anyone, or curate for quality?

**Quality control camp:** "We need gatekeeping. Otherwise we'll get SEO spam, low-quality integrations, brand damage."

**Open camp:** "Developers route around gatekeepers. Network effects matter more than quality control."

**The decision:** Went open. Quality concerns were real, but bet: control comes from discovery and trust layers, not submission gatekeeping.

**What We Built Instead of Gatekeeping:**
1. **Search and discovery** — Surface high-quality integrations through algorithms, not human curation
2. **Trust signals** — Verified badges, usage stats, health scores
3. **Community curation** — User ratings, collections, recommendations
4. **Moderation** — Remove spam after publication, not block before

**Result:** Network effects won. Thousands of integrations published. Quality surfaced through usage, not through us deciding upfront.

**Decision Framework:**
- **Curated** works when: Brand risk high, dozens of partners, can scale human review
- **Open** works when: Hundreds/thousands of potential partners, network effects matter more than quality control

#### The Three-Year Student Program Arc

Most developer programs optimize for quick wins. Better approach: Build long-term talent pipeline.

**Year 1: University Partnerships**
- Partner with CS departments
- Curriculum integration (hackathons, coursework)
- Student licenses (free or heavily discounted)
- Metrics: # universities, # students activated

**Year 2: Student Community & Certification**
- Student expert certification program
- Student-led workshops and events
- Campus ambassadors
- Metrics: # certified, # student-led events

**Year 3: Career Bridge**
- Job board connecting students → companies
- Enterprise partnerships (hire certified students)
- Alumni network
- Metrics: # hired, company partnerships

**Why This Works:**
Students become enterprise buyers 5-10 years later. You're building brand loyalty before they have purchasing power.

#### Developer Journey (Awareness → Integration → Advocacy)

**Stage 1: Awareness**
- How they discover you?
- Content, search, word-of-mouth, events

**Stage 2: Onboarding**
- First API call in <10 minutes
- Quick-start guides
- Sample code in popular languages

**Stage 3: Integration**
- Building real use cases
- Integration guides
- Support when stuck

**Stage 4: Production**
- Deployed and generating value
- Monitoring usage
- Enterprise upgrade path

**Stage 5: Advocacy**
- Sharing publicly
- Recommending to others
- Contributing back (docs, code, community)

**Metrics That Matter:**
- Time to first API call (onboarding)
- % reaching production (integration success)
- Monthly active developers (engagement)
- Developer NPS (advocacy)

#### Documentation Hierarchy

**Tier 1: Quick Starts (Get to Value Fast)**
- "Hello World" in 5 minutes
- Common use case examples
- Copy-paste code that works

**Tier 2: Guides (Solve Real Problems)**
- Use case-specific tutorials
- Integration patterns
- Best practices

**Tier 3: Reference (Complete API Docs)**
- Every endpoint documented
- Request/response examples
- Error codes and handling

**Tier 4: Conceptual (Understand the System)**
- Architecture overviews
- Design philosophy
- Advanced patterns

**Most developers need:** Tier 1 first, then Tier 2. Very few read Tier 4.

#### Community vs Support (When to Use Which)

**Community (Async, Scalable):**
- Slack/Discord for real-time help
- Forum for searchable Q&A
- GitHub discussions for feature requests
- Best for: Common questions, peer-to-peer help

**Support (Sync, Expensive):**
- Email support for enterprise
- Dedicated Slack channels for partners
- Video calls for complex integrations
- Best for: Paying customers, strategic partners

**How to Route:**

**Community first:**
- Developer asks question
- Community member answers
- You validate and upvote
- Searchable for future developers

**Escalate to support when:**
- No community answer in 24 hours
- Enterprise/paying customer
- Security or compliance issue
- Complex integration requiring custom work

**Partner Tiering:**
- **Tier 1: Integration Partners** (Self-Serve) - build with public API, you provide docs/Slack/office hours, they drive own marketing
- **Tier 2: Strategic Partners** (Co-Development) - co-developed integration, you provide dedicated channel/co-marketing, joint case studies
- Don't over-tier. 2 tiers is enough.

---

## Part 3: Enterprise Motion

### Enterprise Account Planning

**When to Use:**
- Preparing for enterprise deals
- Building account strategy
- Stakeholder mapping
- Deal risk assessment
- Pre-sale engagement planning

### Enterprise Onboarding

**When to Use:**
- Implementing new enterprise customers
- Preventing churn during onboarding
- Solving adoption cliff that kills deals post-go-live
- Week 4 ghosting problem

#### The Week 4 Ghosting Problem

Week 1: Kickoff call goes great. Everyone's excited.
Week 2-3: Technical discovery, requirements gathering. Still good.
Week 4: Customer stops responding. Meetings get cancelled. "Too busy."

**What Happened?**
You started customer onboarding before internal alignment on their side.

**Who Owns This Project Internally?**
- Sales rep? (Already moved to next deal)
- Technical champion? (Day job took over)
- Executive sponsor? (Delegates, doesn't drive)
- Nobody? (**This is why they're ghosting**)

#### The Adoption Cliff (Week 12 Problem)

Go-live happens Week 6. Usage spikes. You celebrate.
Week 8: Usage plateaus.
Week 10: Usage declining.
Week 12: Usage down 50% from peak.

**Why This Happens:**
You treated go-live as the finish line. **Go-live is the starting line.**

**Adoption Stages Beyond Go-Live:**

**Week 1-6 (Implementation):** Get it working
- Measure: % of technical setup complete
- Owner: Technical lead

**Week 6-12 (Initial Adoption):** Get people using it
- Measure: # active users, frequency of use
- Owner: Enablement / DevRel

**Week 12-26 (Sustained Adoption):** Prove ongoing value
- Measure: Use case expansion, team spread
- Owner: Customer success

**Week 26+ (Expansion):** Grow within account
- Measure: New teams, new use cases, upgrade triggers
- Owner: Account executive + CS

**What to Do Week 6-12:**
**Week 7:** First value report
"Week 1 accomplishments: [specific metric]. Good looks like Week 12: [target]."

**Week 9:** User success story
"[User name] on [team name] saved [X hours/reduced Y errors]. Here's how they're using it."

**Week 11:** Use case expansion conversation
"You're using us for [primary use case]. Teams like yours also use us for [adjacent use case]. Want to explore?"

#### Four-Phase Onboarding Flow

**Phase 1: Kickoff (Week 1)**
Goal: Align on objectives, timeline, success metrics
Agenda: Introductions + executive alignment + success definition + timeline + cadence + next steps (30-45 min)
Deliverable: Kickoff recap sent within 24 hours

**Phase 2: Discovery & Planning (Week 2-3)**
Goal: Understand technical landscape, map use cases, plan rollout
Three parallel workstreams: Technical Discovery, Success Planning, Technical Setup
Deliverable: Customer Success Plan document

**Phase 3: Implementation (Week 4-6)**
Goal: Deploy to pilot, validate use cases, prepare for broader rollout
Three parallel tracks: Administration & Setup, User Enablement, Pilot & Feedback
Deliverable: Go-live readiness checklist completed

**Phase 4: Go-Live & Ongoing Success (Week 6+)**
Goal: Rollout broadly, sustain adoption, expand use cases
Week 6-8: Rollout, training, support available
Week 8-12: First value report, user success stories, use case expansion
Week 12-26: Monthly business reviews, adoption tracking, expansion opportunities

---

## Part 4: Operating & Communications

### Operating Cadence

**When to Use:**
- Designing meeting rhythms
- Building metric reporting systems
- Quarterly planning structure
- Health metrics and escalations
- Weekly leadership sync

**Core Frameworks:**
Weekly, bi-weekly, monthly, and quarterly meetings that create accountability and visibility without meetings fatigue.

### Board & Investor Communication

**When to Use:**
- Preparing board decks
- Writing investor updates
- Handling bad news with board
- Structuring QBRs
- Building board-level metric discipline

#### The Story, Then the Data

Most board meetings start with data dump. Slide after slide of metrics, then 10 minutes of Q&A where board tries to figure out what it all means.

**Flip it. Narrative leads; data confirms.**

**Board Meeting Structure:**

**Pre-Read (48-72 hrs before)**
- Financial dashboard (ARR, burn, runway, pipeline)
- Metric scorecard with health indicators (green/yellow/red)
- 2-3 page narrative summary covering market context and strategic update
- Rule: If it can be read, don't present it

**Meeting (90-120 min)**
1. Market context + questions on pre-read (15 min)
2. CEO strategic update — The "Three Things" (15 min)
3. Decision items (30-45 min)
4. Deep dive (20-30 min)
5. Closing + closed session (10 min)

#### The "Three Things" Narrative Model

**What's Working (2-3 areas):**
Be specific. Not "sales are going well" but "closed first six-figure enterprise deal, validating the commercial motion." Quantify momentum.

**What's Not Working (1-2 areas):**
Be equally specific. Not "we had challenges" but "self-serve conversion is weak — strong awareness but 0.1% conversion rate." Board needs to understand actual problem, not euphemism.

**What We're Doing About It (for each "not working"):**
Articulate specific changes. What product changes? What org changes? What's timeline? What resources committed?

#### Progress Is Directional, Not Absolute

It doesn't matter if you hit 100K users if you were aiming for 50K, or if you missed 200K. Context is everything. Show progress toward your goal, not just the number.

**How to Frame Progress:**
- **On track:** "Target 100K active developers. Currently 70K. All initiatives performing as planned. Confidence: High."
- **At risk:** "Target 100K active developers. Currently 50K. Acquisition cost higher than expected. Testing new channels. Adjusted target: 85K. Confidence: Medium."
- **Ahead:** "Target 100K active developers. Currently 95K. Exceeding acquisition forecasts. New partnerships accelerating growth. Confidence: Very high."

**The Rules:**
1. Set goal upfront (every metric needs a target)
2. Show progress as % toward goal, not just absolute number
3. Acknowledge misses; explain pivots
4. State confidence level based on trajectory

#### The Four-Tier Metric Hierarchy

**Tier 1: North Star (1 metric)**
Single metric that best represents company health. Examples: ARR, active users, tasks completed. This is the one metric board should remember if they forget everything else.

**Tier 2: Driver Metrics (3-5 metrics)**
Leading indicators that predict your north star. User acquisition rate, retention curves, feature adoption, DAU/MAU ratio, pipeline coverage. Early warning before revenue impact.

**Tier 3: Health Metrics (3-5 metrics)**
Signals of team and operational health. Burn rate and runway, headcount vs plan, engineering velocity/ shipping pace, NPS or customer satisfaction. Capacity constraints on growth.

**Tier 4: Red Flags (2-3 thresholds)**
Metrics that, if they cross a threshold, require immediate action. Churn rate above X%, CAC above $Y, retention decline greater than Z%. Triggers for strategic conversation.

**The Discipline Rules:**
1. Same metrics every quarter. Never drop old ones.
2. One context sentence per metric. Is it good or bad? What's the implication?
3. Actuals vs plan, always. Never show metric without showing what you planned.
4. Disaggregate when needed. Total usage hides segments.
5. Use health indicators. Green/yellow/red for quick board assessment.

#### Deliver Bad News Before Board Asks

Board confidence erodes when bad news is delayed or sugar-coated. They can handle bad news. They can't handle surprises.

**The Pre-Brief Pattern:**
Before bad news hits full board, pre-brief lead director 48-72 hours before meeting.

- **Who:** Board chair or most experienced director
- **What:** The issue, assessment, plan
- **Why:** Director can help frame for full board, avoid surprise shock, may have seen pattern before

Then send short email to full board: "Wanted to flag something before our next meeting. [Specific problem]. Here's what we know so far, what we don't know yet, and what we're doing about it. Will have full update at board meeting."

**The Bad News Framework:**

1. **What happened** (specific, one sentence — not defensive)
   - "We missed Q1 target of 10 new enterprise customers; achieved 7"

2. **Why it happened** (root cause, not excuse)
   - "Customer evaluation timelines slipped due to product gaps we didn't diagnose early enough"
   - Own it: "We misread the demand signal" not "the market shifted"

3. **What's the impact** (honest about severity)
   - "Affects Q1 ARR by ~$50K, pushing us below original guidance"

4. **What we're doing about it** (specific actions, owners, timeline)
   - "Changed sales motion to qualify on product readiness upfront; revised Q2 target to 15 (including Q1 backlog of 7)"

**Common Mistake:**
Sandwiching bad news between good news hoping nobody notices. Board members see this immediately. It damages trust more than bad news itself.

#### The Monthly Investor Update

Most founders send investor updates quarterly at best. Best founders send monthly — even when things are bad. Especially when things are bad.

**Why Monthly:**
- Keeps investors engaged without scheduling calls
- When need help (intros, advice, bridge), investors already have context
- Consistency signals operational discipline; irregular updates signal chaos

**The Format:**

**Subject line:** [Company Name] — [Month] Update

**Opening (1 paragraph):**
One headline. Brief context.

**TL;DR (3 bullets):**
- One number (metric that matters most)
- One win (specific — customer name, deal size, milestone)
- One challenge (with what you're doing about it)

**Key Metrics (same table every month):**
ARR, MRR Growth, Burn Rate, Runway, Pipeline, Customers — track consistency.

**Key Updates (2-3 bullets):**
Major hires, product launches, partnership/customer wins, strategic pivots.

**Asks (1-2 bullets):**
What help do you need? Intros, hiring leads, strategic advice. Be specific.

**Cadence Rules:**
- Same day every month. First Monday, last Friday — pick one and never miss it
- Send within a week of major news (don't hold for next scheduled update)
- During active fundraising: weekly to warm investors, monthly to existing

---

## Part 5: Partnerships

### Partnership Architecture

**When to Use:**
- Designing partner relationships
- Deal structures and co-marketing
- Choosing partners vs direct sales
- Partner tiering and qualification
- Co-selling motions

### Technical Product Pricing

**When to Use:**
- Pricing technical products (APIs, platforms, SaaS)
- Seat-based vs usage-based models
- Freemium thresholds and value gates
- Enterprise enterprise negotiations
- Pricing strategy and economics

---

## Common Mistakes Across All GTM

**1. Optimizing for headlines instead of activation**
50K impressions and 12 signups. Press ≠ growth.

**2. No target customer list before launch**
Spray-and-pray doesn't work at 0-to-1. Build list of 100 accounts first.

**3. Flexibility without defaults**
Giving users every option paralyzes them. Pick 2-3 undeniable use cases and guide hard.

**4. Giving product away for free**
Free users give polite feedback. Paying users give honest feedback.

**5. Scaling before learning**
First 10 customers are for learning, not revenue. Document everything.

**6. Over-planning, under-testing**
2-week experiments with clear kill criteria. Move fast, document learnings.

**7. Diagnosing wrong layer**
Positioning fix when problem is experience = wasted marketing. Experience fix when problem is positioning = wasted engineering.

**8. Starting customer onboarding before internal alignment**
Wastes first 2-3 weeks, creates confusion, kills credibility.

**9. No project owner identified upfront**
Discovers it Week 4, has to restart or deal stalls.

**10. Overcommitting on timeline without technical requirements**
Discovers blockers mid-implementation, misses deadline.

**11. No internal communication hub**
Decisions don't propagate across teams, rework happens.

**12. Treating go-live as project complete**
Adoption cliff at Week 12, account at risk.

**13. Sequential tracks instead of parallel**
Implementation takes twice as long, customer loses momentum.

**14. No ongoing metrics post go-live**
Discovers adoption issues too late to save account.

**15. Board meetings as status reports**
Board members can read. Send pre-read. Use meeting for decisions and discussion, not data walkthroughs.

**16. Changing metrics every quarter**
Consistency in metrics builds trust. Moment you swap out metric that looked bad for one that looks good, you've told board your numbers can't be trusted.

**17. No clear ask**
Every investor update, every board meeting should have an ask. Intros, advice, approval, patience. Investors want to help — if you never ask, they disengage.

**18. Defending instead of describing**
When explaining away a miss for 10 minutes, board hears defensiveness. State miss, state cause, state plan. Move on.

**19. Strategy stays in board room**
If your team can't explain strategy, you haven't communicated it. Cascade it or it doesn't exist.

**20. Surprises in board meeting**
Bad news should never land for first time in board meeting. Pre-brief lead director. Send flag email. Let board process before meeting.

---

## Quick Reference

**GTm Decision Criteria:**

**Positioning:**
- Structural advantage > market position > features (defensibility hierarchy)
- "Autonomous" scares enterprises, "teammate" converts
- Test word choices with A/B before committing

**Motion:**
- PLG works when value in <10 min + self-serve implementation + buyer = user
- Sales-led works when product requires integration + stakeholder alignment + buyer ≠ user
- Hybrid: PLG $0-$10K, Sales-Assist $10K-$50K, Enterprise >$50K

**Launch:**
- First 10 customers are for learning, not revenue
- 2-week experiments with clear kill criteria
- Press ≠ growth, direct outreach wins at 0-to-1
- PMF signals: 40%+ W1→W4 retention + word-of-mouth + shortening sales cycles

**Enterprise:**
- Identify project owner by name BEFORE kickoff
- Go-live is starting line, not finish line
- Week 4 ghosting = no project owner
- Adoption cliff at Week 12 requires intervention

**Communications:**
- Board: Story first, data second. Three Things narrative
- Bad news: Pre-brief lead director, four-part framework
- Updates: Monthly same day, TL;DR, key metrics, specific asks
- Cascade: Exec (weekly) → Leadership (bi-weekly) → All-hands (monthly) → Team (ongoing)

**Developer Ecosystem:**
- Open > curated when network effects > quality control
- Student program: Year 1 partnerships, Year 2 certification, Year 3 job board
- Quick starts first, guides second, reference third, conceptual fourth never
- Community for common questions, support for paying/enterprise

---

## Related Skills

**Positioning & Market:**
- Product-market fit validation
- Category creation and naming
- Messaging and copywriting

**Motion & Launch:**
- Customer acquisition channels
- Pricing strategy frameworks
- Experiment design and testing

**Enterprise:**
- Sales methodology (MEDDIC, Challenger, etc.)
- Customer success best practices
- Technical implementation patterns

**Communications:**
- Data storytelling
- Executive presentation skills
- Crisis communication

---

*Complete GTM strategy framework synthesized from patterns across multiple companies at different stages — from seed to growth. Includes positioning frameworks, launch discipline, PLG vs sales-led testing, enterprise motion, and operating cadences. Not theory — patterns tested across deals where "autonomous" killed conversations and "teammate" converted, the parallel test where sales-led won 10x on revenue despite 10x less volume, the launch that got 50K impressions and 12 signups, the Week 4 ghosting pattern that killed deals, and the Three Things narrative model used across multiple board meetings. All GTM patterns consolidated into one class-level library.*