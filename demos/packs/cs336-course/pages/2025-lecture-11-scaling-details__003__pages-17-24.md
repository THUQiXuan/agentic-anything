# 2025 Lecture 11 - Scaling details — pages 17-24

- page_id: `2025-lecture-11-scaling-details__003__pages-17-24`
- url: https://github.com/stanford-cs336/spring2025-lectures/blob/00191bba00d6d64621dc46ccaed9122681413a24/nonexecutable/2025%20Lecture%2011%20-%20Scaling%20details.pdf
- type: segment

## Content

What remains – model size vs data tradeoffs.
From chinchilla – to fit a scaling law, we need to train from scratch, not just early stop
This turns the cost of fitting a scaling law from n to n^2.. Can we avoid this?

(partial) solution in miniCPM – WSD learning rate
Instead of cosine, split learning rate into warmup, stable, and decay phases.
For chinchilla -style analysis, can restart the run at the end of the stable phase.

WSD learning rates work well in miniCPM
Slower during the stable phase, rapid loss decay during decay phase. Decay ~ 10%.

Side note – other ways of estimating chinchilla curves
Gadre et al propose other, curve -fitting based ways of doing similar things 
Core idea – the ‘penalty’
from overtraining remains stable

Chinchilla-type analysis
Equipped with the WSD learning rate, 
we can now try to find the optimal data -to-model size ratio
MiniCPM  authors choose method 1 (lower envelope) and method 3 (joint fit)

Chinchlla method 1
Fairly clear (though maybe not linear?) trends
Different colors indicate different models. Their runs suggest relatively low diminishing 
returns due to data.

Chinchilla method 3
Their primary scaling approach is the joint fit – they find  very high data -model ratios.

Tiny models with lots of data
The overall data -to-model ratio is very high (192), though they argue LLaMA  
architectures should have a higher ratio.
Note that recent models like LLaMA  3 has significantly  higher data -to-model ratios, 
suggesting that with more careful optimization, we might be able to go far beyond 
the 20* model_size  rule of thumb.
