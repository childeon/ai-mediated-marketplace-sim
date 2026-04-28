# Presentation Prep: AI-Mediated Food Delivery

## Core Throughline

**One-sentence thesis:** An LLM discovery layer improves consumer matching, but the welfare result depends almost entirely on how the LLM is paid.

The presentation should feel like one argument, not four separate experiments:

1. **Discovery moves upstream.** In traditional food delivery, platforms own search and sponsored placement. With ChatGPT-style ordering, the LLM becomes the top-of-funnel gatekeeper.
2. **Neutral AI helps consumers but not platforms.** The neutral LLM aggregates all platforms and ranks by intent fit, so consumers get better matches, lower prices, and faster delivery. But platforms lose aggregate net revenue because consumer-fit routing pulls traffic away from high-commission and sponsored placements.
3. **That creates the monetisation problem.** If neutral LLM access creates negative platform WTP, the LLM operator will look for paid mechanisms. The mechanism design question is therefore unavoidable.
4. **CPC is the bad transplant from ads.** Paying per click rewards attention, not satisfaction. It pushes the LLM toward the highest-paying platform and creates concentration.
5. **CPFI is the aligned mechanism.** Paying per fulfilled intent ties the LLM's revenue to the consumer's actual objective. It preserves the consumer welfare gains while still giving the LLM a revenue path.
6. **Policy punchline:** Do not ban monetisation; regulate the weight and structure of sponsored ranking. Bias caps plus outcome-contingent payment are the right direction.

## 90-Second Opening

Food delivery platforms used to control discovery: users opened DoorDash or Uber Eats, searched inside one app, and saw a platform-ranked feed with sponsored placements. But if users start ordering through ChatGPT, discovery moves one layer upstream. The LLM chooses the shortlist before the delivery app ever sees the consumer.

Our project asks: when the LLM becomes the discovery layer, who benefits, who pays, and what payment mechanism preserves consumer welfare?

We simulate 1,000 consumers, 50 restaurants, and 3 platforms across 10 Monte Carlo runs. Consumers either search their two most-loyal platforms directly, or they query an LLM that aggregates all offers and returns a top-5 shortlist. Then we test four payment regimes: neutral, cost per click, cost per acquisition, and cost per fulfilled intent.

The central result is a tension: the neutral LLM is good for consumers, raising intent fulfilment by 9.3%, lowering average price by $1.71, and cutting delivery time by 1.7 minutes. But it is bad for platforms in aggregate, reducing platform net revenue by about $1,483. That means the LLM creates consumer surplus by taking control away from platform ranking.

Paid mechanisms restore platform willingness to pay, but the design matters. CPC creates the biggest distortion: FoodRush jumps from about one-third to two-thirds of orders. CPFI is the aligned mechanism because the LLM only earns fully when the recommendation actually fulfils the user's intent.

So our punchline is: LLM food delivery is welfare-improving only if monetisation is tied to fulfilled consumer intent, not raw clicks.

## Defensible Design Choices

**Why compare against consumers checking only two platforms?**  
This is the fragmented-search baseline. In reality, most users do not exhaustively compare every delivery app for every meal. Giving them two loyalty-weighted platforms is generous to the no-LLM baseline because it still lets them search more than one app.

**Why does no-LLM use a cuisine filter?**  
To avoid straw-manning direct search. The consumer is not blindly scrolling; they search for their desired cuisine within each app. The LLM advantage is cross-platform aggregation and multi-attribute ranking, not basic keyword matching.

**Why top-5 LLM shortlist?**  
A shortlist represents the actual interaction pattern of an assistant: it does not show every option, it recommends a small set. K=5 is large enough to give choice but small enough for ranking power to matter.

**Why a two-stage LLM choice model?**  
LLM-mediated ordering has a click stage and a purchase stage. CPC bills on click; CPA and CPFI bill on completed purchase. Modeling two stages is what makes CPC and CPA mechanically distinct.

**Why hard-zero wrong cuisine in intent fulfilment?**  
The stated consumer intent is the object being measured. If someone asks for Thai and gets Italian, it may be high quality but it did not fulfil the stated request.

**Why is CPFI not just hand-tuned to win?**  
CPFI uses the same base LLM ranking weights as the other regimes. The only difference is that the sponsorship boost is multiplied by predicted intent fulfilment. That implements the mechanism's incentive logic directly.

