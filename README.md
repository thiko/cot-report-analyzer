
# Purpose

Generates a table with some details about different commodities based on the COT Disaggregated Report.

## Table content
- It contains the Producer/Consumer (Hedger) as well as the big speculators
- The **Net** positions are calculated by taking all longs and subtract the short positions.
- The **25w, 52w, 3y** columns shows the percentile of net positions compared with the desired timeframe. Example: 25w percentile of 70 means, that the current net position is higher than 70% of the net positions in the last 25w.
- The **Gap** area contains the difference between Hedger and Speculator. This can become useful if both participants are exceptional close to each other or exceptional far away

## Further Ideas
- Include the Term structure
    - http://www.scarrtrading.com/OpenContractsSpectrum.action
    


## Other resources
- https://www.tradingster.com/


## Thanks
Kudos to the creators of [https://github.com/NDelventhal/cot_reports]. I changed the code slightly to match my needs but it saved me some time to download and process the COT data.