# Business Analyst – Reference

Full SQL, Python, and report templates for the business-analyst skill.

---

## 1. Data Collection & Validation (SQL)

```sql
-- Revenue analysis by month
SELECT
    DATE_TRUNC('month', created_at) AS month,
    COUNT(DISTINCT user_id) AS new_customers,
    SUM(total_revenue) AS monthly_revenue,
    AVG(total_revenue) AS avg_order_value
FROM orders
WHERE created_at >= '2024-01-01'
GROUP BY DATE_TRUNC('month', created_at)
ORDER BY month;
```

---

## 2. Cohort Retention Analysis (SQL)

```sql
WITH cohorts AS (
    SELECT
        user_id,
        DATE_TRUNC('month', first_purchase_date) AS cohort_month
    FROM user_first_purchases
),
cohort_sizes AS (
    SELECT
        cohort_month,
        COUNT(*) AS cohort_size
    FROM cohorts
    GROUP BY cohort_month
)
SELECT
    c.cohort_month,
    cs.cohort_size,
    DATE_TRUNC('month', o.order_date) AS period,
    COUNT(DISTINCT c.user_id) AS active_customers,
    ROUND(COUNT(DISTINCT c.user_id) * 100.0 / cs.cohort_size, 2) AS retention_rate
FROM cohorts c
JOIN cohort_sizes cs ON c.cohort_month = cs.cohort_month
LEFT JOIN orders o ON c.user_id = o.user_id
GROUP BY c.cohort_month, cs.cohort_size, DATE_TRUNC('month', o.order_date)
ORDER BY c.cohort_month, period;
```

---

## 3. Revenue Forecasting (Python)

```python
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error

def forecast_revenue(historical_data, months_ahead=12):
    # Feature engineering: trend, seasonality, growth rate
    data = historical_data.copy()
    data['month_num'] = range(len(data))
    data['seasonal'] = pd.to_datetime(data['date']).dt.month

    # Train model on historical data
    features = ['month_num', 'seasonal', 'marketing_spend']
    model = LinearRegression()
    model.fit(data[features], data['revenue'])

    # Generate forecasts
    future_data = create_future_features(months_ahead)
    forecasts = model.predict(future_data)

    return forecasts, calculate_confidence_intervals(forecasts)
```

---

## 4. Executive Dashboard Template

```markdown
## BUSINESS PERFORMANCE DASHBOARD

### Key Metrics Summary
| Metric   | Current | Previous | Change | Benchmark   |
|----------|---------|----------|--------|-------------|
| MRR      | $X      | $Y       | +Z%    | Industry avg|
| CAC      | $X      | $Y       | -Z%    | <$Y target  |
| LTV:CAC  | X:1     | Y:1      | +Z%    | >3:1 target |
| Churn Rate| X%     | Y%       | -Z%    | <5% target  |

### Growth Analysis
- Revenue Growth Rate: X% MoM, Y% YoY
- Customer Growth: X new customers (+Y% retention)
- Unit Economics: $X CAC, $Y LTV, Z month payback
```

---

## 5. Business Analysis Report Template

```markdown
## BUSINESS ANALYSIS REPORT

### Executive Summary
[Key insights and recommendations]

### Performance Overview
[Current metrics vs. targets and benchmarks]

### Growth Analysis
[Trends, drivers, and future projections]

### Action Items
[Specific recommendations with impact estimates]

### Data Appendix
[Supporting analysis and methodology]
```

---

Use these as starting points; adapt table and column names to the actual schema and reporting cadence.
