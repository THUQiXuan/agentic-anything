# 2025 Lecture 3 - architecture — pages 41-48

- page_id: `2025-lecture-3-architecture__006__pages-41-48`
- url: https://github.com/stanford-cs336/spring2025-lectures/blob/e9cb2488fdb53ea37f0e38924ec3a1701925cef3/nonexecutable/2025%20Lecture%203%20-%20architecture.pdf
- type: segment

## Content

What can we learn from the model-dim hyperparam?
• The ‘default’ choices of 𝑑𝑓𝑓 = 4𝑑𝑚𝑜𝑑𝑒𝑙  and 𝑑𝑓𝑓 = 2.66𝑑𝑚𝑜𝑑𝑒𝑙  have worked well for nearly 
all modern LLMs.
• But T5 does show that even radical choices of 𝑑𝑓𝑓 = 64𝑑𝑚𝑜𝑑𝑒𝑙  can work. This 
hyperparameter choice isn’t written in stone.
• That said, T5 has a follow -up model (T5 v1.1) that is ‘improved’ and uses a much more 
standard 2.5 multiplier on GeGLU , so the 64 -times multiplier is likely suboptimal.

Surprising (?) consensus hyperparameter 2
Head-dim*num -heads to model -dim ratio. As a reminder, slide from 224n.
This doesn’t have to be true: we can have head -dimensions > model -dim / num -heads.
But most models do follow this guideline

How many heads, whats the model dim?
Some examples of this hyperparameter
Num heads Head dim Model dim Ratio
GPT3 96 128 12288 1
T5 128 128 1024 16
T5 v1.1 64 64 4096 1
LaMDA 128 128 8192 2
PaLM 48 258 18432 1.48
LLaMA2 64 128 8192 1
Most models have ratios around 1 – notable exceptions by some google models.

Evidence for 1-1 ratio?
There have been papers written against the 1 -1 ratio [ Bhojanapalli  et al 2020]
But we don’t seem to be seeing significant ‘low rank bottlenecks’ in practice..

Aspect ratios
Should my model be deep or wide? How deep and how wide?
Most models are surprisingly consistent on this one too! 
Model 𝒅𝒎𝒐𝒅𝒆𝒍 /𝒏𝒍𝒂𝒚𝒆𝒓
BLOOM 205
T5 v1.1 171
PaLM (540B) 156
GPT3/OPT/Mistral/ Qwen 128
LLaMA / LLaMA2 / 
Chinchila
102
T5 (11B) 43
GPT2 33
Sweet spot?

Considerations about aspect ratio
Extremely deep models are harder to parallelize and have higher latency
[Tay et al 2021]

Evidence on aspect ratio scaling
[Kaplan et al 2020]
 [Tay et al 2021]

What are typical vocabulary sizes? 
Monolingual models – 30-50k vocab
Model Token count
Original 
transformer
37000
GPT 40257
GPT2/3 50257
T5/T5v1.1 32128
LLaMA 32000
Model Token count
mT5 250000
PaLM 256000
GPT4 100276
Command A 255000
DeepSeek 100000
Qwen 15B 152064
Yi 64000
Multilingual / production systems 100 -250k
Monolingual vocabs don’t need to be huge, but multilingual ones do
