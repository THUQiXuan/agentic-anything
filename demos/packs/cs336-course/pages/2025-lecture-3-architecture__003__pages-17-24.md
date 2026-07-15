# 2025 Lecture 3 - architecture — pages 17-24

- page_id: `2025-lecture-3-architecture__003__pages-17-24`
- url: https://github.com/stanford-cs336/spring2025-lectures/blob/e9cb2488fdb53ea37f0e38924ec3a1701925cef3/nonexecutable/2025%20Lecture%203%20-%20architecture.pdf
- type: segment

## Content

RMSNorm - validation
RMSNorm  runtime (and surprisingly, perf) gains have been seen in papers
Narang et al 2020

More generally: dropping bias terms
Most modern transformers don’t have bias terms.
Original Transformer: 
Most implementations (if they’re not gated):
𝐹𝐹𝑁 𝑥 = 𝜎 𝑥𝑊1 𝑊2
Reasons: memory (similar to RMSnorm ) and optimization stability

LayerNorm: recap
• Basically everyone does pre -norm.
• Intuition – keep the good parts of residual connections
• Observations – nicer gradient propagation, fewer spike
• Some people add a second norm outside the residual stream (NOT post -norm)
• Most people do RMSnorm
• In practice, works as well as LayerNorm
• But, has fewer parameters to move around, which saves on wallclock time
• People more generally drop bias terms since the compute/param tradeoffs are not 
great.

Activations
A whole zoo of activations .. 
 ReLU, GeLU, Swish, ELU, GLU, GeGLU, ReGLU, SeLU, SwiGLU, LiGLU
What are these things? What do people use? Does it matter?

A few of the common activations
ReLU
𝐹𝐹 𝑥 = max 0, 𝑥𝑊1 𝑊2
GeLU
𝐹𝐹 𝑥 = GELU 𝑥𝑊1 𝑊2
𝐺𝐸𝐿𝑈 𝑥 ≔ 𝑥Φ(𝑥)
SwiGLU  / GeGLU  (next slide..)
Notable models:
Original transformer, T5, 
Gopher, Chinchilla, OPT
Notable models:
GPT1/2/3, GPTJ, GPT -Neox, 
BLOOM
Notable models:
Llama, PaLM,T5 v1.1, most 
models post 2023

Gated activations (*GLU)
GLUs modify the ‘first part’ of a FF layer
𝐹𝐹 𝑥 = max 0, 𝑥𝑊1 𝑊2
Instead of a linear + ReLU, augment the above with an (entrywise) linear term
max 0, 𝑥𝑊1 → max 0, 𝑥𝑊1 ⊗ (𝑥𝑉)
This gives the gated variant (ReGLU) – note that we have an extra parameter (V)
FFReGLU 𝑥 = (max 0, 𝑥𝑊1 ⊗ 𝑥𝑉) 𝑊2

Gated variants of standard FF layers
GeGLU
SwiGLU (swish is 𝑥 ∗ sigmoid(𝑥))
Note: Gated models use smaller dimensions for the 𝑑𝑓𝑓 by 2/3
Notable models:
T5 v1.1, mT5, LaMDA, Phi3, 
Gemma 2, Gemma 3
Notable models:
LLaMa 1/2/3, PaLM, Mistral, 
OlMo, most models post 2023

Do gated linear units work?
Yes, fairly consistently so.
Shazeer 2020
