# 2025 Lecture 11 - Scaling details — pages 33-40

- page_id: `2025-lecture-11-scaling-details__005__pages-33-40`
- url: https://github.com/stanford-cs336/spring2025-lectures/blob/00191bba00d6d64621dc46ccaed9122681413a24/nonexecutable/2025%20Lecture%2011%20-%20Scaling%20details.pdf
- type: segment

## Content

LLaMA 3 (2024) Scaling laws
Isoflops -style scaling (39 -1 ratio)
 Compute -to-downstream scaling

Hunyuan-1 (2024) large scaling laws
Yet more isoflops -style scaling (but this time for MoE parameter sizes)
Optimal ratio – 96-1 (data to active param)

MiniMax-01 (2025)
Architecture scaling laws + Chinchilla method 1

Recent scaling law recipes
CerebrasGPT
• Use muP to make hyperparams invariant to scale
• Directly use the chinchilla scaling formula
DeepSeek recipe
• Assume most transformer hypers are invariant to scale
• Do a scaling analysis on batch / LR to figure out optimal scaling
• IsoFLOP analysis to figure out model sizing
› Use a piecewise-linear schedule to make chinchilla scaling cheap.
miniCPM recipe
• Use muP to make transformer + LR invariant to scale
• Use a piecewise linear schedule to get sample for Chinchilla method 3 (curve fitting)
Recent (late 2024+) but less detailed
LLaMA 3 / Hunyuan
• Just isoflops (no other scaling details)
Minimax
• Architecture choice / decision scaling

Validating and understanding muP
“Scale invariant” hyperparameter tuning would be very useful
CerebrasGPT  and miniCPT  also use muP – is it actually useful?

What is muP, anyway?
muP is based off the following assertion. As a function of the width of the network 𝑛𝑙..
A1: The activations at initialization should remain Θ(1)
A2: After one gradient step, the change in activation should be Θ(1)
Note: if individual activations are Θ(1), then the norm should be Θ nl
(this is a very accessible ‘muP for babies’ paper)

Deriving muP (condition A1) 
Suppose that we have a simple, deep linear network ( ℎ𝑙 = 𝑊𝑙ℎ𝑙−1) and we init
 𝑊𝑙 ∼ 𝑁 0, 𝜎𝐼𝑛𝑙×𝑛𝑙−1  then by basic matrix concentration 𝑊𝑙 ∗ → 𝜎( 𝑛𝑙−1 + 𝑛𝑙) and,
ℎ𝑙 2 ≈ 𝑊𝑙 ∗ ℎ𝑙−1 2
Now let’s pick 𝜎 = 𝑛𝑙
𝑛𝑙−1
𝑛𝑙 + 𝑛𝑙−1
−1
= Θ 1
𝑛𝑙−1
min 1, 𝑛𝑙
𝑛𝑙−1
. What happens?
 Inductive assumption - ℎ𝑙−1 2 = Θ 𝑛𝑙−1
 Inductive case - 𝑊𝑙 ∗ → 𝜎 𝑛𝑙−1 + 𝑛𝑙 = 𝑛𝑙
𝑛𝑙−1 
ℎ𝑙 2 = 𝑛𝑙 + 𝑜( 𝑛𝑙)
[Comments – the ≈ here is a bit hand-wavy, as the min s.v. of a Gaussian is 𝑛𝑙 − 𝑛𝑙−1 − 1, and is non-uniform, like J.L.]

Deriving muP (condition A2)
Now we need to deal with updates. Suppose we have the update Δ𝑊𝑙 on the weights.
For SGD, on a linear layer, this looks like a rank -one loss -activation outer product.
Δ𝑊𝑙 = −𝜂𝑙∇ℎ𝑙ℓ ℎ𝑙−1
⊤
Thus, Δ𝑊𝑙ℎ𝑙−1 2 = Δ𝑊𝑙 ∗ ℎ𝑙−1 2 . Now note that we have the update
Δhl = WlΔℎ𝑙−1 + Δ𝑊𝑙(ℎ𝑙−1 + Δℎ𝑙−1)
Assuming that the leading order terms don’t cancel, we see that
• WlΔℎ𝑙−1 = Θ( 𝑛𝑙)  from induction assumption + condition A1 argument
• Δ𝑊𝑙ℎ𝑙−1 = 𝛥𝑊𝑙 ∗ 𝑛𝑙−1 from above, thus 𝜟𝑾𝒍 ∗ = 𝚯 𝒏𝒍
𝒏𝒍−𝟏
• Δ𝑊𝑙Δℎ𝑙−1 = 𝑂( Δ𝑊𝑙 ∗ 𝑛𝑙−1)
