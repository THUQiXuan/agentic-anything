# 2025 Lecture 4 - MoEs — pages 41-47

- page_id: `2025-lecture-4-moes__006__pages-41-47`
- url: https://github.com/stanford-cs336/spring2025-lectures/blob/98455ec198c9a88ec1ab2b1c4058662431b54ce3/nonexecutable/2025%20Lecture%204%20-%20MoEs.pdf
- type: segment

## Content

DeepSeek MoE v1-v2-v3
To wrap up, we’ll walk through the DeepSeek  MoE architecture.
V1 (16B – 2.8 active): 
Standard, top-k routing
Shared (2) + Fine-grained (64/4) experts
Standard Aux-loss balancing (Expert + Device)

DeepSeek MoE v2
V2 (236B – 21 active): 
New things:
Shared (2) + Fine-grained (160/10) experts, 6 active
Communication balancing loss – balancing both communication in and out
Top-M device routing

DeepSeek MoE v3
Sigmoid+Softmax  topK + topM
V2 (671B – 37 active): 
Shared (1) + Fine-grained (258) experts, 8 active
New things
Aux-loss-free + seq -wise aux

Bonus: What else do you need to make DeepSeek MoE v3?
MLA : Multihead , latent attention
Basic idea:  express the Q, K, V as functions of a lower -dim, ‘latent’ activation

What else do you need to make DeepSeek MoE v3?
Basic idea:  express the Q, K, V as functions of a lower -dim, ‘latent’ activation
Benefits: when KV-caching, we only need to store 𝑐𝑡
𝐾𝑉, which can be much smaller. 
𝑊𝑈𝐾 can be merged into the Q projection
(they also compress queries, for memory savings during training)
Complexity: rope conflicts with MLA -style caching.
 Without RoPE – 𝑄, 𝐾 = ℎ𝑊 𝑄, 𝑊 𝑈𝐾 𝑐𝑡
𝐾𝑉 = ⟨ℎ 𝑊 𝑄𝑊 𝑈𝐾 , 𝑐𝑡
𝐾𝑉 ⟩
 With RoPE - 𝑄𝑅𝑞, 𝑅𝑘𝐾 = ℎ𝑊 𝑄𝑅𝑞, 𝑅𝑘𝑊 𝑈𝐾 𝑐𝑡
𝐾𝑉 = ℎ 𝑊 𝑄𝑅𝑞𝑅𝑘𝑊 𝑈𝐾 , 𝑐𝑡
𝐾𝑉
The solution – Have a few non-latent key dimensions that can be rotated

What else do you need to make DeepSeek MoE v3?
MTP: Have small, lightweight models that predict multiple steps ahead
[Deepseek v3] [EAGLE]
(See paper for ablations)
(But they only do MTP with one token ahead)

MoE summary
❖ MoEs take advantage of sparsity – not all inputs need the full model
❖ Discrete routing is hard, but top -k heuristics seem to work
❖ Lots of empirical evidence now that MoEs work, and are cost -effective
