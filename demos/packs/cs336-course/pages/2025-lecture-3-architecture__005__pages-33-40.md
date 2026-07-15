# 2025 Lecture 3 - architecture — pages 33-40

- page_id: `2025-lecture-3-architecture__005__pages-33-40`
- url: https://github.com/stanford-cs336/spring2025-lectures/blob/e9cb2488fdb53ea37f0e38924ec3a1701925cef3/nonexecutable/2025%20Lecture%203%20-%20architecture.pdf
- type: segment

## Content

RoPE: rotary position embeddings
There are many rotations, which one do you pick? 
Just pair up the coordinates and rotate them in 2d (motivation: complex numbers)
[Su et al 2021]

The actual RoPE math
Multiply with sines and cosines 
Difference with sine embeddings – not additive, no cross terms

Implementation and code for RoPE
…
Same stuff as the usual multi -head self attention below
Get the RoPE 
matrix cos/sin
Multiply 
query/key inputs
Usual 
attention stuff
Note: embedding at each attention operation to enforce position invariance

Hyperparameters
Transformer hyperparameter questions you might have had in 224n..
• How much bigger should the feedforward size be compared to hidden size?
• How many heads, and should num_heads  always divide hidden size?
• What should my vocab size be?
And other model setting questions
• Do people even regularize these huge LMs?
• How do people scale these models  - very deep or very wide?

Surprising (?) consensus hyperparameter 1
Feedforward – model dimension ratio.
There are two dimensions that are relevant – the feedforward dim ( 𝑑𝑓𝑓 ) and model dim 
(𝑑𝑚𝑜𝑑𝑒𝑙 ). What should their relationship be?
𝒅𝒇𝒇 = 𝟒 𝒅𝒎𝒐𝒅𝒆𝒍
This is almost always  true. There’s just a few exceptions.

Exception #1 – GLU variants
Remember that GLU variants scale down by 2/3 rd. This means most GLU variants have 
𝑑𝑓𝑓 =
8
3 𝑑𝑚𝑜𝑑𝑒𝑙 . This is mostly what happens. Some notable such examples.
Model 𝒅𝒇𝒇/𝒅𝒎𝒐𝒅𝒆𝒍
PaLM 4
Mistral 7B 3.5
LLaMA-2 70B 3.5
LLaMA 70B 2.68
Qwen 14B 2.67
DeepSeek 67B 2.68
Yi 34B 2.85
T5 v1.1 2.5
Models are roughly in this range, though PaLM, LLaMA2  and Mistral are slightly larger

Exception #2 – T5
As we have (and will) see, most LMs are have boring, conservative hyperparameters.
One exception is T5 [ Raffel  et al 2020] which has some very bold  settings. 
In particular, for the 11B model, they set 
𝑑𝑓𝑓 = 65,536
𝑑𝑚𝑜𝑑𝑒𝑙 = 1024
For an astounding 64 -times multiplier.
Other, recent exceptions – Gemma 2 (8x), SmolLM/Gemma 3 (4x, GLU)

Why this range of multipliers?
Empirically, there’s a  basin between 1 -10 where this hyperparameter is near -optimal
[Kaplan+ 2020]