**Why calibrate paid rates endogenously?**  
Raw CPC/CPA dollar rates can be arbitrary. The model first measures how much gross platform surplus a paid routing pattern creates, then lets the LLM capture 50% of the positive aggregate sponsor-side surplus. This makes the monetisation comparison about mechanism structure, not about picking convenient prices.

**Important nuance:** This is an aggregate sponsor-side WTP ceiling, not a guarantee every platform benefits. Low-sponsorship platforms can lose traffic as a competitive externality.

## Likely Questions And Strong Answers

**Q: Isn't the model biased toward making LLMs look good?**  
A: We tried to avoid that. The no-LLM baseline is not weak: consumers inspect their two most-loyal platforms and filter by cuisine. The LLM gain is therefore modest, not huge: +1.2 percentage points conversion and +9.3% intent fulfilment. The model also shows neutral LLM hurts platform revenue and that high sponsorship bias can make the LLM worse than direct search.

**Q: Why does neutral LLM reduce platform revenue?**  
A: Platform feeds partially optimize for platform economics: commission revenue, promo boosts, and sponsored slots. Neutral LLM optimizes consumer fit across platforms. That can route consumers to lower-commission or less-sponsored offers, improving consumer outcomes while reducing platform net.

**Q: Why does CPFI have higher shortlist relevance than neutral?**  
A: The difference is small and comes from the CPFI boost being conditional on predicted fulfilment. It can slightly reorder good-fit options upward, while off-intent options receive little boost. I would frame it as "CPFI preserves neutral-like quality," not as a claim that ads improve relevance in general.

**Q: If all_platforms_nonnegative is false, doesn't that break the participation constraint?**  
A: No. The calibration is aggregate and sponsor-side. The platforms receiving traffic gains fund the LLM up to a share of their positive gross surplus. Other platforms can lose traffic without being charged. That is a competitive externality, not voluntary participation by every platform.

**Q: Why use hand-coded cuisine similarity instead of embeddings?**  
A: For a course simulation, a transparent similarity table is easier to audit and explain. It keeps the mechanism interpretable. A natural extension is replacing it with sentence-transformer embeddings, which we list as future work.

**Q: Are the weights arbitrary?**  
A: They are parameterized in `config.py` and chosen to reflect plausible marketplace priorities: platform ranking values commission and promotions; LLM ranking values semantic match, affordability, quality, and delivery time; consumer utility values cuisine match, quality, price, time, promotions, trust, and loyalty. The key results are comparative across regimes under the same environment.

**Q: Why does CPC create so much concentration?**  
A: FoodRush pays the highest CPC rate. In CPC, every FoodRush offer gets a larger additive ranking boost regardless of whether the consumer ultimately buys or is satisfied. That shifts shortlist exposure and order share toward FoodRush.

**Q: What is the main limitation?**  
A: It is a static simulation. Platforms, restaurants, and consumers do not adapt over time. In reality, restaurants could change promo budgets, platforms could change commissions, and consumers could update trust after bad recommendations.

**Q: What should be regulated?**  
A: Not LLM ordering itself. The risky part is sponsored ranking weight. The simulation supports two interventions: cap paid bias around 0.1-0.2, and prefer outcome-contingent mechanisms like CPFI over CPC.

## Slide-By-Slide Talk Track

**Slide 1:** State the question: what happens when AI controls food discovery?

**Slide 2:** Explain the market structure shift. Old world: platform feed. New world: LLM shortlist.

**Slide 3:** Show consumer gains under neutral LLM. Emphasize the baseline is not a straw man.

**Slide 4:** Show the paradox: consumers win, platforms lose. This motivates monetisation.

**Slide 5:** Compare mechanisms. CPC harms; CPA is intermediate; CPFI preserves fit.

**Slide 6:** Explain concentration. The highest-paying platform captures share under CPC.

**Slide 7:** Bias sweep. There is a threshold where paid bias destroys the LLM's consumer advantage.

**Slide 8:** Trust affects conversion volume, not match quality. Algorithm design matters even before mass adoption.

**Slide 9:** Attribution. The LLM creates some new demand; sponsorship mostly redistributes share.

**Slide 10:** Land the punchline: neutral LLM helps consumers, CPC distorts, CPFI plus bias caps is the defensible design.

## What To Say If You Feel Put On The Spot

"The model is intentionally stylized, so I would not claim these exact numbers are predictive. The robust point is directional: once discovery moves to the LLM layer, payment design determines whether the LLM optimizes for consumer intent or for paid traffic. CPC rewards attention, CPFI rewards fulfilled intent, and the simulation shows that distinction clearly."

