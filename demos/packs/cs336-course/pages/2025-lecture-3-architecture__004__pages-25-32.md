# 2025 Lecture 3 - architecture — pages 25-32

- page_id: `2025-lecture-3-architecture__004__pages-25-32`
- url: https://github.com/stanford-cs336/spring2025-lectures/blob/e9cb2488fdb53ea37f0e38924ec3a1701925cef3/nonexecutable/2025%20Lecture%203%20-%20architecture.pdf
- type: segment

## Content

Do gated linear units work (2)?
Yes, with other works corroborating Shazeer  2020
Narang et al 2020

Gating, activations
• Many variations ( ReLU, GeLU, *GLU) across models.
• *GLU isn’t necessary  for a good model (see GPT3), but it’s probably helpful
 Otuer, recent outlier models..
  Nemotron  340B (Squared ReLU), Falcon 2 11b ( ReLU)
• But evidence points towards somewhat consistent gains from Swi/GeGLU

Serial vs Parallel layers
Normal transformer blocks are serial  – they compute attention, then the MLP
Could we parallelize the transformer block?

Parallel layers
A few models (GPTJ, PaLM, GPT-NeoX) do parallel layers. Originally in GPT -J
If implemented right, LayerNorm  can be shared, and matrix multiplies can be fused
Recent Models: Cohere Command A, Falcon 2 11B, Command R+

Summary: architectures
Pre-vs-post norm: 
• Everyone does pre-norm (except 
OPT350M), likely with good reason.
Layer vs RMSnorm :
• RMSnorm has clear compute wins, 
sometimes even performance
Gating:
• GLUs seem generally better, though 
differences are small
Serial vs parallel layers:
• No extremely serious ablations, but has a 
compute win.

Many variations in position embeddings
Sine embeddings: add sines and cosines that enable localization
𝐸𝑚𝑏𝑒𝑑 𝑥, 𝑖 = 𝑣𝑥 + 𝑃𝐸𝑝𝑜𝑠
Absolute embeddings: add a position vector to the embedding
𝐸𝑚𝑏𝑒𝑑 𝑥, 𝑖 = 𝑣𝑥 + 𝑢𝑖
Relative embeddings: add a vector to the attention computation  
Notable models:
Original transformer
Notable models:
GPT1/2/3, OPT
Notable models:
T5, Gopher, Chinchilla
Rope embeddings (next slides..)
Notable models: 
 GPTJ, PaLM, LLaMA
Most 2024+ models

RoPE: rotary position embeddings
High level thought process: a relative position embedding should be some 𝑓(𝑥, 𝑖) s.t. 
𝑓 𝑥, 𝑖 , 𝑓 𝑦, 𝑗 = 𝑔(𝑥, 𝑦, 𝑖 − 𝑗)
That is, the attention function only gets to depend on the relative position ( i-j). How do 
existing embeddings not fulfill this goal?
• Sine: Has various cross -terms that are not relative
𝐸𝑚𝑏𝑒𝑑 𝑥, 𝑖 , 𝐸𝑚𝑏𝑒𝑑 𝑦, 𝑖 = 𝑣𝑥, 𝑣𝑦 + 𝑃𝐸𝑖, 𝑣𝑦 …
• Absolute: obviously not relative
• Relative embeddings: 
 is not an inner product

RoPE: rotary position embeddings
How can we solve this problem? 
•  We want our embeddings to be invariant to absolute position
•  We know that inner products are invariant to arbitrary rotation.
we 
know
Position independent 
embedding
we 
know
Embedding 
“of course we know”
Rotate we by ‘2 positions’Rotate we by ‘0 positions’
we 
know
Embedding 
“we know that”
know by ‘1 positions’ Rotate know by ‘3 positions’
