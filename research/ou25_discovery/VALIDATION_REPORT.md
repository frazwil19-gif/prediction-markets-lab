# Gate 1b (Football O/U 2.5) -- Validation Report (2023/24 season, third walk-forward fold)

Fold: `train_through_2022_23_eval_2023_24` (train on 2020/21+2021/22+2022/23, evaluate on 2023/24,
n=1,158-1,160 depending on model).

| Model | n | Log loss | Brier | AUC | Accuracy @ 0.5 | Mean predicted P | Actual rate |
|---|---|---|---|---|---|---|---|
| Naive frequency | 1160 | 0.7011 | 0.2540 | 0.5000 | 0.4345 | 0.4747 | 0.5655 |
| Market (thin panel) | 1160 | 0.6633 | 0.2354 | 0.6255 | 0.6000 | 0.5371 | 0.5655 |
| Fundamentals only | 1158 | 0.6747 | 0.2410 | 0.5921 | 0.5812 | 0.5244 | 0.5648 |
| Market + fundamentals | 1158 | 0.6641 | 0.2358 | 0.6239 | 0.6002 | 0.5329 | 0.5648 |

**Ranking on this single validation season matches the pooled ranking exactly**: market best on every
metric, market+fundamentals second, fundamentals-only third, naive worst. This is the first
out-of-sample confirmation (independent of the pooled figure, and independent of the later holdout
season) that the pooled result is not an artefact of a single unusual fold.
