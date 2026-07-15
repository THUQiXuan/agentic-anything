# 2025 Lecture 9 - Scaling laws basics — pages 1-8

- page_id: `2025-lecture-9-scaling-laws-basics__001__pages-1-8`
- url: https://github.com/stanford-cs336/spring2025-lectures/blob/fb79eb018fa047bf99c4c785dcbbd62fff361e54/nonexecutable/2025%20Lecture%209%20-%20Scaling%20laws%20basics.pdf
- type: segment

## Content

Lecture 9
CS336
S C A L I N G L A W S - B A S I C S

Taking scaling seriously
Imagine the following scenario..
Your friend has given you ten thousand H100s for a month, 
and asked you to build a good open source LM. 
What do you do?
• Put together your infra team and distributed training framework (A2)
• Put together a great pretraining dataset (A4)
• Run a big model (but which one??) < - we are here.

Scaling isn’t easy
Wide or deep? How many heads? Which nonlinearity? 
We could cargo cult things from existing LMs… but how do these get optimized in the first place?

Today: simple, predictive ‘laws’ for behaviors of LMs
The approach -
  scaling laws  which are simple, predictive rules for model performance
Old and unpleasant: tune hyperparameters on big models
New (over?) optimism: tune on small models, extrapolate to large ones

Part 1. Scaling laws, history and background.
❖ Data scaling as empirical sample complexities
❖ Initial forays into understanding neural scaling with data

Sample complexity and rates
Theorists have thought about ‘scaling’ for a long time..
But these are upper bounds, not actual, realized loss values.
https://www.cs.cmu.edu/~epxing/Class/10701/slides/lecture16-VC.pdf
Hall, 1989
(learning in a finite set of k hypotheses)
(generative modeling for smooth densities)

Earliest (data) scaling law paper – 1993

Early history of scaling laws – data scaling
Log-linear scaling with data [Banko and Brill ‘01]
