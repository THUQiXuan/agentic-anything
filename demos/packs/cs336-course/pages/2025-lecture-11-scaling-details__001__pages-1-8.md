# 2025 Lecture 11 - Scaling details — pages 1-8

- page_id: `2025-lecture-11-scaling-details__001__pages-1-8`
- url: https://github.com/stanford-cs336/spring2025-lectures/blob/00191bba00d6d64621dc46ccaed9122681413a24/nonexecutable/2025%20Lecture%2011%20-%20Scaling%20details.pdf
- type: segment

## Content

Lecture 11
CS336
S C A L I N G – C A S E S T U D Y A N D D E T A I L S

Motivation today
What is the best practices for scaling and hparam tuning LMs?
• Does chinchilla’s approach to scaling actually work?
• Can we save compute when training and fitting these things?
• Should we be picking particular architectures / parametrizations to scale nicely?

Scaling in practice
The newest model we talked about with scaling details - 2022
What about more recently?
2023 2024 2024
2024
 2024
 2025

Maximum update parametrization – in depth
Recall – the maximum update parametrization makes appealing claims
Scale-invariant hyperparameter tuning would be very nice. 
How does it work, and does it work in practice?

Recent models with detailed, public scaling recipes
1. Cerebras -GPT
2. MiniCPM
3. DeepSeek

CerebrasGPT
CerebrasGPT  – 0.1 to 13B models trained with the Chinchilla recipe.
Core finding – using muP parametrization makes scaling more stable

Hyperparam scaling strategy
Cerebras  GPT authors find more predictable scaling from muP parametrization

muP parametrization
Appendix contains a very clear set of differences in parametrizing the model for scaling
