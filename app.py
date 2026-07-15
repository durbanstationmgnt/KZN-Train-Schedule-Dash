import dash
from dash import dcc, html, dash_table, Input, Output
import pandas as pd

# --- DATA PREPROCESSING ---
sheet_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRWyqEm0Rd5hXCQuv6NbpoqC6fN7b5gO-9mXDlDQIw9cF6oJ6-x2FSqQN95TPFb1GiO6oFS22uu8fu7/pub?gid=1813705626&single=true&output=csv"
df = pd.read_csv(sheet_url)
df = df.dropna(subset=['From Station', 'To Station'])

def format_train_no(x):
    if pd.isna(x) or str(x).strip() in ("", "nan"):
        return ""
    try:
        return f"{int(float(x)):04d}"
    except ValueError:
        return str(x)

if 'Train No.' in df.columns:
    df['Train No.'] = df['Train No.'].apply(format_train_no)

# --- INITIALIZE APP ---
app = dash.Dash(__name__)
app.title = "KZN Train Schedule"

# --- LAYOUT ---
app.layout = html.Div(style={'fontFamily': 'sans-serif', 'padding': '20px', 'maxWidth': '1200px', 'margin': 'auto'}, children=[
    html.H1("KZN INTERACTIVE TRAIN SERVICE SCHEDULE", style={'textAlign': 'center'}),
    
    # Filter UI: Dropdowns (using flexbox for columns)
    html.Div(style={'display': 'flex', 'gap': '20px', 'marginBottom': '30px'}, children=[
        html.Div(style={'flex': 1}, children=[
            html.Label("From Station", style={'fontWeight': 'bold'}),
            dcc.Dropdown(id='from-station-dropdown', clearable=False)
        ]),
        html.Div(style={'flex': 1}, children=[
            html.Label("To Station", style={'fontWeight': 'bold'}),
            dcc.Dropdown(id='to-station-dropdown', clearable=False)
        ]),
        html.Div(style={'flex': 1}, children=[
            html.Label("Day Type", style={'fontWeight': 'bold'}),
            dcc.Dropdown(id='day-type-dropdown', clearable=False)
        ]),
    ]),
    
    # Layout: Departure Schedule and Map (using flexbox for a 1.2 : 1 ratio)
    html.Div(style={'display': 'flex', 'gap': '40px'}, children=[
        
        # Left Column: Departure Schedule Display
        html.Div(style={'flex': 1.2}, children=[
            html.H3("Departure Schedule"),
            html.Div(id='schedule-table-container')
        ]),
        
        # Right Column: Route Map and Button
        html.Div(style={'flex': 1}, children=[
            html.Div(style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center'}, children=[
                html.H3("Route Map"),
                html.A(
                    html.Button("Expand Map", style={'padding': '8px 16px', 'cursor': 'pointer'}), 
                    id='expand-map-link', 
                    target="_blank", 
                    style={'display': 'none'}
                )
            ]),
            html.Div(id='map-image-container', style={'marginTop': '10px'})
        ])
    ])
])

# --- CALLBACKS FOR DROPDOWN CHAINING ---
@app.callback(
    Output('from-station-dropdown', 'options'),
    Output('from-station-dropdown', 'value'),
    Input('from-station-dropdown', 'id') # Trigger on load
)
def set_from_station_options(_):
    options = sorted(df['From Station'].unique())
    value = "KZN" if "KZN" in options else options[0] if options else None
    return options, value

@app.callback(
    Output('to-station-dropdown', 'options'),
    Output('to-station-dropdown', 'value'),
    Input('from-station-dropdown', 'value')
)
def set_to_station_options(from_station):
    if not from_station:
        return [], None
    filtered_for_to = df[df['From Station'] == from_station]
    options = sorted(filtered_for_to['To Station'].unique())
    value = "KZN" if "KZN" in options else options[0] if options else None
    return options, value

@app.callback(
    Output('day-type-dropdown', 'options'),
    Output('day-type-dropdown', 'value'),
    Input('from-station-dropdown', 'value'),
    Input('to-station-dropdown', 'value')
)
def set_day_type_options(from_station, to_station):
    if not from_station or not to_station:
        return [], None
    filtered_for_days = df[(df['From Station'] == from_station) & (df['To Station'] == to_station)]
    options = sorted(filtered_for_days['Day Type'].unique())
    value = options[0] if options else None
    return options, value

# --- CALLBACK FOR MAIN DATA FILTERING & DISPLAY ---
@app.callback(
    Output('schedule-table-container', 'children'),
    Output('map-image-container', 'children'),
    Output('expand-map-link', 'href'),
    Output('expand-map-link', 'style'),
    Input('from-station-dropdown', 'value'),
    Input('to-station-dropdown', 'value'),
    Input('day-type-dropdown', 'value')
)
def update_schedule_and_map(from_station, to_station, day_type):
    # Fallback if dropdowns haven't populated yet
    if not from_station or not to_station or not day_type:
        return html.Div("Loading data..."), html.Div("Loading map..."), "", {'display': 'none'}
    
    # Filter logic
    filtered_df = df[
        (df['From Station'] == from_station) & 
        (df['To Station'] == to_station) & 
        (df['Day Type'] == day_type)
    ]
    
    # Generate Table
    if not filtered_df.empty:
        display_cols = ['Train No.', 'Departure Time', 'Day Type']
        existing_cols = [c for c in display_cols if c in filtered_df.columns]
        
        table_ui = dash_table.DataTable(
            data=filtered_df.to_dict('records'),
            columns=[{"name": i, "id": i} for i in existing_cols],
            style_table={'overflowX': 'auto'},
            style_cell={'textAlign': 'left', 'padding': '10px'},
            style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'}
        )
    else:
        table_ui = html.Div("No train times found for this selected route.", style={'padding': '20px', 'backgroundColor': '#f8d7da', 'color': '#721c24', 'borderRadius': '5px'})
        
    # Generate Map
    map_ui = html.Div("Select a route to view the corresponding map.", style={'padding': '20px', 'backgroundColor': '#e2e3e5', 'borderRadius': '5px'})
    btn_href = ""
    btn_style = {'display': 'none'}
    
    if not filtered_df.empty and 'Route Map' in filtered_df.columns:
        map_url = filtered_df['Route Map'].iloc[0]
        
        if pd.notna(map_url) and str(map_url).startswith("http"):
            map_ui = html.Img(src=map_url, style={'width': '100%', 'borderRadius': '5px', 'boxShadow': '0 4px 8px rgba(0,0,0,0.1)'})
            btn_href = map_url
            btn_style = {'display': 'inline-block'} # Show the button
        else:
            map_ui = html.Div("No map image link available for this route.", style={'padding': '20px', 'backgroundColor': '#fff3cd', 'color': '#856404', 'borderRadius': '5px'})

    return table_ui, map_ui, btn_href, btn_style

# New code
if __name__ == '__main__':
    app.run(debug=True)
