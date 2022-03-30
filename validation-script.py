# -*- coding: utf-8 -*-
"""
Automatically generated by Colaboratory.
"""

#@title Install required libraries and packages, authentication 

#@markdown Kick off this piece of code to install the required libraries and packages. In this case we are installing pandas, numpy and gspread.

#@markdown ---

#@markdown Once everything is installed, follow the authentication process.

#@markdown ---

#@markdown * **gspread** is a Python API for Google Sheets. This allows us to open a spreadsheet by title, key or url. Read, write, and format cell ranges.
#@markdown * **pandas** provides us with powerful tools like DataFrame and Series that are mainly used to analyze data
#@markdown * **numpy** works with numerical data and provides powerful objects called Arrays


from googleapiclient import discovery

import pandas as pd;
import numpy as np;

#This is to connect Colab with G-sheet

from google.colab import auth
auth.authenticate_user()

import gspread
from gspread_dataframe import set_with_dataframe
from gspread_formatting import *

from oauth2client.client import GoogleCredentials

gc = gspread.authorize(GoogleCredentials.get_application_default())

#@title Provide the path to Pricing Analysis File and Pricing Procedure Sheet Name 

#@markdown Define the path and sheet name

#@markdown **analysis_sheet_path** = the path to the Pricing Analysis File
analysis_sheet_path = "" #@param {type:"string"}
strip_path = analysis_sheet_path.split('/')
sheet_id = strip_path[5]

#@markdown **pricing_analysis_sheet** = the name of your chosen pricing procedure from the file above
pricing_analysis_sheet = ''#@param {type:"string"}

#@title Provide the path to Validation Sheet, S4 Pricing Procedure Extract and Results Sheet Names

#@markdown ### Enter the link:


validation_path = "" #@param {type:"string"}
config_sheet = "" #@param {type:"string"}
results_difference_sheet = "" #@param {type:"string"}

#@title Accessing the S4 Pricing Procedure SAP Extract, returning total number of rows and columns 

#@markdown Pulled in from **config_sheet** that you provided earlier.

#@markdown Any 0 values are replaced with an empty string.

#@markdown Total number of rows and columns are printed below.

#@markdown ---

wb = gc.open_by_url(validation_path)
#CHANGE THE BELOW WORKSHEET NAME WITH YOUR SHEET TO BE USED FOR COMPARISON

ws = wb.worksheet(config_sheet)

# get_all_values gives a list of rows.
rows = ws.get_all_values()

df1 = pd.DataFrame.from_records(rows,index=None)
df1 = df1.replace(np.nan, '', regex=True).replace(['0',0],'')

#Number of rows in first sheet
print(df1.shape)

#@title Accessing the Pricing Procedure from the Pricing Analysis File, formatting the data and returning total numbers of rows and columns 

#@markdown Pulled in from **pricing_analysis_sheet** that you provided earlier.

#@markdown Right columns are selected based on the 'X' in the header, ~~strikethrough~~ rows are ignored.

#@markdown Unwanted rows and columns are dropped. N/As and 0s are replaced with an empty string.

#@markdown 

#@markdown ---

wb = gc.open_by_url(analysis_sheet_path)
#CHANGE THE BELOW WORKSHEET NAME WITH YOUR SHEET TO BE USED FOR COMPARISON

ws = wb.worksheet(pricing_analysis_sheet)


range_name = str(pricing_analysis_sheet)+"!A1:AZ1000"


credentials = None

service = discovery.build('sheets', 'v4', credentials=credentials)


ranges = range_name

data = (
    service.spreadsheets()
    .get(
        spreadsheetId=sheet_id,
        ranges=ranges,
        includeGridData=True,  # important,
        fields=",".join([  # specify only required fields to reduce response size
            "sheets.data.rowData.values.formattedValue",
            "sheets.data.rowData.values.effectiveFormat.textFormat.strikethrough",
        ])
    )
    .execute()
)



