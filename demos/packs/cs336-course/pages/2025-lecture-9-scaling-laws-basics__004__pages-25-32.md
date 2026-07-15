# 2025 Lecture 9 - Scaling laws basics — pages 25-32

- page_id: `2025-lecture-9-scaling-laws-basics__004__pages-25-32`
- url: https://github.com/stanford-cs336/spring2025-lectures/blob/fb79eb018fa047bf99c4c785dcbbd62fff361e54/nonexecutable/2025%20Lecture%209%20-%20Scaling%20laws%20basics.pdf
- type: segment

## Content

Recap: data scaling laws
❖ Remarkably linear relationship between log -data size and log -error
❖ Holds across domains and models
❖ Theory understanding: similar to generalization bounds: mean estimation example
❖ Applications: data collection / curation

Scaling laws for model engineering
Now for what I promised at the start: model scaling!
Our motivation: how can we efficiently design huge LMs?
• LSTMs vs Transformers
• Adam vs SGD
How should we allocate our limited resources?
• Train models longer vs train bigger models?
• Collect more data vs get more GPUs?
Scaling laws provide a simple procedure to answer these.

Hyperparameter questions
We’ll consider some of these choices in the context of the classic Kaplan scaling paper
• Architecture
• Optimizer
• Aspect ratio / depth
• Batch size

1. Architecture: transformers vs LSTMs
Q: Are transformers better than LSTMs?
Brute force way: spend tens of millions to train a LSTM GPT -3
Scaling law way:
[Kaplan+ 2021]

1. Many architectures
Cross-architecture scaling in Tay et al.

2. Optimizer choice
What about ADAM vs SGD?
[Hestness+ 2017]
(Note, this is in 2017, so pre -transformers. RHN is recurrent highway nets)

3. Depth/Width: Number of layers
Does depth or width make a huge difference?
• 1 vs 2 layers makes a huge difference. 
• More layers have diminishing returns below 107 params

3. Depth/Width: But not all parameters are made equal
We’ve been thinking about ‘parameters’ but not all parameters are equal
Embedding layer parameters don’t behave the same!
Related : recent papers on scaling laws for mixtures of experts.
