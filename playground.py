import pandas as pd

import cot_reports as cot

#df = cot.cot_year(year = 2024, cot_report_type = 'legacy_futopt')
df = cot.cot_year(year = 2024, cot_report_type = 'disaggregated_fut')
df.to_csv('./2024_disaggregated_fut.csv')

# Example: cot_hist()
# df = cot.cot_hist(cot_report_type= 'traders_in_financial_futures_futopt')
# cot_hist() downloads the historical bulk file for the specified report type, in this example the Traders in Financial Futures Futures-and-Options Combined report. Returns the data as dataframe.

# Example: cot_year()
#df = cot.cot_year(year = 2020, cot_report_type = 'traders_in_financial_futures_fut')
# cot_year() downloads the single year file of the specified report type and year. Returns the data as dataframe.

# Example for collecting data of a few years, here from 2017 to 2020, of a specified report:
#df = pd.DataFrame()
#begin_year = 2017
#end_year = 2020
#for i in range(begin_year, end_year + 1):
#    single_year = pd.DataFrame(cot.cot_year(i, cot_report_type='legacy_futopt')) 
#    df = df.append(single_year, ignore_index=True)

# Example: cot_all()
#df = cot.cot_all(cot_report_type='legacy_fut')
# cot_all() downloads the historical bulk file and all remaining single year files of the specified report type.  Returns the data as dataframe.

