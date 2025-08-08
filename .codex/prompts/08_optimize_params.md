Using the latest nightly artifacts (CSV results, equity curves), adjust the default parameter grid to prioritize regions with higher Sharpe and lower MaxDD. 
- Update config/config.example.yaml defaults accordingly.
- Propose 2 alternative entry filters (e.g., ADX>20, or volume surge confirmation) and implement them behind config flags.
- Add A/B backtests comparing baseline vs new filters; update README with findings (tables + brief narrative).
Return all modifications.
