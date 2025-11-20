# Repository & Service Test Notes

- _No issues logged yet. Add entries here when code oddities surface during testing._
- [2025-11-12] `TrendingRepository.get_trending_terms` raises `UnboundLocalError` when called with `category=...` and `active_only=False` because `filter_expression` is referenced before assignment (no code change made).
