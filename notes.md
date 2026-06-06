Prompt: Build a mini-app I'd use

- Build it as a deployable web app where AI doees real work
- Product call and AI integration for real users

Goal is to keep costs low
- Flights anywhere with more criteria
- Google flights only has specific criteria for this: origin, destination, departure date, and arrival date
- However, what if I want to do add more criterias like maximum price, airline preferences, country inclusion/exclusion?

Requirements:
- User must input an origin flight destination

Optional (need to think of default for date range):
- Date range of travel
    - Or how many days/wees you want to want to stay in the location with no set date range
- Max price/travel points (optional if we can get travel points information)
- Country inclusion/exclusion
- Airline preferences

Deliverable
- A simple web ui that can be deployed

Questions:
- Where am I going to get my source of truth data from? Here are some potentials
    - Google Flights (need to reverse engineer)
    - SerpApi
    - United, AA, Delta, etc. (need to figure out how to get this data.)