# Question log

The dashboard was designed question-first: each visual exists because a stakeholder asked a question it answers.
The stakeholders and their roles are part of the portfolio scenario (synthetic company, three distribution centres).

| ID | Stakeholder | Question (in their words) | Decision it supports | Answered by | KPI(s) |
|---|---|---|---|---|---|
| Q-01 | Head of Procurement | Which suppliers consistently miss on timeliness or quantity? | Which suppliers go into a performance review | Supplier scorecard | OTIF, on-time %, in-full % |
| Q-02 | Head of Procurement | How much spend sits with underperforming suppliers? | Where to source a second supplier first | Supplier scorecard (spend column, red rows) | Spend, OTIF |
| Q-03 | Head of Procurement | Is a supplier's lead time reliable, or just long? | Whether to change the lead time used in planning | Scorecard: lead-time variance | Lead-time variance |
| Q-04 | Supply Planner | Which SKUs are at risk of running out before the next delivery can arrive? | Expedite, rebalance or raise an emergency order | At-risk SKUs chart | Projected days of cover vs promised lead time |
| Q-05 | Supply Planner | Are supplier delays causing my stockouts? | Whether to escalate to procurement | Scorecard stockout column, monthly trend, drill-through | OTIF, stockout rate |
| Q-06 | Supply Planner | For a failing supplier, which orders went wrong and how? | Evidence for the supplier review | Drill-through: PO lines | Days late, qty short |
| Q-07 | Finance | How much working capital is tied up in excess stock? | Whether to stop or reduce orders | Excess stock value card | Excess stock value |
| Q-08 | Finance | Is stock in line with the agreed cover policy for each class? | Whether the policy or the parameters need to change | Days of cover by class card | Days of cover vs band |

## Open questions for stakeholders

These are the points a real project would need agreed before the dashboard is signed off.

1. **OTIF date basis.** Should "on time" use the supplier-confirmed date or the date on the original PO? (Current build: promised date on the PO.)
2. **Early deliveries.** Should a delivery more than 2 days early count as a failure? It uses space and cash. (Current build: early counts as on time.)
3. **Partial deliveries.** Is a line with 98% delivered "in full"? Finance and procurement may disagree. (Current build: no tolerance, 100% required.)
4. **Open lines.** Lines not yet received are excluded from OTIF until they arrive. Should overdue open lines count as failures immediately?
