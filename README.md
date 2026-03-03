# Smart-Dispatch-AI-Driven-Emergency-Response-Simulator

Inspiration
Emergency response systems in real cities are incredibly complex. Dispatchers must decide which units to send, how to route them through traffic, and how to coordinate signals and infrastructure — all under time pressure.

We wanted to explore what a smarter, more adaptive response system could look like if cities combined AI decision-making with real-time routing and traffic control.

Our goal was to build a visual simulation that shows how emergency services, road networks, and traffic signals could work together instead of operating as separate systems.

What it does
Our project is an interactive smart-city emergency simulator.

Users can enter an incident, and the system:

Uses AI to determine the appropriate responders
Routes units along real road networks
Dynamically adjusts traffic signals to clear paths
Allows multiple incidents to occur simultaneously
Visualizes responders moving, arriving, and returning to base
This demonstrates how coordinated infrastructure could reduce response times and improve city safety.

How we built it
The system combines a map-based frontend with an AI-powered dispatch backend.

A Leaflet-based map renders roads, stations, and signals
Routing uses real road geometry via OSRM
The backend processes incident descriptions and determines responders
Frontend logic animates responders and manages signal behavior
We focused on building a responsive simulation rather than a static visualization so users can see how decisions play out in real time.

Challenges we ran into
One of the biggest challenges was balancing realism with performance.

Simulating an entire city’s traffic signals and responder movement can quickly overwhelm the browser, so we redesigned parts of the system to approximate real-world behavior while staying interactive and smooth.

We also had to make the dispatch logic resilient to AI output variability by adding fallback rules to ensure the system always responds correctly.

What we learned
This project taught us how complex urban response systems really are.

We learned that intelligent infrastructure isn’t just about AI models — it’s about coordination between routing, signals, dispatch logic, and visualization.

We also learned how to design systems that remain stable even when external APIs fail, which is critical for real-world reliability.

What's next
Future work could include integrating real traffic data, predictive congestion modeling, and analytics dashboards to help city planners evaluate response efficiency.

Our long-term vision is a decision-support tool that helps cities simulate and improve emergency coordination before real incidents occur.

Built With
codex
flask
gemini/groq
html/css
javascript
leaflet.js
llm
osrm-routing-api
python
