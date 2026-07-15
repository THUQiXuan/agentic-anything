# 2025 Lecture 11 - Scaling details — pages 25-32

- page_id: `2025-lecture-11-scaling-details__004__pages-25-32`
- url: https://github.com/stanford-cs336/spring2025-lectures/blob/00191bba00d6d64621dc46ccaed9122681413a24/nonexecutable/2025%20Lecture%2011%20-%20Scaling%20details.pdf
- type: segment

## Content

Scaling curve fits are (generally) good
Overall fits and predictions of models across a large range of sizes is fairly good.
X-axis, number of tokens in billions.

DeepSeek
DeepSeek  (2024) – another LM with careful scaling analysis
7 and 67B param models – generally high performance compared to other open LM

DeepSeek
Performance - Roughly comparable to LLaMA 2 models of equivalent size.

Scaling strategy – batch + LR 
Scaling strategy : don’t use any muP, directly estimate optimal batch / LR

Scaling analysis of learning rates
Small scale runs + collect ‘near optimal’ (within 0.25% of min) models.
Learning rate fit looks a bit questionable..

For chinchilla analysis: WSD-style learning rate
Deepseek  uses WSD -style learning rate – fast warmup + two decay steps of 10% each.
Generally seems to match performance of cosine learning rates.

Data-size tradeoff analysis: Chinchilla method 2
Straightforward isoflop -style analysis for selecting the model size tradeoffs.

Scaling predicts final model loss
The fitted scaling models (generally) accurately predict the final model losses.
