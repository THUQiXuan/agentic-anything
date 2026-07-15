# 2025 Lecture 3 - architecture — pages 49-56

- page_id: `2025-lecture-3-architecture__007__pages-49-56`
- url: https://github.com/stanford-cs336/spring2025-lectures/blob/e9cb2488fdb53ea37f0e38924ec3a1701925cef3/nonexecutable/2025%20Lecture%203%20-%20architecture.pdf
- type: segment

## Content

Dropout and other regularization
Do we need regularization during pretraining?
Arguments against:
• There is a lot of data (trillions of tokens), more than parameters.
• SGD only does a single pass on a corpus (hard to memorize)
This is all quite reasonable.. but what do people do in practice?

Dropout and weight decay in practice
* Most of the times papers just don’t discuss dropout. On open models, this closely matches not doing dropout. 
This may not be true of closed models.
Model Dropout* Weight decay
Original transformer 0.1 0
GPT2 0.1 0.1
T5 0.1 0
GPT3 0.1 0.1
T5 v1.1 0 0
PaLM 0 (variable)
OPT 0.1 0.1
LLaMA 0 0.1
Qwen 14B 0.1 0.1
Many older models used 
dropout during pretraining
Newer models (except Qwen) rely 
only on weight decay

Why weight decay LLMs?
[Andriushchenko  et al 2023] has interesting observations about LLM weight decay
It’s not  to control overfitting
 Weight decay interacts with learning rates (cosine schedule)

Summary: hyperparameters
Feedforward
• Factor-of-4 rule of thumb (8/3 for GLUs) is 
standard (with some evidence)
Head dim
• Head dim*Num head = D model is standard 
– but low to no validation
Aspect ratio
• Wide range of ‘good’ values (100-200). 
Systems concerns dictate the value
Regularization
• You still ‘regularize’ LMs but its effects are 
primarily on optimization dynamics

Stability tricks
Recently, lots of attention on stable training  
Don’t train models that look like the blue curve!

Where do the issues arise? Beware of softmaxes!
Softmaxes  – can be ill -behaved due to exponentials / divison  by zero

Output softmax stability – the ‘z-loss’
Recall the softmax  calculation 
[From Devlin 2014]
This is useful for stability! PaLM pioneered this ‘z loss’ trick.
Other examples: Baichuan  2 (2023), DCLM (2024), OLMo 2 (2025)

Attention softmax stability – the ‘QK norm’
The query and keys are Layer (RMS) normed before going into the softmax  operation.
Other examples: DCLM, OLMo2, Gemma 2
Originally from vision and multimodal models [ Dehgani  2023, Idefcs, Chameleon]
Norms