def parse(data): 
    for grid_data in data["sheets"][0]["data"]:
        for row_data in grid_data["rowData"]:
            row = []
            for cell_data in row_data["values"]:
                #value = cell_data["formattedValue"]
                value = cell_data.get("formattedValue",'')
                if value == '':
                  value = ''              
                try:
                  strikethrough = cell_data.get("effectiveFormat",'').get("textFormat",'').get("strikethrough",False)
                except AttributeError:
                  pass
                if not strikethrough:
                    row.append(value)
                else:
                    row.append(None)
            yield row
    

#print(list(parse(data)))
#pprint(data["sheets"][0]["data"])
df2 = pd.DataFrame(list(parse(data)))

df2_header = df2.iloc[0]


right_column = []
i = 0
while i < len(df2_header):
  for column_index in df2_header:
      if 'x' in column_index.lower():
        right_column.append(i)
      i += 1

empty_rows = []
for rows in df2[df2.columns[1]]:
    empty_rows.append(rows)

number_of_rows = empty_rows.count(empty_rows[2]) + empty_rows.count(None) + 2

df2 = df2.iloc[:number_of_rows]
df2 = df2[df2.columns[right_column]]

df2 = df2.mask(df2.eq(None)).dropna()

df2 = df2.replace(np.nan, '', regex=True).replace(['0',0],'')


# for cell in df2[df2.columns[1]]:
#   print(len(cell))
#   if len(cell) == 0:
#     print("hello")

#df2 = df2.iloc[1:].mask(df2.eq('')).dropna()

df2 = df2.iloc[1:]

#df2 = df2.iloc[1:].mask(df2.eq('')).dropna()
print(df2.shape)
#print(df2)

#@title Compares Pricing Procedures and Displays the Differences 

# rows and cols where rows and cells are not equal
rows, cols = np.where(np.not_equal(df1, df2))

# empty dataframe for results
df3 = pd.DataFrame()

# where value not equal in rows and cells, display the difference between the two
# ' {Sheet_Name_1_value} -> {Sheet_Name_2_value} '
for cell in zip(rows, cols):
    df1.iloc[cell[0], cell[1]] = ' {} -> {} '.format(df1.iloc[cell[0], cell[1]], df2.iloc[cell[0], cell[1]])
    df3 = df3.append(df1.iloc[cell[0]])[df1.columns]

# remove any duplicate differences and group in order
grouped = df3.groupby(level=0)
results = grouped.last()

results = results.iloc[1:]

# if column type is a float, change it to integer
# removes the unecessary .0 
for column in results:
    if results[column].dtypes == 'float64':
        results[column] = results[column].map(int)

# gets the right header for the results sheet
new_header_name = df2.iloc[0].to_list()
old_header_name = results.columns.to_list()

# print(new_header_name)
# print(old_header_name)

# # replaces the header in the results sheet
results.rename(
     columns={i:j for i,j in zip(old_header_name,new_header_name)}, inplace=True
 )

wb = gc.open_by_url(validation_path)
#CHANGE THE BELOW WORKSHEET NAME WITH YOUR SHEET TO BE USED FOR COMPARISON

ws = wb.worksheet(config_sheet)
sheet = wb.worksheet(results_difference_sheet)


# opens the worksheet and prints the results 
set_with_dataframe(sheet, results)
print ('Differences found in',str(len(results)),'rows!')
print('\n')
print('\n')

# formats the header in the results sheet
bold_format = cellFormat(
    textFormat=textFormat(bold=True)
    )
format_cell_range(sheet, '1:1', bold_format)


# conditional formatting based on '->' in the cell
rule = ConditionalFormatRule(
    ranges=[GridRange.from_a1_range('A1:Z100', sheet)],
    booleanRule=BooleanRule(
    condition=BooleanCondition('TEXT_CONTAINS', ['->'],),
    format=CellFormat(textFormat=textFormat(bold=True),backgroundColor=Color(1,0,0))
    )
)
rules = get_conditional_format_rules(sheet)
rules.append(rule)
rules.save()