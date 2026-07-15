# 2025 Lecture 3 - architecture — pages 9-16

- page_id: `2025-lecture-3-architecture__002__pages-9-16`
- url: https://github.com/stanford-cs336/spring2025-lectures/blob/e9cb2488fdb53ea37f0e38924ec3a1701925cef3/nonexecutable/2025%20Lecture%203%20-%20architecture.pdf
- type: segment

## Content

Architecture variations..
Let’s think about the core architecture piece
High level view:
• Low consensus 
(except pre-norm)
• Trends toward ‘LLaMA-
like’ architectures

Pre-vs-post norm
The one thing everyone  agrees on (in 2024)
Figure from Xiong 2020
Set up LayerNorm so that it doesn’t affect the 
main residual signal path (on the left)
Almost all modern LMs use pre-norm (but BERT was post-norm) 
(One somewhat funny exception – OPT350M. I don’t know why this is post-norm)

Pre-vs-post-norm, the data
Figure from Xiong 2020
Salazar and Ngyuen 2019

Pre-vs-post norm, explanations?
Gradient attenuation [ Xiong 2020]
 Gradient spikes [Salazar and Ngyuen ] 
Original stated advantage– removing warmup. 
Today – stability and larger LRs for large networks

New things – ‘double’ norm.
If putting LayerNorms  in residual streams is bad.. Why not post -norm outside the stream?
Recent models: Grok, Gemma 2. Olmo 2 only does non-residual post norm

LayerNorm vs RMSNorm
Original transformer: LayerNorm  – normalizes 
the mean and variance across 𝑑𝑚𝑜𝑑𝑒𝑙
Many modern LMs: RMSNorm  – does not 
subtract mean or add a bias term
𝑦 = 𝑥
𝑥 2
2
+ 𝜀
∗ 𝛾
Notable models:
GPT3/2/1, OPT, GPT -J, BLOOM 
Notable models:
LLaMA-family, PaLM, Chinchilla, T5

Why RMSNorm?
Modern explanation – it’s faster (and just as good).
• Fewer operations (no mean calculation)
• Fewer parameters (no bias term to store)
Does this explanation make sense?
Matrix multiplies are the vast majority of FLOPs (and memory)
[Ivanov et al 2023]

Why RMSNorm (2)
Important lesson: FLOPS are not runtime! (we will discuss this in far more detail later)
[Ivanov et al 2023]
Left top (”43G”) is FLOPS
Right top (“153”) is the FLOP-to-memory ratio
RMSNorm can still matter due to 
the importance of data movement
