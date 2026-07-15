# 2025 Lecture 4 - MoEs — pages 17-24

- page_id: `2025-lecture-4-moes__003__pages-17-24`
- url: https://github.com/stanford-cs336/spring2025-lectures/blob/98455ec198c9a88ec1ab2b1c4058662431b54ce3/nonexecutable/2025%20Lecture%204%20-%20MoEs.pdf
- type: segment

## Content

Common routing variants in detail
Top-k
Used in most MoEs
Switch Transformer (k=1)
Gshard (k=2), Grok (2), Mixtral (2), 
Qwen (4), DBRX (4), 
DeepSeek (7)
Hashing
 Common baseline
[Fedus et al 2022]

Other routing methods
RL to learn routes Used in some of the earliest work
Bengio 2013, not common now
Linear assignment for routing
Used in various papers like Clark ‘22
Solve a matching 
problem
[Fedus et al 2022]

Top-K routing in detail.
Most papers do the old and classic top -k routing. How does this work?
[Dai et al 2024]
Gating
Gates selected by a logistic regressor
This is the 
DeepSeek (V1-2) router
(Grok, Qwen do this too)
Mixtral, DBRX, 
DeepSeek v3 
softmaxes after the 
TopK

Recent variations from DeepSeek and other Chinese LMs
Smaller, larger number of experts + a few shared experts that are always on.
(Used in DeepSeek / Qwen, originally from DeepSpeed MoE)

Various ablations from the DeepSeek paper
More experts, shared experts all seem to generally help

Ablations from OlMoE
Gains from fine -grained experts, none from shared experts.

Expert routing setups for recent MoEs
Model Routed Active Shared Fine-grained ratio
GShard 2048 2 0
Switch Transformer 64 1 0
ST-MOE 64 2 0
Mixtral 8 2 0
DBRX 16 4 0
Grok 8 2 0
DeepSeek v1 64 6 2 1/4
Qwen 1.5 60 4 4 1/8
DeepSeek v3 256 8 1 1/14
OlMoE 64 8 0 1/8
MiniMax 32 2 0 ~1/4
Llama 4 (maverick) 128 1 1 1/2

How do we train MoEs?
Major challenge: we need sparsity for training -time efficiency…
But sparse gating decisions are not differentiable!
Solutions?  
1. Reinforcment  learning to optimize gating policies
2. Stochastic perturbations
3. Heuristic ‘balancing’ losses.
Guess which one people use in practice?
