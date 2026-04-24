# Project Overview — France Fuel Stations Webapp

## Goal
Build a web application listing fuel stations in France (metropolitan),
with a service to find the most cost-effective station from a given point.
Side project aimed at gaining visibility on LinkedIn.

## Core Features
1. Map displaying all fuel stations in France
2. Find the nearest station from an address
3. (Bonus) Calculate the most cost-effective station:
   a real cost = fuel price × distance × vehicle consumption
4. (Bonus) Configure vehicle type to adapt consumption and tank capacity

## Data Sources
- Fuel stations (location + prices): data.gouv.fr flux
- Routing: OSRM (open source, self-hosted or public API)
- Vehicles: flat file with main categories
  (city car, minivan, SUV...) — no external flux for now

## Vehicle Categories (flat file)
To be defined — main categories with average consumption (L/100km)
and tank capacity (L).

## Technical Constraints
- Solo side project, limited time and budget
- Open source and free solutions only
- Simple stack preferred
- Target audience: general public (LinkedIn showcase)

## Project Status
- [ ] Architecture & technical choices
- [ ] Data ingestion (data.gouv)
- [ ] Spatial search engine (nearest station)
- [ ] Cost-effectiveness algorithm
- [ ] Vehicle management (flat file)
- [ ] Frontend webapp (map, UX)
- [ ] Deployment & publication