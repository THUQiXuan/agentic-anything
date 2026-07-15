# 2025 Lecture 9 - Scaling laws basics — pages 9-16

- page_id: `2025-lecture-9-scaling-laws-basics__002__pages-9-16`
- url: https://github.com/stanford-cs336/spring2025-lectures/blob/fb79eb018fa047bf99c4c785dcbbd62fff361e54/nonexecutable/2025%20Lecture%209%20-%20Scaling%20laws%20basics.pdf
- type: segment

## Content

Early history of scaling laws – data scaling
Early tests of functional forms
Kolachina  et al 2012 – power law relation between data and downstream performance

Hestness et al 2017
Earliest ‘large scale neural’ scaling work: Hestness  2017
Predictable scaling on many tasks (MT, LM, Speech) and hypothesized scaling shape.

Hestness II
Very ahead of its time..
“Emergence”
Scaling by compute
Speed = accuracy

Part 2. Neural (LLM) scaling behaviors
1.Data vs performance 
“Are there simple rules that determine how data affects 
performance?”
2. Data vs model size 
Do we train on more data or bigger models?
3. Hyper-parameters vs performance
“How should we set hyperparameters on the big model??”

Scaling laws – power law relationships for many factors
These scaling laws hold on many different kind of phenomena!
They even hold in non -standard 
settings (when train ≠ test)
[Kaplan+ 2020]

Data vs performance 
What’s a data scaling law?
Data scaling laws  : simple formula that maps dataset size (n) to error
What do we expect out of scaling laws?
Monotonic, logistic -
like curves
[Hestness+ 2017]

Data scaling laws for language models
First, an empirical observation
Test Loss
Loss and dataset size is linear on a log-log plot
“Scale-free” or
“Power law”
(For language modeling, from Kaplan+ 2020)

Conceptual foundations of data scaling laws.
Q: Why do scaling laws show up?
 We know error should be monotone
But why is it a power law / linear in log -log?
A (?): Estimation error naturally decays polynomially .
But this answer may take a moment to understand. Let’s work through an example.
Example: If our task is to estimate the mean of a dataset, what’s the scaling law?
