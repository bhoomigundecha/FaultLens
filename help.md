what are we building: 
An incident detection and root cause diagnosis system that works across deployment environments with different levels of observability, from a fully self-hosted app instrumented with OpenTelemetry (metrics+logs+traces) down to a managed platform like Vercel or Render that only exposes logs or response codes, by detecting what signals are actually available and adapting its diagnosis strategy accordingly, instead of assunming one fixed data shape 

We need to essentially perform three things 
-- Anomaly Detection 
-- Failure Triage 
-- Root Cause Localization 

AD continuously monitors system states to trigger alerts upon detecting abnormal behaviors 

FT categorizes the detected anomalies into specific 
failure types for appropriate engineering team 

RCL identifies exact culprit instance responsible for the failure 

You could refer research papers like TrioExpert, ART, ARMOR, etc. for the same, get an idea of how exactly are they working. 

My idea of building this is that, a developer of any sort, having serverless or server architecture, should be able to perform root cause localization through this 

So when they open our site they can choose if they have serverless or server app then we somehow get the metric log traces (this also i need to figure how to do) or if deployed on render, vercel etc we need to see that also 

Above all this my goal is to build a working demo that can actually be used/shown 

discuss things with me before you start, we go the agentic way, or even if you feel RAG or some other architecture would perform better let me know, i want it to be system heavy like there should be system design involved, do not hold biases be goal driven 