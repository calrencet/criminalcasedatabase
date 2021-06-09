# Imports
from flask import Flask, render_template, send_file, make_response, url_for, Response
from flask import *
from google.cloud import storage
import pandas as pd
import re
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io
import requests
pd.set_option('display.max_colwidth', 300)
plt.ioff()



# Initialize flask
app = Flask(__name__)

# Route 1: Home
@app.route("/")

# Define home function
def index():
        return render_template('index.html')

def classify_search(input_string):
    if re.search('[Aa]ct|[Cc]ode', input_string):
        try:
            section = re.search('(([Ss](ection|)(s|) |)\d+)', input_string.lower()).group(0).strip()
            section_num = re.sub('([Ss](ection|)(s|) )', "", section)
        except:
            section_num = ""
        statute = re.search(r'((([A-Za-z]*)|(of| )*)*([Aa]ct|[Cc]ode))', input_string.lower()).group(0).strip()
        section_statute = section_num + " " + str.lower(statute)
        return section_statute
    elif re.search(' [Vv] ', input_string):
        temp_case_name = re.search('((([A-Za-z]*)|(a\/l|a\/p|d\/o|s\/o| |bte|bin|and|another|anr|binti|de|the|for|other|matters))* v (([A-Za-z]*)|(a\/l|a\/p|d\/o|s\/o| |bte|bin|and|another|anr|binti|de|the|for|other|matters))*(?=|))', input_string.lower()).group(0).strip()
        case_name = str.lower(temp_case_name)
        return case_name
    else:
        return str.lower(input_string)

def search_search(input_string):
    search_string = classify_search(input_string)
    database = pd.read_csv('gs://criminalcasedatabase.appspot.com/static/data/database.csv')
    if re.search('act|code', search_string):
        temp = database.copy().dropna()
        temp1 = temp['possible_statutes'].apply(lambda x: x.lower())
        result = database.loc[list(temp[temp1.str.contains(search_string)].index)]
        return result[['tribunal/court','case_name','decision_date','aggravation_discussed','mitigation_discussed','citations','possible_titles','possible_statutes','link']]
    elif re.search(' v ', search_string):
        temp = database.copy()
        temp1 = temp['case_name'].apply(lambda x: x.lower())
        result = database.loc[list(temp[temp1.str.contains(search_string)].index)]
        return result[['tribunal/court','case_name','decision_date','aggravation_discussed','mitigation_discussed','citations','possible_titles','possible_statutes','link']]
    else:
        temp = database.copy()
        temp1 = temp['case_name'].apply(lambda x: x.lower())
        result = database.loc[list(temp[temp1.str.contains(search_string)].index)]
        if len(result) == 0:
            temp = database.copy().dropna()
            temp2 = temp['possible_titles'].apply(lambda x: x.lower())
            result = database.loc[list(temp[temp2.str.contains(search_string)].index)]
            if len(result) == 0:
                temp3 = temp['possible_statutes'].apply(lambda x: x.lower())
                result = database.loc[list(temp[temp3.str.contains(search_string)].index)]
                if len(result) == 0:
                    print('''No results found.
                    Please ensure your search is in the following format:
                    Case Name (e.g. John v Smith),
                    Part of offence name (e.g. Forgery - try to avoid), or
                    Statute name (e.g. Section 33 Criminal Procedure Code)''')
                else:
                    return result[['tribunal/court','case_name','decision_date','aggravation_discussed','mitigation_discussed','citations','possible_titles','possible_statutes','link']]
            else:
                return result[['tribunal/court','case_name','decision_date','aggravation_discussed','mitigation_discussed','citations','possible_titles','possible_statutes','link']]
        else:
            return result[['tribunal/court','case_name','decision_date','aggravation_discussed','mitigation_discussed','citations','possible_titles','possible_statutes','link']]

def aggravating(input_string):
    """
    Input: `input_string` as dtype string.
    Output: `results1` as dtype string containing `aggravated_rate` for this search
    """
    results = search_search(input_string)
    results = results.reset_index(drop=True)
    aggravated_rate = results.aggravation_discussed.mean()
    results1 = f'Aggravating factors were discussed in {round(aggravated_rate*100,1)}% of the cases for this search.'
    return results1

def mitigating(input_string):
    """
    Input: `input_string` as dtype string.
    Output: `results1` as dtype string containing `mitigation_rate` for this search
    """
    results = search_search(input_string)
    results = results.reset_index(drop=True)
    mitigation_rate = results.mitigation_discussed.mean()
    results1 = f'Mitigating factors were discussed in {round(mitigation_rate*100,1)}% of the cases for this search.'
    return results1

def create_figure(input_string):
    """
    Input: `input_string` as dtype string.
    Output: `fig` as plot of top 10 citations for this search
    """
    # Takes the `input_string` and performs a search, returning a filtered dataframe
    results = search_search(input_string)
    results = results.reset_index(drop=True)

    # Create citations dataframe
    citations = pd.DataFrame(results['citations'])

    # Split the values of the `citations` column
    citations['citations'] = citations['citations'].apply(lambda x: x.split(','))

    # Dummify the columns of the split results.
    citations2 = pd.DataFrame(pd.get_dummies(citations['citations'].apply(pd.Series).stack()).sum(level=0))

    # Create a fig for the plot
    fig, ax = plt.subplots(figsize = (10,8))

    # Set colour of the plot background
    fig.patch.set_facecolor('#dbdbd7')

    # Set the x and y values of the plot
    x = citations2.sum().sort_values(ascending=False).head(10)[::-1].index
    y = citations2.sum().sort_values(ascending=False).head(10)[::-1]

    # Plot a horizontal bar plot of the data
    ax.barh(x, y, color = "#304C89")

    # Set plot title
    plt.title(f'Top citations for {input_string}', size = 15)

    # Set plot x_ticks size
    plt.xticks(rotation = 0, size = 12)

    # Set plot layout to tight
    plt.tight_layout()

    # Return the plot as output
    return fig

@app.route('/submit')
def submission():
    """
    Input: `input_string` as dtype string which is given from the search box in `form.html`.
    Output: `results.html` with the information from the searches `mitigation rate` as `results2`, `aggravated rate` as `results1`, `search_results` as `results`
    """
# load in the form data from the incoming request
# Input arguments always in JSON format
    user_input = request.args
# manipulate data into a format that we pass to our model
    data = str(escape(user_input['input_string']))
    # return jsonify({'data': data}), 200
    results = search_search(data).reset_index(drop=True)
    results1 = aggravating(data)
    results2 = mitigating(data)
    query = str(data).replace(" ", "+")
    return render_template("results.html", column_names=results.columns.values, row_data=list(results.values.tolist()),
                           link_column="link", zip=zip, plot_name=f"Top citations for '{str.title(data)}':", url=f'/plot.png?input_string={query}', aggravating=results1, mitigating=results2)

@app.route('/plot.png')
def plot_png():
    # Input arguments
    user_input = request.args

    # Manipulate data into a format that we pass to our model
    data = str(escape(user_input['input_string'])).replace("+", " ")

    # Create a figure with the input
    fig = create_figure(data)

    # Store the figure as bytes in an in-memory buffer
    output = io.BytesIO()
    FigureCanvas(fig).print_png(output)

    # Return the figure as an output
    return Response(output.getvalue(), mimetype='image/png')

@app.errorhandler(500)
def invalid_search(e):
    return render_template('invalid_search.html'), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
