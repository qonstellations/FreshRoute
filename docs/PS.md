# PROBLEM STATEMENT

## FreshRoute: Intelligent Decision Support for Perishable Produce Distribution
Official Problem Statement

India's Ministry of Food Processing Industries has published a study of post-harvest losses covering 54 commodities across 15 agro-climatic zones, based on the 2020–22 reference period. The reported losses in fruits and vegetables highlight the economic importance of improving post-harvest handling and distribution. Produce distributors must coordinate inventory, estimated shelf life, destination demand, transport time, market prices, and available capacity. Poor coordination can contribute to spoilage, unsold inventory, avoidable logistics costs, and lost revenue.

Build a decision-support platform that recommends which batches to dispatch first, where to allocate them, and when discounting may be appropriate. The system should account for remaining shelf-life estimates, destination demand, transport time and cost, market prices, and available capacity. It must generate an explainable distribution plan and compare its outcomes against a defined baseline.

### Mandatory MVP
● Represent inventory batches by commodity, quantity, and estimated remaining shelf life.
● Allocate available stock across destinations using demand, prices, transport time or cost, and capacity constraints.
● Prioritize dispatches based on perishability and feasibility, including whether expected arrival and handling fit within the remaining shelf-life allowance.
● Recommend discounts for batches at risk of remaining unsold or spoiling, using disclosed assumptions or rules.
● Compare the proposed plan against a baseline strategy and report estimated spoilage, demand fulfillment, and net revenue after the costs defined in the dataset.
Optional Extensions
● Forecast destination demand from historical sales or event and seasonality indicators.
● Optimize discount timing or price reductions under demand and inventory uncertainty.
● Replan when routes are disrupted, transport capacity changes, or new orders arrive.
● Use uncertainty ranges for shelf life, travel time, or demand and explain how they affect the plan.
● Integrate simulated temperature readings or live market-price feeds; live services and physical sensors are optional.

#### Data and Feasibility
Organizers should provide a synthetic or anonymized dataset containing inventory batches, remaining shelf-life estimates, destination demand, market prices, travel times, transport costs, and capacity limits. Include a documented baseline, a consistent economic cost model, and hidden scenarios.

Government post-harvest loss estimates provide context but are not batch-level shelf-life data. A one-day MVP should focus on planning and simulation rather than real distributor integration.

### Commercial Model
Supply-chain optimization software and subscriptions for produce distributors, wholesalers, food logistics companies, cold-storage operators, and agricultural supply-chain platforms.

## Criterion

What Judges Assess | Weight

Spoilage reduction | 20
Reduction in modeled spoilage or expired inventory versus baseline, under the published shelf-life assumptions.

Demand fulfillment | 15
Share of demand fulfilled, with unmet demand and allocation balance measured consistently.

Net economic outcome | 20
Revenue after defined transport, handling, discount, and spoilage costs; all teams use the same cost model.

Allocation feasibility | 15
Compliance with stock availability, destination demand, transport capacity, delivery windows, and shelf-life constraints.

Robustness and sensitivity | 10
How well the plan adapts to demand changes, delays, or uncertainty in shelf life and prices.

Engineering and reproducibility | 10
Repeatable planning runs, transparent assumptions, reliable data handling, and correct calculations.

Explainability and commercial relevance | 10
Clear reasons for dispatch and discount recommendations, with a plausible operational workflow.
